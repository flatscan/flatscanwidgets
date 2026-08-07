#!/usr/bin/python
# coding: utf-8

"""
Base class for info providers.
"""

from resources.lib.kodi_utils import json_rpc_call, set_window_property
from resources.lib.logger import log


class InfoProvider:
    """Base class for info providers."""
    
    def __init__(self):
        self.properties = {}
        
    def set_property(self, key, value, window_id=10000):
        """
        Set a window property.
        
        Args:
            key: Property name
            value: Property value
            window_id: Window ID (default 10000 = home)
        """
        set_window_property(key, value, window_id)
        self.properties[key] = value
        log(f'Set property {key} = {value}')
        
    def clear_properties(self, window_id=10000):
        """Clear all properties set by this provider."""
        for key in self.properties:
            set_window_property(key, None, window_id)
        self.properties.clear()
        
    def get_info(self, **kwargs):
        """
        Get information. Override in subclass.
        
        Returns:
            Dict with info data
        """
        raise NotImplementedError("Subclasses must implement get_info()")