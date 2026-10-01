#!/usr/bin/python
# coding: utf-8

"""
Service entry point for Flatscan Widgets.
"""

import sys
import os
import xbmcaddon

# Get addon path and add to sys.path
ADDON_ID = 'script.flatscan.widgets'
addon = xbmcaddon.Addon(ADDON_ID)
addon_path = addon.getAddonInfo('path')

# Add paths for imports
if addon_path not in sys.path:
    sys.path.insert(0, addon_path)

# Now import works
from resources.lib.service.monitor import main
from resources.lib.service.artwork_cache import start_artwork_cache_service

if __name__ == '__main__':
    # Start artwork pre-caching
    start_artwork_cache_service()
    
    # Run main service
    main()