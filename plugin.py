#!/usr/bin/python
# coding: utf-8

"""
Plugin entry point for Flatscan Widgets.
"""

import sys
import os
import urllib.parse

import xbmc

# Force debug logging for testing
xbmc.log('=== Flatscan Widgets: Plugin starting ===', xbmc.LOGINFO)

# Add addon path to Python path
addon_path = os.path.dirname(os.path.abspath(__file__))
if addon_path not in sys.path:
    sys.path.insert(0, addon_path)

import xbmcgui
import xbmcplugin
from resources.lib.addon import ADDON
from resources.lib.logger import log

# WIDGET IMPORTS - Make sure these are here
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
    """
    # Determine content type from item if not specified
    if content_type == 'video' and item_data.get('mediatype'):
        content_type = item_data['mediatype']
    
    # Set label based on content type
    if content_type == 'episode':
        label = f"{item_data.get('showtitle', '')} - {item_data.get('title', '')}"
        label2 = f"S{item_data.get('season', 0)}E{item_data.get('episode', 0)}"
    elif content_type == 'tvshow':
        label = item_data.get('title', '')
        # Show year and episode count
        year = item_data.get('year', '')
        episodes = item_data.get('episode', 0)
        watched = item_data.get('watchedepisodes', 0)
        label2 = f"{year} • {watched}/{episodes} eps" if year else f"{watched}/{episodes} eps"
    elif content_type == 'season':
        label = f"Season {item_data.get('season', 0)}"
        episodes = item_data.get('episode', 0)
        watched = item_data.get('watchedepisodes', 0)
        label2 = f"{watched}/{episodes} episodes"
    elif content_type == 'movie':
        label = item_data.get('title', '')
        label2 = str(item_data.get('year', ''))
    else:
        label = item_data.get('title', '')
        label2 = ''
    
    li = xbmcgui.ListItem(label=label, label2=label2)
    
    # Set art based on content type
    art = {}
    if content_type == 'tvshow':
        art = {
            'poster': item_data.get('art', {}).get('poster', ''),
            'fanart': item_data.get('art', {}).get('fanart', ''),
            'banner': item_data.get('art', {}).get('banner', ''),
            'clearlogo': item_data.get('art', {}).get('clearlogo', ''),
            'landscape': item_data.get('art', {}).get('landscape', ''),
            'thumb': item_data.get('art', {}).get('poster', ''),  # Use poster as thumb
        }
    elif content_type == 'episode':
    # Use season poster (stored in 'poster') as main art
        art = {
            'thumb': item_data.get('art', {}).get('thumb', ''),  # Small episode thumb
            'poster': item_data.get('art', {}).get('poster', ''),  # Season poster (main)
            'fanart': item_data.get('art', {}).get('fanart', ''),
            'banner': item_data.get('art', {}).get('banner', ''),
            'clearlogo': item_data.get('art', {}).get('clearlogo', ''),
        }
    else:
        art = {
            'thumb': item_data.get('thumbnail', ''),
            'poster': item_data.get('art', {}).get('poster', ''),
            'fanart': item_data.get('art', {}).get('fanart', ''),
            'clearlogo': item_data.get('art', {}).get('clearlogo', ''),
            'banner': item_data.get('art', {}).get('banner', ''),
            'landscape': item_data.get('art', {}).get('landscape', ''),
        }
    li.setArt(art)
    
    # Set info labels based on content type
    if content_type == 'tvshow':
        info_labels = {
            'title': item_data.get('title', ''),
            'tvshowtitle': item_data.get('title', ''),
            'plot': item_data.get('plot', ''),
            'rating': item_data.get('rating', 0),
            'genre': item_data.get('genre', []),
            'studio': item_data.get('studio', []),
            'mpaa': item_data.get('mpaa', ''),
            'episode': item_data.get('episode', 0),
            'watchedepisodes': item_data.get('watchedepisodes', 0),
            'year': item_data.get('year', ''),
        }
        li.setInfo('video', info_labels)
        li.setIsFolder(True)  # TV shows are folders
        
    elif content_type == 'episode':
        info_labels = {
            'title': item_data.get('title', ''),
            'tvshowtitle': item_data.get('showtitle', ''),
            'plot': item_data.get('plot', ''),
            'episode': item_data.get('episode', 0),
            'season': item_data.get('season', 0),
            'rating': item_data.get('rating', 0),
            'firstaired': item_data.get('firstaired', ''),
            'duration': item_data.get('runtime', 0),
        }
        li.setInfo('video', info_labels)
        li.setProperty('IsPlayable', 'true')
        
    elif content_type == 'movie':
        info_labels = {
            'title': item_data.get('title', ''),
            'plot': item_data.get('plot', ''),
            'rating': item_data.get('rating', 0),
            'year': item_data.get('year', ''),
            'genre': item_data.get('genre', []),
            'mpaa': item_data.get('mpaa', ''),
            'duration': item_data.get('runtime', 0),
        }
        li.setInfo('video', info_labels)
        li.setProperty('IsPlayable', 'true')
    
    # Add DBID property
    dbid = item_data.get('tvshowid') or item_data.get('movieid') or item_data.get('episodeid', '')
    li.setProperty('dbid', str(dbid))
    
    return li


def add_items_to_directory(items, content_type, category=''):
    """
    Add items to the plugin directory.
    """
    if HANDLE < 0:
        return
        
    if category:
        xbmcplugin.setPluginCategory(HANDLE, category)
    
    xbmcplugin.setContent(HANDLE, content_type)
    
    for item in items:
        item_type = item.get('mediatype', content_type)
        li = create_listitem(item, item_type)
        
        # Get the file path or DBID for the URL
        file_path = item.get('file', '')
        dbid = item.get('tvshowid') or item.get('movieid') or item.get('episodeid', '')
        
        if item_type == 'episode':
            # Episodes need special handling - use file path or library ID
            if file_path:
                url = file_path  # Direct file path works best
            else:
                # Fallback to videodb ID
                url = f'videodb://episodes/titles/{item.get("episodeid", "")}'
            is_folder = False
            
        elif item_type == 'movie':
            if file_path:
                url = file_path
            else:
                url = f'videodb://movies/titles/{item.get("movieid", "")}'
            is_folder = False
            
        elif item_type == 'tvshow':
            url = f'videodb://tvshows/titles/{dbid}/'
            is_folder = True
            
        elif item_type == 'season':
            url = f'videodb://tvshows/titles/{item.get("tvshowid")}/{item.get("season")}/'
            is_folder = True
            
        else:
            url = ''
            is_folder = False
            
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    
    xbmcplugin.endOfDirectory(HANDLE)

def show_root_listing():
    """Show root menu with proper category grouping."""
    if HANDLE < 0:
        return
        
    xbmcplugin.setPluginCategory(HANDLE, 'Flatscan Widgets')
    xbmcplugin.setContent(HANDLE, 'video')
    
    # TV Shows Category (as a folder)
    li = xbmcgui.ListItem(label='[B]TV Shows[/B]')
    li.setArt({'icon': 'DefaultTVShows.png'})
    li.setInfo('video', {'title': 'TV Shows'})
    url = 'plugin://script.flatscan.widgets/?info=category&category=tvshows'
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Movies Category (as a folder)
    li = xbmcgui.ListItem(label='[B]Movies[/B]')
    li.setArt({'icon': 'DefaultMovies.png'})
    li.setInfo('video', {'title': 'Movies'})
    url = 'plugin://script.flatscan.widgets/?info=category&category=movies'
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Mixed Category (as a folder)
    li = xbmcgui.ListItem(label='[B]Mixed[/B]')
    li.setArt({'icon': 'DefaultVideo.png'})
    li.setInfo('video', {'title': 'Mixed'})
    url = 'plugin://script.flatscan.widgets/?info=category&category=mixed'
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def show_tvshows_listing():
    """Show all TV Shows widgets."""
    if HANDLE < 0:
        return
        
    xbmcplugin.setPluginCategory(HANDLE, 'TV Shows')
    xbmcplugin.setContent(HANDLE, 'video')
    
    tv_widgets = [
    ('In Progress Episodes', 'inprogressepisodes'),
    ('Next Up', 'nextup'),
    ('Recent Episodes', 'recentepisodes'),
    ('Recently Updated Shows', 'recenttvshows'),
    ('TV Show Genres', 'tvshowgenres'),
    ('Random Genre', 'tvshowsbyrandomgenre'),
    ('Suggestions', 'tvsuggestions'),
    ]
    
    for label, info_id in tv_widgets:
        li = xbmcgui.ListItem(label=label)
        url = f'plugin://script.flatscan.widgets/?info={info_id}'
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def show_movies_listing():
    """Show all Movies widgets."""
    if HANDLE < 0:
        return
        
    xbmcplugin.setPluginCategory(HANDLE, 'Movies')
    xbmcplugin.setContent(HANDLE, 'video')
    
    movie_widgets = [
        ('In Progress Movies', 'inprogressmovies'),
        ('Recent Movies', 'recentmovies'),
        ('Random Movies', 'randommovies'),
    ]
    
    for label, info_id in movie_widgets:
        li = xbmcgui.ListItem(label=label)
        url = f'plugin://script.flatscan.widgets/?info={info_id}'
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def show_mixed_listing():
    """Show all Mixed widgets."""
    if HANDLE < 0:
        return
        
    xbmcplugin.setPluginCategory(HANDLE, 'Mixed')
    xbmcplugin.setContent(HANDLE, 'video')
    
    mixed_widgets = [
        ('Continue Watching', 'inprogressmedia'),
        ('Suggestions', 'suggestions'),
    ]
    
    for label, info_id in mixed_widgets:
        li = xbmcgui.ListItem(label=label)
        url = f'plugin://script.flatscan.widgets/?info={info_id}'
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def router():
    log('=== ROUTER CALLED ===', force=True)   # <-- Add this line
    """Route plugin requests to appropriate handlers."""
    params = get_params()
    info = params.get('info', '')

    # Handle category folders
    if info == 'category':
        category = params.get('category', '')
        if category == 'tvshows':
            show_tvshows_listing()
        elif category == 'movies':
            show_movies_listing()
        elif category == 'mixed':
            show_mixed_listing()
        return
    
    log(f'Plugin called with info={info}, params={params}')
    
    # Handle root browsing (no info parameter)
    if not info:
        show_root_listing()
        return
    
    # Get limit parameter (default 20)
    limit = int(params.get('limit', 20))
    
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
            items = shows.get_recently_updated(limit=limit)
            add_items_to_directory(items, 'tvshow', 'Recently Updated Shows')

        # TV SHOW WIDGETS
        elif info == 'inprogressepisodes':
            items = shows.get_inprogress(limit=limit)
            add_items_to_directory(items, 'episode', 'In Progress Episodes')
            
        elif info == 'nextup':
            items = shows.get_next_up(limit=limit)
            add_items_to_directory(items, 'episode', 'Next Up')
            
        elif info == 'recentepisodes':
            items = shows.get_recent_episodes(limit=limit)
            add_items_to_directory(items, 'episode', 'Recent Episodes')
            
        elif info == 'recenttvshows':
            items = shows.get_recently_updated(limit=limit)
            add_items_to_directory(items, 'tvshow', 'Recently Updated Shows')
            
        elif info == 'tvshowgenres':
            items = shows.get_genres()
            add_items_to_directory(items, 'genre', 'TV Show Genres')
            
        elif info == 'tvshowsbyrandomgenre':
            items = shows.get_by_random_genre(limit=limit)
            add_items_to_directory(items, 'tvshow', 'TV Shows by Genre')
            
        elif info == 'tvsuggestions':
            items = shows.get_suggestions(limit=limit)
            add_items_to_directory(items, 'tvshow', 'Suggested TV Shows')

        elif info == 'recentlyairedepisodes':
            days = int(params.get('days', 90))
            items = shows.get_recently_aired_episodes(limit=limit, days=days)
            add_items_to_directory(items, 'episode', f'Recently Aired (Last {days} Days)')
            
        elif info == 'tvsimilar':
            dbid = params.get('dbid')
            if dbid:
                items = shows.get_similar(dbid, limit=limit)
                add_items_to_directory(items, 'tvshow', 'Similar TV Shows')
            else:
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
                
        elif info == 'seasons':
            dbid = params.get('dbid')
            if dbid:
                items = shows.get_seasons(dbid, limit=limit)
                add_items_to_directory(items, 'season', 'Seasons')
            else:
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
                
        elif info == 'episodes':
            dbid = params.get('dbid')
            season = params.get('season')
            if dbid and season:
                items = shows.get_episodes_of_season(dbid, season, limit=limit)
                add_items_to_directory(items, 'episode', 'Episodes')
            else:
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

        
                    
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