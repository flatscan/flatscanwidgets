#!/usr/bin/python
# coding: utf-8

"""
Addon constants and paths.
"""

import xbmcaddon
import xbmcvfs
import os

# Addon instance
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')

# Paths
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_DATA_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))


# Ensure directories exist
def ensure_directories():
    """Create addon data directories if they don't exist."""
    for path in [ADDON_DATA_PATH]:
        if not os.path.exists(path):
            os.makedirs(path)

def get_setting(key, default=''):
    """Get addon setting value."""
    return ADDON.getSetting(key) or default

# Call on import
ensure_directories()