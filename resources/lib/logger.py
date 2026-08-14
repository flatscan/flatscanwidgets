#!/usr/bin/python
# coding: utf-8

import xbmc

ADDON_ID = 'script.flatscan.widgets'

def log(message, level='DEBUG'):
    """Log with addon-specific debug setting support."""
    level_map = {
        'DEBUG': xbmc.LOGDEBUG,
        'INFO': xbmc.LOGINFO,
        'WARNING': xbmc.LOGWARNING,
        'ERROR': xbmc.LOGERROR,
    }
    
    # Check addon debug setting - if enabled, promote DEBUG to INFO so it shows
    try:
        addon = xbmcaddon.Addon(ADDON_ID)
        debug_enabled = addon.getSettingBool('debug')
        if debug_enabled and level.upper() == 'DEBUG':
            level = 'INFO'
    except:
        pass
    
    log_level = level_map.get(level.upper(), xbmc.LOGDEBUG)
    formatted = f'[{ADDON_ID}] {message}'
    
    xbmc.log(msg=formatted, level=log_level)


def log_error(message, exception=None):
    """Log an error with optional exception."""
    if exception:
        message = f'{message}: {str(exception)}'
    log(message, 'ERROR')