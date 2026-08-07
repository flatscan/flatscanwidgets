#!/usr/bin/python
# coding: utf-8

"""
Script entry point for Flatscan Widgets.
Routes RunScript() calls to appropriate modules.
"""

import sys
from resources.lib.logger import log

def route_script_call():
    """Route script calls to appropriate modules."""
    
    # Parse arguments
    args = {}
    for arg in sys.argv[1:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            args[key.lower()] = value
    
    action = args.get('action', '')
    log(f'Script called with action: {action}')
    
    # Route to appropriate module
    if action in ['blurimg', 'blur']:
        # Image module
        from resources.lib.image.blur import ImageBlur
        # ... handle blur action
        
    elif action in ['tvshowdetails', 'pathstats']:
        # Info module
        from resources.lib.info.router import route_action
        route_action(action, args)
        
    else:
        log(f'Unknown action: {action}')


if __name__ == '__main__':
    route_script_call()