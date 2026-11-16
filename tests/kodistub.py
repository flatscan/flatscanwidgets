#!/usr/bin/python
# coding: utf-8

"""
Minimal stand-ins for Kodi's Python modules (xbmc, xbmcaddon, xbmcgui,
xbmcplugin, xbmcvfs) so the add-on's modules import outside Kodi.

They only do what the tests need: settings come from SETTINGS, the add-on
profile is a temporary folder, JSON-RPC answers '{}' (tests mock
json_rpc_call instead), and xbmcplugin records the directory items added.
"""

import sys
import tempfile
import types

ADDON_ID = 'script.flatscan.widgets'
PROFILE_DIR = tempfile.mkdtemp(prefix='flatscan-tests-')

# Add-on settings returned by Addon.getSetting*; tests change and reset these
SETTINGS = {}

# xbmcplugin.addDirectoryItem calls as (url, listitem, is_folder)
DIRECTORY = []


class _Recorder:
    """Accepts any setter call and remembers it, e.g. an InfoTagVideo."""

    def __init__(self):
        self.calls = {}

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls[name] = args[0] if len(args) == 1 else args
        return record


class ListItem:
    def __init__(self, label='', label2='', path='', offscreen=False):
        self.label = label
        self.label2 = label2
        self.art = {}
        self.properties = {}
        self.is_folder = None
        self.infotag = _Recorder()

    def setArt(self, art):
        self.art.update(art)

    def setProperty(self, key, value):
        self.properties[key.lower()] = value

    def getProperty(self, key):
        return self.properties.get(key.lower(), '')

    def setIsFolder(self, is_folder):
        self.is_folder = is_folder

    def getVideoInfoTag(self):
        return self.infotag

    def setInfo(self, *args, **kwargs):
        pass


class Window:
    _props = {}

    def __init__(self, window_id=10000):
        self.props = Window._props.setdefault(window_id, {})

    def setProperty(self, key, value):
        self.props[key.lower()] = value

    def getProperty(self, key):
        return self.props.get(key.lower(), '')

    def clearProperty(self, key):
        self.props.pop(key.lower(), None)


class Addon:
    def __init__(self, addon_id=None):
        pass

    def getAddonInfo(self, key):
        return {'id': ADDON_ID, 'profile': PROFILE_DIR, 'name': 'Flatscan Widgets',
                'version': '0.0.0', 'path': ''}.get(key, '')

    def getSetting(self, key):
        return SETTINGS.get(key, '')

    def getSettingBool(self, key):
        return SETTINGS.get(key, '') == 'true'

    def getSettingInt(self, key):
        return int(SETTINGS.get(key) or 0)

    def getLocalizedString(self, string_id):
        return ''


class Monitor:
    def abortRequested(self):
        return False

    def waitForAbort(self, timeout=0):
        return False


def _add_directory_item(handle, url, listitem, isFolder=False, totalItems=0):
    DIRECTORY.append((url, listitem, isFolder))
    return True


def install():
    """Register the stand-in modules in sys.modules (once)."""
    if 'xbmc' in sys.modules:
        return

    xbmc = types.ModuleType('xbmc')
    xbmc.LOGDEBUG, xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 0, 1, 2, 3
    xbmc.log = lambda msg, level=0: None
    xbmc.executeJSONRPC = lambda query: '{}'
    xbmc.executebuiltin = lambda *args, **kwargs: None
    xbmc.getCondVisibility = lambda condition: False
    xbmc.sleep = lambda ms: None
    xbmc.Monitor = Monitor

    xbmcaddon = types.ModuleType('xbmcaddon')
    xbmcaddon.Addon = Addon

    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.ListItem = ListItem
    xbmcgui.Window = Window

    xbmcplugin = types.ModuleType('xbmcplugin')
    xbmcplugin.addDirectoryItem = _add_directory_item
    xbmcplugin.endOfDirectory = lambda *args, **kwargs: None
    xbmcplugin.setContent = lambda *args, **kwargs: None
    xbmcplugin.setPluginCategory = lambda *args, **kwargs: None

    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda path: path
    xbmcvfs.exists = lambda path: False

    for module in (xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs):
        sys.modules[module.__name__] = module


def import_plugin():
    """
    Import plugin.py as Kodi would for a widget path with no handle.

    plugin.py reads the handle from sys.argv[1] on import, so hide the test
    runner's own arguments while importing it.
    """
    if 'plugin' in sys.modules:
        return sys.modules['plugin']
    saved = sys.argv
    sys.argv = ['plugin.py']
    try:
        import plugin
    finally:
        sys.argv = saved
    return plugin
