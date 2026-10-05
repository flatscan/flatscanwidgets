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
from resources.lib.addon import ADDON, get_setting
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
    Create a Kodi ListItem from widget data using modern InfoTagVideo API.
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
        episode_count = item_data.get('episode_count', 0)
        # year = item_data.get('year', '')
        # episodes = item_data.get('episode', 0)
        # watched = item_data.get('watchedepisodes', 0)
        label2 = f"{episode_count} new episodes"
    elif content_type == 'season':
        # Custom label: "Show Name - Season X" 
        showtitle = item_data.get('tvshowtitle', '')
        season_title = item_data.get('season_title', '')
        episode_count = item_data.get('episode_count', 0)
        label = f"{showtitle} - {season_title}"
        label2 = f"{episode_count} new episodes"
    elif content_type == 'movie':
        label = item_data.get('title', '')
        label2 = str(item_data.get('year', ''))
    else:
        label = item_data.get('title', '')
        label2 = ''
    
    li = xbmcgui.ListItem(label=label, label2=label2)
    
    # Set art based on content type
    if content_type == 'tvshow':
        art = {
            'poster': item_data.get('art', {}).get('poster', ''),
            'fanart': item_data.get('art', {}).get('fanart', ''),
            'banner': item_data.get('art', {}).get('banner', ''),
            'clearlogo': item_data.get('art', {}).get('clearlogo', ''),
            'landscape': item_data.get('art', {}).get('landscape', ''),
            'thumb': item_data.get('art', {}).get('poster', ''),
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
    
    # Use new InfoTagVideo API instead of deprecated setInfo()
    if content_type == 'tvshow':
        infotag = li.getVideoInfoTag()
        infotag.setTitle(item_data.get('title', ''))
        infotag.setPlot(item_data.get('plot', ''))
        infotag.setRating(float(item_data.get('rating', 0)))
        infotag.setGenres(item_data.get('genre', []))
        infotag.setStudios(item_data.get('studio', []))
        infotag.setMpaa(item_data.get('mpaa', ''))
        infotag.setEpisode(int(item_data.get('episode', 0)))
        infotag.setPlaycount(int(item_data.get('watchedepisodes', 0)))
        infotag.setYear(int(item_data.get('year', 0)) if item_data.get('year') else 0)
        infotag.setFirstAired(item_data.get('dateadded', ''))
        # Set art
        li.setArt({
            'fanart': item_data.get('art', {}).get('fanart', ''),
            'poster': item_data.get('art', {}).get('poster', ''),
            'banner': item_data.get('art', {}).get('banner', ''),
            'clearlogo': item_data.get('art', {}).get('clearlogo', ''),
        })
        
        li.setIsFolder(True)
        
    elif content_type == 'episode':
        # Check if this is a Sonarr upcoming episode (no file)
        if not item_data.get('file'):
            # Sonarr upcoming - not playable, just informational
            infotag = li.getVideoInfoTag()
            infotag.setTitle(item_data.get('title', ''))
            infotag.setTvShowTitle(item_data.get('showtitle', ''))
            infotag.setPlot(item_data.get('plot', ''))
            infotag.setSeason(int(item_data.get('season', 0)))
            infotag.setEpisode(int(item_data.get('episode', 0)))
            infotag.setFirstAired(item_data.get('firstaired', ''))
            infotag.setMediaType('episode')
            li.setArt({
                'fanart': item_data.get('art', {}).get('fanart', ''),
                'poster': item_data.get('art', {}).get('poster', ''),
                'banner': item_data.get('art', {}).get('banner', ''),
                'clearlogo': item_data.get('art', {}).get('clearlogo', ''),
                'thumb': item_data.get('art', {}).get('poster', ''),  # Use poster as thumb
            })
            # Not playable - no file yet
            li.setProperty('IsPlayable', 'false')
        else:
            # Regular episode with file - playable
            infotag = li.getVideoInfoTag()
            infotag.setTitle(item_data.get('title', ''))
            infotag.setTvShowTitle(item_data.get('showtitle', ''))
            infotag.setPlot(item_data.get('plot', ''))
            infotag.setEpisode(int(item_data.get('episode', 0)))
            infotag.setSeason(int(item_data.get('season', 0)))
            infotag.setRating(float(item_data.get('rating', 0)))
            infotag.setFirstAired(item_data.get('firstaired', ''))
            infotag.setDuration(int(item_data.get('runtime', 0)))
            li.setArt({
                'fanart': item_data.get('art', {}).get('fanart', ''),
                'poster': item_data.get('art', {}).get('poster', ''),
                'banner': item_data.get('art', {}).get('banner', ''),
                'clearlogo': item_data.get('art', {}).get('clearlogo', ''),
                'thumb': item_data.get('art', {}).get('poster', ''),  # Use poster as thumb
            })
            li.setProperty('IsPlayable', 'true')
        
    elif content_type == 'movie':
        infotag = li.getVideoInfoTag()
        infotag.setTitle(item_data.get('title', ''))
        infotag.setPlot(item_data.get('plot', ''))
        infotag.setRating(float(item_data.get('rating', 0)))
        infotag.setYear(int(item_data.get('year', 0)) if item_data.get('year') else 0)
        infotag.setGenres(item_data.get('genre', []))
        infotag.setMpaa(item_data.get('mpaa', ''))
        infotag.setDuration(int(item_data.get('runtime', 0)))
        li.setProperty('IsPlayable', 'true')

    elif content_type == 'season':
        infotag = li.getVideoInfoTag()
        infotag.setTitle(item_data.get('title', ''))
        infotag.setPlot(item_data.get('plot', ''))
        infotag.setSeason(int(item_data.get('season', 0)))
        infotag.setFirstAired(item_data.get('dateadded', ''))
        infotag.setMediaType('season')
        li.setArt({
            'fanart': item_data.get('art', {}).get('fanart', ''),
            'poster': item_data.get('art', {}).get('poster', ''),
            'banner': item_data.get('art', {}).get('banner', ''),
            'clearlogo': item_data.get('art', {}).get('clearlogo', ''),
            'thumb': item_data.get('art', {}).get('poster', ''),  # Use poster as thumb
        })
        # Respect the playable flag from _set_navigation
        if item_data.get('is_playable'):
            li.setProperty('IsPlayable', 'true')
            li.setIsFolder(False)
        else:
            li.setIsFolder(True)
    
    # Add DBID property
    dbid = item_data.get('tvshowid') or item_data.get('movieid') or item_data.get('episodeid', '')
    li.setProperty('dbid', str(dbid))
    
    # Resume info if available
    resume = item_data.get('resume', {})
    if resume and resume.get('position', 0) > 0:
        li.setProperty('ResumeTime', str(resume.get('position', 0)))
        li.setProperty('TotalTime', str(resume.get('total', 0)))
    
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
            is_playable = item.get('is_playable', True)  # Default to playable for regular episodes
            # Episodes need special handling - use file path or library ID
            if file_path and is_playable:
                url = file_path  # Direct file path works best
            else:
                # Fallback to videodb ID
                url = ''
                is_playable = False

            is_folder = False

            li = create_listitem(item, item_type)
            li.setProperty('IsPlayable', 'true' if is_playable else 'false')
                        
        elif item_type == 'movie':
            if file_path:
                url = file_path
            else:
                url = f'videodb://movies/titles/{item.get("movieid", "")}'
            is_folder = False
            
        elif item_type == 'season':
            if item.get('is_playable'):
                url = file_path  # Use the file path from _set_navigation
                is_folder = False
            else:
                url = f'videodb://tvshows/titles/{item.get("tvshowid")}/{item.get("season")}/'
                is_folder = True

        elif item_type == 'tvshow':
            if item.get('is_playable'):
                url = file_path
                is_folder = False
            else:
                url = f'videodb://tvshows/titles/{dbid}/'
                is_folder = True
            
        else:
            url = ''
            is_folder = False
            
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    
    xbmcplugin.endOfDirectory(HANDLE)

# ========== ROUTE REGISTRY ==========
#
# Every plugin route is registered once with @route. A handler takes
# (widgets, params, limit) and returns (items, mediatype, label) to display,
# or None to fail the directory (missing params, feature disabled, ...).
#
# Routes given a category and label also appear in that category's listing
# menu, in the order they are defined here. To add a widget, add a method on
# a widget class and register a handler below.

CATEGORIES = [
    # (category id, title, icon)
    ('tvshows', 'TV Shows', 'DefaultTVShows.png'),
    ('movies', 'Movies', 'DefaultMovies.png'),
    ('mixed', 'Mixed', 'DefaultVideo.png'),
]

ROUTES = {}


class Widgets:
    """Widget providers handed to route handlers."""

    def __init__(self):
        self.movies = MovieWidgets()
        self.shows = TVShowWidgets()
        self.mixed = MixedWidgets()


def route(info, category=None, label=None):
    """Register a handler for ?info=<info>, optionally listed in a category menu."""
    def register(handler):
        ROUTES[info] = {'handler': handler, 'category': category, 'label': label}
        return handler
    return register


# ----- TV show widgets -----

@route('inprogressepisodes', 'tvshows', 'In Progress Episodes')
def route_inprogressepisodes(w, params, limit):
    return w.shows.get_inprogress_episodes(limit=limit), 'episode', 'In Progress Episodes'


@route('nextup', 'tvshows', 'Next Up')
def route_nextup(w, params, limit):
    return w.shows.get_next_up(limit=limit), 'episode', 'Next Up'


@route('recentepisodes', 'tvshows', 'Recent Episodes')
def route_recentepisodes(w, params, limit):
    return w.shows.get_recent_episodes(limit=limit), 'episode', 'Recent Episodes'


@route('recentlyaired', 'tvshows', 'Recently Aired Episodes')
def route_recentlyaired(w, params, limit):
    days = int(params.get('days', 90))  # Allow custom days via parameter
    return w.shows.get_recently_aired(days=days, limit=limit), 'episode', 'Recently Aired'


@route('recenttvshows', 'tvshows', 'Recently Updated Shows')
def route_recenttvshows(w, params, limit):
    return w.shows.get_recently_updated(limit=limit), 'tvshow', 'Recently Updated Shows'


@route('recentlyaddedgrouped', 'tvshows', 'Recently Added Grouped')
def route_recentlyaddedgrouped(w, params, limit):
    days = int(params.get('days', 30))
    # navigate_to comes from settings, not URL
    return w.shows.get_recently_added_grouped(days=days, limit=limit), 'mixed', 'Recently Added'


@route('upcomingepisodes', 'tvshows', 'Upcoming Episodes')
def route_upcomingepisodes(w, params, limit):
    if not get_setting('sonarr.enabled', 'false') == 'true':
        log('Sonarr not enabled, cannot show upcoming episodes')
        return None
    days = int(params.get('days', get_setting('sonarr.days', '7')))
    return w.shows.get_sonarr_upcoming(days=days, limit=limit), 'episode', 'Upcoming Episodes'


@route('tvshowgenres', 'tvshows', 'TV Show Genres')
def route_tvshowgenres(w, params, limit):
    return w.shows.get_genres(), 'genre', 'TV Show Genres'


@route('tvshowsbyrandomgenre', 'tvshows', 'Random Genre')
def route_tvshowsbyrandomgenre(w, params, limit):
    return w.shows.get_by_random_genre(limit=limit), 'tvshow', 'TV Shows by Genre'


@route('tvsuggestions', 'tvshows', 'Suggestions')
def route_tvsuggestions(w, params, limit):
    return w.shows.get_suggestions(limit=limit), 'tvshow', 'Suggested TV Shows'


@route('tvsimilar')
def route_tvsimilar(w, params, limit):
    dbid = params.get('dbid')
    if not dbid:
        return None
    return w.shows.get_similar(dbid, limit=limit), 'tvshow', 'Similar TV Shows'


@route('seasons')
def route_seasons(w, params, limit):
    dbid = params.get('dbid')
    if not dbid:
        return None
    return w.shows.get_seasons(dbid, limit=limit), 'season', 'Seasons'


@route('episodes')
def route_episodes(w, params, limit):
    dbid = params.get('dbid')
    season = params.get('season')
    if not (dbid and season):
        return None
    return w.shows.get_episodes_of_season(dbid, season, limit=limit), 'episode', 'Episodes'


# ----- Movie widgets -----

@route('inprogressmovies', 'movies', 'In Progress Movies')
def route_inprogressmovies(w, params, limit):
    return w.movies.get_inprogress(limit=limit), 'movie', 'In Progress Movies'


@route('recentmovies', 'movies', 'Recent Movies')
def route_recentmovies(w, params, limit):
    unwatched = params.get('unwatched', 'false').lower() == 'true'
    items = w.movies.get_recent(limit=limit, unwatched_only=unwatched)
    return items, 'movie', 'Recent Unwatched Movies' if unwatched else 'Recent Movies'


@route('randommovies', 'movies', 'Random Movies')
def route_randommovies(w, params, limit):
    return w.movies.get_random(limit=limit), 'movie', 'Random Movies'


# ----- Mixed media widgets -----

@route('inprogressmedia', 'mixed', 'Continue Watching')
def route_inprogressmedia(w, params, limit):
    return w.mixed.get_inprogress_media(limit=limit), 'video', 'Continue Watching'


@route('suggestions', 'mixed', 'Suggestions')
def route_suggestions(w, params, limit):
    return w.mixed.get_suggestions_based_on_watched(limit=limit), 'video', 'Suggestions'


@route('byrandomgenre')
def route_byrandomgenre(w, params, limit):
    result = w.mixed.get_by_random_genre(limit=limit)
    genre = result.get('genre', 'Random')
    return result.get('items', []), 'video', f'{genre} Movies & Shows'


@route('similarmovies')
def route_similarmovies(w, params, limit):
    dbid = params.get('dbid')
    if not dbid:
        log('similarmovies: No dbid provided')
        return None
    return w.mixed.get_similar_to_current(dbid, 'movie', limit=limit), 'movie', 'Similar Movies'


@route('similartvshows')
def route_similartvshows(w, params, limit):
    dbid = params.get('dbid')
    if not dbid:
        log('similartvshows: No dbid provided')
        return None
    return w.mixed.get_similar_to_current(dbid, 'tvshow', limit=limit), 'tvshow', 'Similar TV Shows'


@route('morebyactor')
def route_morebyactor(w, params, limit):
    actor = params.get('actor')
    if not actor:
        log('morebyactor: No actor provided')
        return None
    return w.mixed.get_more_by_actor(actor, limit=limit), 'movie', f'Movies with {actor}'


# ----- Info-based widgets (using the info module) -----

@route('seasonshowdetails')
def route_seasonshowdetails(w, params, limit):
    # Returns TV show details as a single "dummy" item for display at season level
    dbid = params.get('dbid')
    if not dbid:
        log('seasonshowdetails: No dbid provided')
        return None
    show_info = TVShowDetails().get_info(dbid, 'season')
    if not show_info:
        return None
    # Skins can use this to display show stats at season level
    dummy_item = {
        'title': show_info.get('title', ''),
        'plot': f"{show_info.get('episodes', 0)} episodes | {show_info.get('watchedepisodes', 0)} watched",
        'art': show_info.get('art', {}),
        'mediatype': 'tvshow'
    }
    return [dummy_item], 'tvshow', show_info.get('title', '')


@route('pathstatswidget')
def route_pathstatswidget(w, params, limit):
    # Returns path statistics as a displayable item
    path = params.get('path', '')
    if not path:
        return None
    stats = PathStats().get_stats(path)
    stat_items = [
        {
            'title': f"Total: {stats.get('count', 0)}",
            'plot': f"Watched: {stats.get('watched', 0)} | Unwatched: {stats.get('unwatched', 0)}",
            'mediatype': 'video'
        }
    ]
    return stat_items, 'video', 'Statistics'


# ========== LISTING MENUS ==========

def show_root_listing():
    """Show root menu with the widget categories."""
    if HANDLE < 0:
        return

    xbmcplugin.setPluginCategory(HANDLE, 'Flatscan Widgets')
    xbmcplugin.setContent(HANDLE, 'video')

    for category, title, icon in CATEGORIES:
        li = xbmcgui.ListItem(label=f'[B]{title}[/B]')
        li.setArt({'icon': icon})
        li.setInfo('video', {'title': title})
        url = f'plugin://script.flatscan.widgets/?info=category&category={category}'
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)


