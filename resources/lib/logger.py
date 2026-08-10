#!/usr/bin/python
# coding: utf-8

"""
Centralized logging module.
"""

import xbmc
from resources.lib.addon import ADDON_ID, ADDON

# Log level constants
LOG_DEBUG = xbmc.LOGDEBUG
LOG_INFO = xbmc.LOGINFO
LOG_WARNING = xbmc.LOGWARNING
LOG_ERROR = xbmc.LOGERROR
LOG_FATAL = xbmc.LOGFATAL

# String to constant mapping
LOG_LEVELS = {
    'DEBUG': LOG_DEBUG,
    'INFO': LOG_INFO,
    'WARNING': LOG_WARNING,
    'ERROR': LOG_ERROR,
    'FATAL': LOG_FATAL,
}


def log(message, level=LOG_DEBUG, force=False):
    # Convert string levels
    if isinstance(level, str):
        level = LOG_LEVELS.get(level.upper(), LOG_DEBUG)
    
    # Check debug setting
    if level == LOG_DEBUG and not force:
        try:
            if not ADDON.getSettingBool('debug'):
                return
        except:
            pass  # If setting doesn't exist, continue
    
    formatted = f'[{ADDON_ID}] {message}'
    
    try:
        xbmc.log(msg=formatted, level=level)
    except:
        pass  # Don't crash if logging fails


def log_error(message, exception=None):
    """Log an error message with optional exception details."""
    if exception:
        message = f'{message}: {str(exception)}'
    log(message, LOG_ERROR, force=True)


def log_info(message):
    """Log an info message."""
    log(message, LOG_INFO, force=True)