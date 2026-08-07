#!/usr/bin/python
# coding: utf-8

"""
Centralized logging module.
"""

import xbmc
from resources.lib.addon import ADDON_ID, ADDON

# Log levels
LOG_DEBUG = xbmc.LOGDEBUG
LOG_INFO = xbmc.LOGINFO
LOG_WARNING = xbmc.LOGWARNING
LOG_ERROR = xbmc.LOGERROR

def log(message, level=LOG_DEBUG, force=False):
    """
    Log a message to the Kodi log.
    
    Args:
        message: The message to log
        level: Log level (LOG_DEBUG, LOG_INFO, LOG_WARNING, LOG_ERROR)
        force: If True, log even if debug logging is disabled
    """
    # Only log debug messages if debug setting is enabled or force=True
    if level == LOG_DEBUG and not force:
        if not ADDON.getSettingBool('debug'):
            return
    
    # Format and log
    formatted = f'[{ADDON_ID}] {message}'
    xbmc.log(msg=formatted, level=level)

def log_error(message, exception=None):
    """Log an error message with optional exception details."""
    if exception:
        message = f'{message}: {str(exception)}'
    log(message, LOG_ERROR, force=True)

def log_info(message):
    """Log an info message."""
    log(message, LOG_INFO, force=True)