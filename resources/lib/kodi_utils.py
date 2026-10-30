#!/usr/bin/python
# coding: utf-8

"""
Kodi utility functions - wrappers around Kodi APIs.
"""

import xbmc
import xbmcgui
import json
from resources.lib.logger import log_error

def set_window_property(key, value, window_id=10000):
    """
    Set a window property.
    
    Args:
        key: Property name
        value: Property value (will be converted to string)
        window_id: Window ID (default 10000 = home)
    """
    window = xbmcgui.Window(window_id)
    if value is None:
        window.clearProperty(key)
    else:
        window.setProperty(key, str(value))

def json_rpc_call(method, params=None):
    """
    Make a JSON-RPC call to Kodi.
    
    Args:
        method: The JSON-RPC method (e.g., 'VideoLibrary.GetMovies')
        params: Optional parameters dict
    
    Returns:
        Parsed JSON response dict
    """
    query = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': method
    }
    if params:
        query['params'] = params
    
    try:
        response = xbmc.executeJSONRPC(json.dumps(query))
        return json.loads(response)
    except Exception as e:
        log_error(f'JSON-RPC call failed: {method}', e)
        return {}
