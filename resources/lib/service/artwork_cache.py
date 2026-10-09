#!/usr/bin/python
# coding: utf-8

"""
Artwork cache service.

Keeps the widgets fast in two ways:

- Warms Kodi's texture cache for the artwork the widgets show, so the first
  paint of a home screen row does not wait on remote image downloads.
- Refreshes slow network data (the Sonarr calendar) in the background so
  widget loads read it from disk instead of waiting on the network.
"""

import threading
import time
import urllib.parse

import xbmcvfs

from resources.lib.addon import ADDON
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log

# Art keys the plugin puts on list items (see create_listitem in plugin.py)
ART_KEYS = ('poster', 'fanart', 'banner', 'clearlogo', 'landscape')

# Only remote art is worth warming; local files are already fast
REMOTE_PREFIXES = ('http://', 'https://', 'smb://', 'nfs://')

# Cap on downloads per cycle so one pass never runs for minutes
MAX_WARM_PER_CYCLE = 150

WIDGET_LIMIT = 20


def unwrap(url):
    """Return the underlying URL of a Kodi image:// URL (other URLs unchanged)."""
    if url.startswith('image://'):
        return urllib.parse.unquote(url[len('image://'):]).rstrip('/')
    return url


def wrap(url):
    """Return the image:// form Kodi uses as the texture cache key and VFS path."""
    if url.startswith('image://'):
        return url
    return 'image://' + urllib.parse.quote(url, safe='') + '/'


def get_cached_urls():
    """Return the set of underlying URLs already in Kodi's texture cache."""
    result = json_rpc_call('Textures.GetTextures', {'properties': ['url']})
    textures = result.get('result', {}).get('textures', [])
    return {unwrap(t.get('url', '')) for t in textures}


def collect_art_urls(items):
    """Collect the remote artwork URLs a widget's items will display, in order."""
    urls = []
    for item in items:
        art = item.get('art', {})
        candidates = [art.get(key, '') for key in ART_KEYS]
        # Episode list items show the poster as their thumb; others use thumbnail
        if item.get('mediatype') != 'episode':
            candidates.append(item.get('thumbnail', ''))
        for url in candidates:
            if url and unwrap(url).startswith(REMOTE_PREFIXES):
                urls.append(url)
    return urls


def warm_image(url):
    """
    Make Kodi download and cache an image.

    Opening an image:// path through the VFS goes through Kodi's texture
    cache: it downloads, resizes and stores the image, and returns instantly
    next time.
    """
    f = xbmcvfs.File(wrap(url))
    f.close()


class ArtworkCacheService:
    """Background thread that warms artwork and refreshes cached network data."""

    STARTUP_DELAY = 30       # let Kodi settle before doing any work
    REFRESH_INTERVAL = 600   # seconds between cycles when nothing prompts one
    DEBOUNCE = 15            # coalesce bursts of library updates into one cycle

    def __init__(self, monitor):
        self._monitor = monitor
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = None

    def start(self):
        """Start the background thread (if enabled in settings)."""
        if not ADDON.getSettingBool('artwork_cache_enabled'):
            log('ArtworkCache: Disabled')
            return

        self._thread = threading.Thread(target=self._run, name='flatscan-artwork-cache')
        self._thread.daemon = True
        self._thread.start()
        log('ArtworkCache: Started')

    def stop(self):
        """Stop the background thread."""
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=1)
        log('ArtworkCache: Stopped')

    def request_refresh(self):
        """Ask for a cycle soon (for example after the library changed)."""
        self._wake.set()

    def _wait(self, seconds, wake_on_request=False):
        """
        Sleep, waking early for shutdown (and optionally a refresh request).

        Returns:
            'stop', 'wake' or 'timeout'
        """
        end = time.monotonic() + seconds
        while True:
            if self._stop.is_set() or self._monitor.abortRequested():
                return 'stop'
            if wake_on_request and self._wake.is_set():
                self._wake.clear()
                return 'wake'
            remaining = end - time.monotonic()
            if remaining <= 0:
                return 'timeout'
            self._monitor.waitForAbort(min(0.25, remaining))

    def _interrupted(self):
        return self._stop.is_set() or self._monitor.abortRequested()

    def _run(self):
        if self._wait(self.STARTUP_DELAY) == 'stop':
            return

        while True:
            try:
                self._cycle()
            except Exception as e:
                log(f'ArtworkCache: Cycle failed: {e}', 'ERROR')

            reason = self._wait(self.REFRESH_INTERVAL, wake_on_request=True)
            if reason == 'stop':
                return
            if reason == 'wake' and self._wait(self.DEBOUNCE) == 'stop':
                return
            self._wake.clear()

    def _cycle(self):
        # Imported here to avoid circular imports at service start-up
        from resources.lib.widgets.tvshows import TVShowWidgets
        from resources.lib.widgets.movies import MovieWidgets

        shows = TVShowWidgets()
        movies = MovieWidgets()

        # Slow network data first, so widgets are served from disk
        if shows.refresh_sonarr_cache():
            log('ArtworkCache: Sonarr calendar refreshed')

        getters = [
            ('nextup', lambda: shows.get_next_up(limit=WIDGET_LIMIT)),
            ('inprogressepisodes', lambda: shows.get_inprogress_episodes(limit=WIDGET_LIMIT)),
            ('recentepisodes', lambda: shows.get_recent_episodes(limit=WIDGET_LIMIT)),
            ('recentlyaired', lambda: shows.get_recently_aired(limit=WIDGET_LIMIT)),
            ('recentlyaddedgrouped', lambda: shows.get_recently_added_grouped(limit=WIDGET_LIMIT)),
            ('recenttvshows', lambda: shows.get_recently_updated(limit=WIDGET_LIMIT)),
            ('upcomingepisodes', lambda: shows.get_sonarr_upcoming(limit=WIDGET_LIMIT)),
            ('inprogressmovies', lambda: movies.get_inprogress(limit=WIDGET_LIMIT)),
            ('recentmovies', lambda: movies.get_recent(limit=WIDGET_LIMIT)),
        ]

        # Widgets share artwork (a show's fanart repeats across episodes), so
        # de-duplicate by underlying URL before touching the network
        wanted = {}
        for name, getter in getters:
            if self._interrupted():
                return
            try:
                for url in collect_art_urls(getter()):
                    wanted.setdefault(unwrap(url), url)
            except Exception as e:
                log(f'ArtworkCache: Error reading {name}: {e}', 'WARNING')

        cached = get_cached_urls()
        missing = [url for key, url in wanted.items() if key not in cached]
        log(f'ArtworkCache: {len(wanted)} images used by widgets, {len(missing)} not cached')

        warmed = 0
        for url in missing[:MAX_WARM_PER_CYCLE]:
            if self._interrupted():
                break
            try:
                warm_image(url)
                warmed += 1
            except Exception as e:
                log(f'ArtworkCache: Failed to cache image: {e}', 'WARNING')

        if warmed:
            log(f'ArtworkCache: Cached {warmed} images')
