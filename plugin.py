#!/usr/bin/python
# coding: utf-8

"""
Plugin entry point for Flatscan Widgets.
Handles widget requests via plugin:// URLs.
"""

import sys
import urllib.parse
import xbmcgui
import xbmcplugin
from resources.lib.addon import ADDON
from resources.lib.logger import log
from resources.lib.widgets import MovieWidgets, TVShowWidgets, MixedWidgets
from resources.lib.info.tvshowdetails import TVShowDetails
from resources.lib.info.pathstats import PathStats

# Handle for plugin:// calls
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1


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


def create_listitem(item_data, content_type):
    """
    Create a Kodi ListItem from widget data.
    
    Args:
        item_data: Dict with item properties
        content_type: 'movie', 'episode', 'tvshow', etc.
        
    Returns:
        xbmcgui.ListItem
    """
    # Determine label based on content type
    if content_type == 'episode':
        label = f"{item_data.get('showtitle', '')} - {item_data.get('title', '')}"
        label2 = f"S{item_data.get('season', 0)}E{item_data.get('episode', 0)}"
    else:
        label = item_data.get('title', '')
        label2 = item_data.get('year', '')
    
    li = xbmcgui.ListItem(label=label, label2=str(label2))
    
    # Set art
    art = {
        'thumb': item_data.get('thumbnail', ''),
        'poster': item_data.get('art', {}).get('poster', ''),
        'fanart': item_data.get('art', {}).get('fanart', ''),
        'clearlogo': item_data.get('art', {}).get('clearlogo', ''),
        'banner': item_data.get('art', {}).get('banner', ''),
        'landscape': item_data.get('art', {}).get('landscape', '')
    }
    li.setArt(art)
    
    # Set info labels
    info_labels = {
        'title': item_data.get('title', ''),
        'plot': item_data.get('plot', ''),
        'rating': item_data.get('rating', 0),
        'genre': item_data.get('genre', []),
        'director': item_data.get('director', ''),
        'writer': item_data.get('writer', ''),
        'year': item_data.get('year', 0),
        'mpaa': item_data.get('mpaa', ''),
    }
    
    # Add content-type specific info
    if content_type == 'movie':
        info_labels['duration'] = item_data.get('runtime', 0)
        info_labels['premiered'] = item_data.get('premiered', '')
        li.setInfo('video', info_labels)
        li.setProperty('IsPlayable', 'true')
        
    elif content_type == 'episode':
        info_labels['episode'] = item_data.get('episode', 0)
        info_labels['season'] = item_data.get('season', 0)
        info_labels['tvshowtitle'] = item_data.get('showtitle', '')
        info_labels['duration'] = item_data.get('runtime', 0)
        info_labels['firstaired'] = item_data.get('firstaired', '')
        li.setInfo('video', info_labels)
        li.setProperty('IsPlayable', 'true')
        
    elif content_type == 'tvshow':
        info_labels['episode'] = item_data.get('episode', 0)
        info_labels['season'] = item_data.get('season', 0)
        info_labels['watchedepisodes'] = item_data.get('watchedepisodes', 0)
        li.setInfo('video', info_labels)
    
    # Add custom properties for skin use
    li.setProperty('mediatype', content_type)
    li.setProperty('dbid', str(item_data.get('tvshowid') or item_data.get('movieid') or item_data.get('episodeid', '')))
    
    # Resume info if available
    resume = item_data.get('resume', {})
    if resume and resume.get('position', 0) > 0:
        li.setProperty('ResumeTime', str(resume.get('position', 0)))
        li.setProperty('TotalTime', str(resume.get('total', 0)))
    
    return li


