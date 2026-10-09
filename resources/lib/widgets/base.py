#!/usr/bin/python
# coding: utf-8

"""
Base widget class - provides common functionality for all widgets.
"""

import xbmcplugin
import sys
from datetime import datetime, timedelta
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log

class BaseWidget:
    """Base class for all content widgets."""
    
    def __init__(self, handle=None):
        """
        Initialize widget.
        
        Args:
            handle: Plugin handle (for plugin:// calls)
        """
        if handle is None:
            # sys.argv[1] is the handle for plugin:// calls, but a RunScript
            # argument (e.g. 'action=...') or missing in other contexts
            try:
                handle = int(sys.argv[1])
            except (IndexError, ValueError):
                handle = -1
        self.handle = handle
        self.li = []  # List items accumulator
        
    def add_list_item(self, item_data, content_type):
        """
        Add an item to the list.
        
        Args:
            item_data: Dict with item properties
            content_type: 'movie', 'episode', 'tvshow', etc.
        """
        self.li.append({
            'data': item_data,
            'type': content_type
        })
        
    def set_content(self, content_type, category=None):
        """
        Set the plugin content type.
        
        Args:
            content_type: Content type string
            category: Optional category label
        """
        if self.handle >= 0:
            if category:
                xbmcplugin.setPluginCategory(self.handle, category)
            xbmcplugin.setContent(self.handle, content_type)
            
    def end_directory(self, succeeded=True):
        """End the directory listing."""
        if self.handle >= 0:
            xbmcplugin.endOfDirectory(self.handle, succeeded)
            
    def get_inprogress_filter(self):
        """Get standard in-progress filter."""
        return {
            'field': 'inprogress',
            'operator': 'true',
            'value': ''
        }
        
    def get_unwatched_filter(self):
        """Get standard unwatched filter."""
        return {
            'field': 'playcount',
            'operator': 'is',
            'value': '0'
        }
        
    def get_random_sort(self):
        """Get random sort order."""
        return {'method': 'random'}
        
    def get_recent_sort(self):
        """Get sort by date added, descending."""
        return {
            'order': 'descending',
            'method': 'dateadded'
        }
        
    def get_lastplayed_sort(self):
        """Get sort by last played, descending."""
        return {
            'order': 'descending',
            'method': 'lastplayed'
        }

    def get_recentlyaired_sort(self):
        """Get sort by air date (Kodi sorts episodes by firstaired under "year"), descending."""
        return {
            'order': 'descending',
            'method': 'year'  # for episodes Kodi sorts this by full air date
        }

    def episode_art(self, ep):
        """
        Build a widget art dict from the art Kodi already attaches to an episode.

        Kodi returns inherited season and show art on every episode
        (season.poster, tvshow.poster, tvshow.fanart, ...), so no extra
        JSON-RPC lookups are needed per show or season.
        """
        art = ep.get('art', {})
        poster = art.get('season.poster') or art.get('tvshow.poster', '')
        # A season's own backdrop wins, falling back to the show's
        fanart = art.get('season.fanart') or art.get('tvshow.fanart') or art.get('fanart', '')
        return {
            'thumb': ep.get('thumbnail', '') or art.get('thumb', ''),
            'poster': poster,
            'season.poster': art.get('season.poster', ''),
            'tvshow.poster': art.get('tvshow.poster', ''),
            'fanart': fanart,
            'tvshow.fanart': art.get('tvshow.fanart', ''),
            'banner': art.get('season.banner') or art.get('tvshow.banner', ''),
            'clearlogo': art.get('tvshow.clearlogo', ''),
            'landscape': art.get('tvshow.landscape', ''),
        }

    def get_recently_added(self, method, properties, limit, windows=(30, 180)):
        """
        Get the newest items of a library type, avoiding a full-table sort.

        Sorting a whole library by dateadded is slow (about 0.9 s for a large
        episode table), while the same sort over a recent date window is
        near-instant. Try progressively wider windows and only fall back to the
        unfiltered query when the windows do not hold enough items.

        Args:
            method: 'VideoLibrary.GetEpisodes', 'VideoLibrary.GetMovies', ...
            properties: Properties to request
            limit: Number of items wanted
            windows: Window sizes in days to try, smallest first

        Returns:
            List of items, newest first
        """
        key = 'episodes' if method.endswith('Episodes') else 'movies' if method.endswith('Movies') else 'tvshows'
        params = {
            'properties': properties,
            'limits': {'start': 0, 'end': limit},
            'sort': self.get_recent_sort(),
        }

        for days in windows:
            after = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            params['filter'] = {'field': 'dateadded', 'operator': 'after', 'value': after}
            items = json_rpc_call(method, params).get('result', {}).get(key, [])
            if len(items) >= limit:
                return items

        del params['filter']
        return json_rpc_call(method, params).get('result', {}).get(key, [])
