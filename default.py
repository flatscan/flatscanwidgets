#!/usr/bin/python
# coding: utf-8

"""
Script entry point for Flatscan Widgets.
"""

import sys
import os
import urllib.parse

# Add addon path to Python path
addon_path = os.path.dirname(os.path.abspath(__file__))
if addon_path not in sys.path:
    sys.path.insert(0, addon_path)

from resources.lib.addon import ADDON
from resources.lib.logger import log


def parse_arguments():
    """
    Parse script arguments from RunScript() call.
    
    Returns:
        Dict of parsed arguments
    """
    args = {}
    for arg in sys.argv[1:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            # Clean up quotes and unescape
            value = value.strip('"\'')
            value = urllib.parse.unquote_plus(value)
            args[key.lower()] = value
        else:
            # Handle flag-style arguments
            args[arg.lower()] = True
            
    return args


def route_action(action, args):
    """
    Route script action to appropriate handler.
    
    Args:
        action: The action to perform
        args: Dict of arguments
    """
    log(f'Routing action: {action}')
    
    # INFO MODULE ACTIONS
    if action in ['tvshowdetails', 'seasondetails', 'showdetails']:
        from resources.lib.info.tvshowdetails import TVShowDetails
        handle_tvshow_details(args)
        
    elif action in ['pathstats', 'stats']:
        from resources.lib.info.pathstats import PathStats
        handle_path_stats(args)
        
    # WIDGET REFRESH ACTIONS
    elif action == 'refreshwidgets':
        handle_widget_refresh(args)
        
    # SERVICE CONTROL
    elif action == 'restartservice':
        handle_service_restart(args)
        
    else:
        log(f'Unknown action: {action}')


def handle_tvshow_details(args):
    """
    Handle TV show details action.
    
    Usage: RunScript(script.flatscan.widgets,action=tvshowdetails,dbid=DBID,idtype=TYPE,window=WINDOW_ID)
    """
    dbid = args.get('dbid')
    idtype = args.get('idtype', 'season')
    window_id = int(args.get('window', 10000))
    
    if not dbid:
        log('TV show details: No DBID specified')
        return
        
    try:
        from resources.lib.info.tvshowdetails import TVShowDetails
        
        provider = TVShowDetails()
        provider.set_window_properties(dbid, idtype, window_id)
        
        log(f'TV show details: Set properties for {idtype} {dbid}')

    except Exception as e:
        log(f'TV show details failed: {e}', level='ERROR')


def handle_path_stats(args):
    """
    Handle path statistics action.

    Usage: RunScript(script.flatscan.widgets,action=pathstats,path=PATH,prop=PREFIX,window=WINDOW_ID)
    """
    path = args.get('path')
    prop_prefix = args.get('prop', 'PathStats')
    window_id = int(args.get('window', 10000))

    if not path:
        log('Path stats: No path specified')
        return

    try:
        from resources.lib.info.pathstats import PathStats

        provider = PathStats()
        provider.set_window_properties(path, prop_prefix, window_id)

        log(f'Path stats: Set properties with prefix {prop_prefix}')

    except Exception as e:
        log(f'Path stats failed: {e}', level='ERROR')


def handle_widget_refresh(args):
    """
    Handle widget refresh action.

    Pulses the FlatscanWidgetUpdate home window property, the same signal the
    service sends when the video library updates, so skins can reload widgets.

    Usage: RunScript(script.flatscan.widgets,action=refreshwidgets)
    """
    import xbmc
    import xbmcgui

    window = xbmcgui.Window(10000)
    window.setProperty('FlatscanWidgetUpdate', '1')
    xbmc.sleep(100)
    window.clearProperty('FlatscanWidgetUpdate')

    log('Widget refresh: Pulsed FlatscanWidgetUpdate')


def handle_service_restart(args):
    """
    Handle service restart action.

    The service runs in its own process, so ask it to restart with a Kodi
    notification (handled in ServiceMonitor.onNotification).

    Usage: RunScript(script.flatscan.widgets,action=restartservice)
    """
    import xbmc

    xbmc.executebuiltin('NotifyAll(script.flatscan.widgets,restart_service)')

    log('Service restart: Requested')


def main():
    """Main entry point for script calls."""
    args = parse_arguments()
    action = args.get('action', '')

    if action:
        route_action(str(action).lower(), args)
    else:
        log('No action specified')


if __name__ == '__main__':
    main()
