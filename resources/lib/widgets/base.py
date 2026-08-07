#!/usr/bin/python
# coding: utf-8

"""
Base widget class - provides common functionality for all widgets.
"""

import xbmcplugin
import sys
from resources.lib.kodi_utils import json_rpc_call, set_window_property
from resources.lib.logger import log

class BaseWidget:
    """Base class for all content widgets."""
    
    def __init__(self, handle=None):
        """
        Initialize widget.
        
        Args:
            handle: Plugin handle (for plugin:// calls)
        """
        self.handle = handle or int(sys.argv[1]) if len(sys.argv) > 1 else -1
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