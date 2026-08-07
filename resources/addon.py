#!/usr/bin/python
# coding: utf-8

"""
Addon singleton module.
Provides centralized access to addon info and paths.
"""

import xbmcaddon
import xbmcvfs
import os

# Addon singleton - imported by all modules
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')

# Paths
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_DATA_PATH = xbmcvfs.translatePath(
    os.path.join('special://profile/addon_data/', ADDON_ID)
)
ADDON_IMG_PATH = os.path.join(ADDON_DATA_PATH, 'img')
ADDON_TEMP_PATH = os.path.join(ADDON_DATA_PATH, 'tmp')

# Ensure directories exist
def ensure_directories():
    """Create addon data directories if they don't exist."""
    for path in [ADDON_DATA_PATH, ADDON_IMG_PATH, ADDON_TEMP_PATH]:
        if not os.path.exists(path):
            os.makedirs(path)

# Call on module import
ensure_directories()