def show_category_listing(category):
    """Show every registered widget belonging to a category."""
    if HANDLE < 0:
        return

    titles = {cat: title for cat, title, _ in CATEGORIES}
    if category not in titles:
        return

    xbmcplugin.setPluginCategory(HANDLE, titles[category])
    xbmcplugin.setContent(HANDLE, 'video')

    for info_id, entry in ROUTES.items():
        if entry['category'] != category:
            continue
        li = xbmcgui.ListItem(label=entry['label'])
        url = f'plugin://script.flatscan.widgets/?info={info_id}'
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)


# ========== ROUTER ==========

def router():
    """Route plugin requests to appropriate handlers."""
    log('=== ROUTER CALLED ===')
    params = get_params()
    info = params.get('info', '')

    # Handle category folders
    if info == 'category':
        show_category_listing(params.get('category', ''))
        return

    log(f'Plugin called with info={info}, params={params}')

    # Handle root browsing (no info parameter)
    if not info:
        show_root_listing()
        return

    entry = ROUTES.get(info)
    if entry is None:
        log(f'Unknown info type: {info}')
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    # Get limit parameter (default 100)
    limit = int(params.get('limit', 100))

    try:
        result = entry['handler'](Widgets(), params, limit)
        if result is None:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        else:
            items, mediatype, label = result
            add_items_to_directory(items, mediatype, label)
    except Exception as e:
        log(f'Error in router: {e}', level='ERROR')
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


if __name__ == '__main__':
    router()