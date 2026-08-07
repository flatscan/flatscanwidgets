#!/usr/bin/python
# coding: utf-8

"""
Router for info module script calls.
Handles RunScript() calls from skins.
"""

import sys
from resources.lib.logger import log
from resources.lib.info.tvshowdetails import TVShowDetails
from resources.lib.info.pathstats import PathStats


def route_action(action, params):
    """
    Route info actions to appropriate handlers.
    
    Args:
        action: The action to perform
        params: Dict of parameters
    """
    log(f'Info router: action={action}, params={params}')
    
    if action == 'tvshowdetails':
        provider = TVShowDetails()
        dbid = params.get('dbid')
        idtype = params.get('idtype', 'season')
        window_id = int(params.get('window', 10000))
        
        if dbid:
            provider.set_window_properties(dbid, idtype, window_id)
            
    elif action == 'pathstats':
        provider = PathStats()
        path = params.get('path', '')
        prop_prefix = params.get('prop', 'PathStats')
        window_id = int(params.get('window', 10000))
        
        if path:
            provider.set_window_properties(path, prop_prefix, window_id)
            
    else:
        log(f'Unknown info action: {action}')


def parse_arguments():
    """Parse script arguments."""
    args = {}
    for arg in sys.argv[1:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            args[key.lower()] = value
    return args


def main():
    """Main entry point for script calls."""
    args = parse_arguments()
    action = args.get('action', '')
    
    if action:
        route_action(action, args)
    else:
        log('No action specified for info module')


if __name__ == '__main__':
    main()