#!/usr/bin/python
# coding: utf-8

"""
Script entry point for Flatscan Widgets.
Handles RunScript() calls from skins.
"""

import sys
import urllib.parse
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
    
    # IMAGE MODULE ACTIONS
    if action in ['blur', 'blurimg']:
        from resources.lib.image.blur import ImageBlur
        handle_blur_action(args)
        
    # INFO MODULE ACTIONS
    elif action in ['tvshowdetails', 'seasondetails', 'showdetails']:
        from resources.lib.info.tvshowdetails import TVShowDetails
        handle_tvshow_details(args)
        
    elif action in ['pathstats', 'stats']:
        from resources.lib.info.pathstats import PathStats
        handle_path_stats(args)
        
    # WIDGET REFRESH ACTIONS
    elif action == 'refreshwidgets':
        handle_widget_refresh(args)
        
    # SERVICE CONTROL
    elif action == 'restartservcie':
        handle_service_restart(args)
        
    else:
        log(f'Unknown action: {action}')


def handle_blur_action(args):
    """
    Handle blur image action.
    
    Usage: RunScript(script.flatscan.widgets,action=blur,file=IMAGE_PATH,prop=PREFIX,radius=RADIUS)
    """
    file_path = args.get('file')
    prop_prefix = args.get('prop', 'FlatscanBlur')
    radius = args.get('radius')
    saturation = args.get('saturation')
    
    if not file_path:
        log('Blur action: No file specified')
        return
        
    try:
        from resources.lib.image.blur import ImageBlur
        
        # Convert radius to int if provided
        if radius:
            radius = int(radius)
        if saturation:
            saturation = float(saturation)
            
        blur = ImageBlur(
            file=file_path,
            radius=radius,
            saturation=saturation
        )
        
        # Set properties
        import xbmcgui
        window = xbmcgui.Window(10000)
        window.setProperty(f'{prop_prefix}_blurred', blur.filepath)
        window.setProperty(f'{prop_prefix}_color', blur.avgcolor)
        window.setProperty(f'{prop_prefix}_color_noalpha', blur.avgcolor[2:])
        
        log(f'Blur action: Set properties with prefix {prop_prefix}')
        
    except Exception as e:
        log(f'Blur action failed: {e}', level='ERROR')


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
        
        log(f'TV show details: Set properties for {id