def add_items_to_directory(items, content_type, category=''):
    """
    Add items to the plugin directory.
    
    Args:
        items: List of item dicts
        content_type: Content type string
        category: Category label for the directory
    """
    if HANDLE < 0:
        return
        
    # Set plugin category
    if category:
        xbmcplugin.setPluginCategory(HANDLE, category)
    
    # Set content type
    xbmcplugin.setContent(HANDLE, content_type)
    
    # Add items
    for item in items:
        li = create_listitem(item, content_type)
        
        # Create URL for the item
        dbid = item.get('movieid') or item.get('episodeid') or item.get('tvshowid', '')
        url = f'videodb://{content_type}s/titles/{dbid}' if dbid else ''
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def router():
    """Route plugin requests to appropriate handlers."""
    params = get_params()
    info = params.get('info', '')
    
    log(f'Plugin called with info={info}, params={params}')
    
    # Initialize widget classes
    movies = MovieWidgets()
    shows = TVShowWidgets()
    mixed = MixedWidgets()
    
    # Get limit parameter (default 20)
    limit = int(params.get('limit', 20))
    
    # Route to appropriate handler
    try:
        # WIDGET ROUTES
        
        if info == 'inprogressmovies':
            items = movies.get_inprogress(limit=limit)
            add_items_to_directory(items, 'movie', 'In Progress Movies')
            
        elif info == 'recentmovies':
            unwatched = params.get('unwatched', 'false').lower() == 'true'
            items = movies.get_recent(limit=limit, unwatched_only=unwatched)
            label = 'Recent Unwatched Movies' if unwatched else 'Recent Movies'
            add_items_to_directory(items, 'movie', label)
            
        elif info == 'randommovies':
            items = movies.get_random(limit=limit)
            add_items_to_directory(items, 'movie', 'Random Movies')
            
        elif info == 'inprogressepisodes':
            items = shows.get_inprogress_episodes(limit=limit)
            add_items_to_directory(items, 'episode', 'In Progress Episodes')
            
        elif info == 'nextup':
            items = shows.get_next_up(limit=limit)
            add_items_to_directory(items, 'episode', 'Next Up')
            
        elif info == 'recentepisodes':
            items = shows.get_recent_episodes(limit=limit)
            add_items_to_directory(items, 'episode', 'Recent Episodes')
            
        elif info == 'recenttvshows':
            items = shows.get_recently_updated_shows(limit=limit)
            add_items_to_directory(items, 'tvshow', 'Recently Updated Shows')
            
        # MIXED MEDIA ROUTES
        
        elif info == 'inprogressmedia':
            items = mixed.get_inprogress_media(limit=limit)
            add_items_to_directory(items, 'video', 'Continue Watching')
            
        elif info == 'suggestions':
            items = mixed.get_suggestions_based_on_watched(limit=limit)
            add_items_to_directory(items, 'video', 'Suggestions')
            
        elif info == 'byrandomgenre':
            result = mixed.get_by_random_genre(limit=limit)
            items = result.get('items', [])
            genre = result.get('genre', 'Random')
            add_items_to_directory(items, 'video', f'{genre} Movies & Shows')
            
        elif info == 'similarmovies':
            dbid = params.get('dbid')
            if dbid:
                items = mixed.get_similar_to_current(dbid, 'movie', limit=limit)
                add_items_to_directory(items, 'movie', 'Similar Movies')
            else:
                log('similarmovies: No dbid provided')
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
                
        elif info == 'similartvshows':
            dbid = params.get('dbid')
            if dbid:
                items = mixed.get_similar_to_current(dbid, 'tvshow', limit=limit)
                add_items_to_directory(items, 'tvshow', 'Similar TV Shows')
            else:
                log('similartvshows: No dbid provided')
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
                
        elif info == 'morebyactor':
            actor = params.get('actor')
            if actor:
                items = mixed.get_more_by_actor(actor, limit=limit)
                add_items_to_directory(items, 'movie', f'Movies with {actor}')
            else:
                log('morebyactor: No actor provided')
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        
        # INFO-BASED WIDGET ROUTES (using info module)
        
        elif info == 'seasonshowdetails':
            # Returns TV show details as a single "dummy" item for display at season level
            dbid = params.get('dbid')
            if dbid:
                provider = TVShowDetails()
                show_info = provider.get_info(dbid, 'season')
                
                # Create a single item with show details
                if show_info:
                    # This is a special case - we return one item with show info
                    # Skins can use this to display show stats at season level
                    dummy_item = {
                        'title': show_info.get('title', ''),
                        'plot': f"{show_info.get('episodes', 0)} episodes | {show_info.get('watchedepisodes', 0)} watched",
                        'art': show_info.get('art', {}),
                        'mediatype': 'tvshow'
                    }
                    add_items_to_directory([dummy_item], 'tvshow', show_info.get('title', ''))
                else:
                    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            else:
                log('seasonshowdetails: No dbid provided')
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        
        elif info == 'pathstatswidget':
            # Returns path statistics as a displayable item
            path = params.get('path', '')
            if path:
                provider = PathStats()
                stats = provider.get_stats(path)
                
                # Create displayable stat items
                stat_items = [
                    {
                        'title': f"Total: {stats.get('count', 0)}",
                        'plot': f"Watched: {stats.get('watched', 0)} | Unwatched: {stats.get('unwatched', 0)}",
                        'mediatype': 'video'
                    }
                ]
                add_items_to_directory(stat_items, 'video', 'Statistics')
            else:
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        
        # UNKNOWN ROUTE
        
        else:
            log(f'Unknown info type: {info}')
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            
    except Exception as e:
        log(f'Error in router: {e}', level='ERROR')
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


if __name__ == '__main__':
    router()