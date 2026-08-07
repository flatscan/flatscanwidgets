#!/usr/bin/python
# coding: utf-8

"""
Fanart service - Rotates background fanart.
"""

import xbmc
import xbmcgui
import random
import threading
from resources.lib.addon import ADDON
from resources.lib.logger import log
from resources.lib.kodi_utils import json_rpc_call


class FanartService:
    """
    Background fanart rotation service.
    Provides random fanart for skin backgrounds.
    """
    
    def __init__(self):
        self._running = False
        self._paused = False
        self._thread = None
        
        # Settings
        self.enabled = ADDON.getSettingBool('fanart_enabled')
        self.interval = ADDON.getSettingInt('fanart_interval') or 30  # seconds
        self.categories = {
            'movies': ADDON.getSettingBool('fanart_movies'),
            'tvshows': ADDON.getSettingBool('fanart_tvshows'),
            'artists': ADDON.getSettingBool('fanart_music'),
        }
        
        # Fanart cache
        self._fanart_cache = []
        self._current_index = 0
        
        log(f'FanartService: Initialized (enabled={self.enabled})')
        
    def start(self):
        """Start the fanart service."""
        if not self.enabled:
            log('FanartService: Disabled')
            return
            
        # Initial population of cache
        self._refresh_cache()
        
        self._running = True
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()
        log('FanartService: Started')
        
    def stop(self):
        """Stop the fanart service."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        log('FanartService: Stopped')
        
    def pause(self):
        """Pause the service."""
        self._paused = True
        log('FanartService: Paused')
        
    def resume(self):
        """Resume the service."""
        self._paused = False
        log('FanartService: Resumed')
        
    def _run(self):
        """Main fanart loop."""
        cycle_count = 0
        
        while self._running:
            if self._paused:
                xbmc.sleep(1000)
                continue
                
            try:
                # Refresh cache periodically (every 10 cycles)
                cycle_count += 1
                if cycle_count >= 10 or not self._fanart_cache:
                    self._refresh_cache()
                    cycle_count = 0
                    
                # Set next fanart
                if self._fanart_cache:
                    self._set_random_fanart()
                    
            except Exception as e:
                log(f'FanartService: Error - {e}', level='ERROR')
                
            # Sleep for interval
            xbmc.sleep(self.interval * 1000)
            
    def _refresh_cache(self):
        """Refresh the fanart cache from library."""
        self._fanart_cache = []
        
        try:
            if self.categories.get('movies'):
                self._fetch_movie_fanart()
                
            if self.categories.get('tvshows'):
                self._fetch_tvshow_fanart()
                
            if self.categories.get('artists'):
                self._fetch_artist_fanart()
                
            # Shuffle for random order
            random.shuffle(self._fanart_cache)
            self._current_index = 0
            
            log(f'FanartService: Cache refreshed ({len(self._fanart_cache)} items)')
            
        except Exception as e:
            log(f'FanartService: Failed to refresh cache - {e}', level='ERROR')
            
    def _fetch_movie_fanart(self):
        """Fetch movie fanart."""
        result = json_rpc_call('VideoLibrary.GetMovies', {
            'properties': ['art'],
            'limits': {'start': 0, 'end': 100},
            'sort': {'method': 'random'}
        })
        
        movies = result.get('result', {}).get('movies', [])
        for movie in movies:
            fanart = movie.get('art', {}).get('fanart')
            if fanart:
                self._fanart_cache.append({
                    'path': fanart,
                    'type': 'movie',
                    'title': movie.get('label', '')
                })
                
    def _fetch_tvshow_fanart(self):
        """Fetch TV show fanart."""
        result = json_rpc_call('VideoLibrary.GetTVShows', {
            'properties': ['art'],
            'limits': {'start': 0, 'end': 100},
            'sort': {'method': 'random'}
        })
        
        shows = result.get('result', {}).get('tvshows', [])
        for show in shows:
            fanart = show.get('art', {}).get('fanart')
            if fanart:
                self._fanart_cache.append({
                    'path': fanart,
                    'type': 'tvshow',
                    'title': show.get('label', '')
                })
                
    def _fetch_artist_fanart(self):
        """Fetch music artist fanart."""
        result = json_rpc_call('AudioLibrary.GetArtists', {
            'properties': ['art'],
            'limits': {'start': 0, 'end': 100},
            'sort': {'method': 'random'}
        })
        
        artists = result.get('result', {}).get('artists', [])
        for artist in artists:
            fanart = artist.get('art', {}).get('fanart')
            if fanart:
                self._fanart_cache.append({
                    'path': fanart,
                    'type': 'artist',
                    'title': artist.get('label', '')
                })
                
    def _set_random_fanart(self):
        """Set a random fanart as window property."""
        if not self._fanart_cache:
            return
            
        # Get next fanart (cycling through shuffled list)
        fanart = self._fanart_cache[self._current_index]
        self._current_index = (self._current_index + 1) % len(self._fanart_cache)
        
        # Set properties
        window = xbmcgui.Window(10000)
        window.setProperty('FlatscanBackground', fanart['path'])
        window.setProperty('FlatscanBackgroundTitle', fanart['title'])
        window.setProperty('FlatscanBackgroundType', fanart['type'])
        
        log(f'FanartService: Set background ({fanart["type"]})')