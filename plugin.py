#!/usr/bin/python
# coding: utf-8

"""
Plugin entry point for Flatscan Widgets.
Handles widget requests via plugin:// URLs.
"""

import sys
import urllib.parse
from resources.lib.addon import ADDON
from resources.lib.logger import log
from resources.lib.kodi_utils import set_window_property
from resources.lib.widgets import MovieWidgets, TVShowWidgets, MixedWidgets

def get_params():
    """Parse plugin URL parameters."""
    params = {}
    if len(sys.argv) > 2:
        param_string = sys.argv[2][1:]  # Remove leading ?
        if param_string:
            pairs = param_string.split('&')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    params[key] = urllib.parse.unquote_plus(value)
    return params

def router():
    """Route plugin requests to appropriate handlers."""
    params = get_params()
    info = params.get('info', '')
    
    log(f'Plugin called with info={info}, params={params}')
    
    # Initialize widget classes
    movies = MovieWidgets()
    shows = TVShowWidgets()
    mixed = MixedWidgets()
    
    # Route to appropriate handler
    handlers = {
        # Movie widgets
        'inprogressmovies': movies.get_inprogress,
        'recentmovies': lambda: movies.get_recent(unwatched_only=False),
        'unwatchedmovies': lambda: movies.get_recent(unwatched_only=True),
        'randommovies': movies.get_random,
        
        # TV show widgets
        'inprogressepisodes': shows.get_inprogress_episodes,
        'nextup': shows.get_next_up,
        'recentepisodes': shows.get_recent_episodes,
        'recenttvshows': shows.get_recently_updated_shows,
        
        # MIXED MEDIA widgets - the unique value of this addon
        'inprogressmedia': mixed.get_inprogress_media,
        'suggestions': mixed.get_suggestions_based_on_watched,
        'byrandomgenre': mixed.get_by_random_genre,
        'similarmovies': lambda: mixed.get_similar_to_current(
            params.get('dbid'), 
            'movie',
            int(params.get('limit', 20))
        ),
        'similartvshows': lambda: mixed.get_similar_to_current(
            params.get('dbid'),
            'tvshow', 
            int(params.get('limit', 20))
        ),
        'morebyactor': lambda: mixed.get_more_by_actor(
            params.get('actor'),
            int(params.get('limit', 20))
        ),
    }
    
    handler = handlers.get(info)
    if handler:
        try:
            items = handler()
            # TODO: Convert items to ListItems and add to directory
            log(f'Handler returned {len(items) if isinstance(items, list) else "dict with " + str(len(items.get("items", []))) + " items"}')
        except Exception as e:
            log(f'Handler error: {e}')
    else:
        log(f'Unknown info type: {info}')

if __name__ == '__main__':
    router()