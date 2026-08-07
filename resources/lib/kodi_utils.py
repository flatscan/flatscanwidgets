#!/usr/bin/python
# coding: utf-8

"""
Kodi utility functions - wrappers around Kodi APIs.
"""

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs
import json
import sys
from resources.lib.addon import ADDON
from resources.lib.logger import log, log_error

# Common dialog
DIALOG = xbmcgui.Dialog()
PLAYER = xbmc.Player()

def execute_builtin(builtin):
    """Execute a Kodi builtin command."""
    log(f'Executing: {builtin}')
    xbmc.executebuiltin(builtin)

def get_cond_visibility(condition):
    """Check a visibility condition."""
    return xbmc.getCondVisibility(condition)

def get_info_label(label):
    """Get an info label value."""
    return xbmc.getInfoLabel(label)

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

def clear_window_property(key, window_id=10000):
    """Clear a window property."""
    window = xbmcgui.Window(window_id)
    window.clearProperty(key)

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

def notify(message, title=None, icon='info', duration=3000):
    """
    Show a notification.
    
    Args:
        message: Notification message
        title: Notification title (defaults to addon name)
        icon: 'info', 'warning', or 'error'
        duration: Duration in milliseconds
    """
    if title is None:
        title = ADDON.getAddonInfo('name')
    
    icons = {
        'info': xbmcgui.NOTIFICATION_INFO,
        'warning': xbmcgui.NOTIFICATION_WARNING,
        'error': xbmcgui.NOTIFICATION_ERROR
    }
    
    DIALOG.notification(title, message, icons.get(icon, 'info'), duration)