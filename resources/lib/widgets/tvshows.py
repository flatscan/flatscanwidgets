#!/usr/bin/python
# coding: utf-8

"""
TV show widgets - All TV-related content.
"""

import random
from .base import BaseWidget
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log


class TVShowWidgets(BaseWidget):
    """TV show and episode widgets."""
    
    EPISODE_PROPERTIES = [
    'title', 'plot', 'votes', 'rating', 'writer', 
    'firstaired', 'playcount', 'runtime', 'director', 
    'productioncode', 'season', 'episode', 'originaltitle', 
    'showtitle', 'cast', 'fanart', 'thumbnail', 
    'file',  # <-- Make sure this is included
    'resume', 'tvshowid', 'dateadded', 'lastplayed', 
    'art', 'seasonid'
    ]
    
    TVSHOW_PROPERTIES = [
        'title', 'genre', 'year', 'rating', 'plot', 
        'studio', 'mpaa', 'cast', 'playcount', 'episode', 
        'imdbnumber', 'premiered', 'votes', 'lastplayed', 
        'fanart', 'thumbnail', 'file', 'originaltitle', 
        'sorttitle', 'episodeguide', 'season', 'watchedepisodes', 
        'dateadded', 'tag', 'art', 'userrating'
    ]
    
    SEASON_PROPERTIES = [
        'season', 'episode', 'watchedepisodes', 'art', 
        'thumbnail', 'fanart', 'playcount', 'tvshowid'
    ]
    
    # ========== EPISODE WIDGETS ==========
    
    def get_inprogress_episodes(self, limit=20):
        """Get episodes currently in progress with season posters."""
        log(f'Getting in-progress episodes (limit: {limit})')
        
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': self.EPISODE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': self.get_lastplayed_sort(),
            'filter': self.get_inprogress_filter()
        })
        
        episodes = result.get('result', {}).get('episodes', [])
        
        # Get season artwork for each episode
        for ep in episodes:
            ep['mediatype'] = 'episode'
            
            show_id = ep.get('tvshowid')
            season_num = ep.get('season', 1)
            
            # Get season poster
            season_art = self._get_season_art(show_id, season_num)
            
            # Build art with season poster
            ep['art'] = {
                'thumb': ep.get('thumbnail', ''),  # Episode thumbnail
                'poster': season_art.get('poster', ''),  # Season poster
                'season.poster': season_art.get('poster', ''),
                'fanart': season_art.get('fanart', '') or ep.get('art', {}).get('fanart', ''),
                'banner': season_art.get('banner', ''),
            }
        
        log(f'Found {len(episodes)} in-progress episodes')
        return episodes
    
    def get_next_up(self, limit=20):
        """
        Get next episodes to watch with season posters.
        """
        log('=== Next Up: Starting ===')
        
        try:
            # Get shows with watched episodes
            shows_result = json_rpc_call('VideoLibrary.GetTVShows', {
                'properties': ['title', 'watchedepisodes', 'episode', 'lastplayed', 'art'],
                'sort': {'order': 'descending', 'method': 'lastplayed'},
                'limits': {'start': 0, 'end': 30}
            })
            
            shows = shows_result.get('result', {}).get('tvshows', [])
            next_up = []
            
            for show in shows:
                show_id = show.get('tvshowid')
                watched = show.get('watchedepisodes', 0)
                total = show.get('episode', 0)
                
                if watched == 0 or watched >= total:
                    continue
                
                # Get first unwatched episode
                ep_result = json_rpc_call('VideoLibrary.GetEpisodes', {
                    'tvshowid': int(show_id),
                    'properties': self.EPISODE_PROPERTIES,
                    'sort': {'order': 'ascending', 'method': 'episode'},
                    'filter': {'field': 'playcount', 'operator': 'is', 'value': '0'},
                    'limits': {'start': 0, 'end': 1}
                })
                
                episodes = ep_result.get('result', {}).get('episodes', [])
                
                if episodes:
                    ep = episodes[0]
                    ep['mediatype'] = 'episode'
                    ep['show_lastplayed'] = show.get('lastplayed', '')
                    
                    # Get season artwork for this episode's season
                    season_num = ep.get('season', 1)
                    season_art = self._get_season_art(show_id, season_num)
                    
                    # Build art dict with season poster as priority
                    ep['art'] = {
                        'thumb': ep.get('thumbnail', ''),  # Episode thumbnail
                        'poster': season_art.get('poster', ''),  # Season poster (main)
                        'season.poster': season_art.get('poster', ''),
                        'tvshow.poster': show.get('art', {}).get('poster', ''),  # Fallback
                        'fanart': season_art.get('fanart', '') or show.get('art', {}).get('fanart', ''),
                        'tvshow.fanart': show.get('art', {}).get('fanart', ''),
                        'banner': season_art.get('banner', '') or show.get('art', {}).get('banner', ''),
                        'clearlogo': show.get('art', {}).get('clearlogo', ''),
                    }
                    
                    next_up.append(ep)
                    
                    if len(next_up) >= limit:
                        break
            
            log(f'=== Next Up: Returning {len(next_up)} episodes ===')
            return next_up
            
        except Exception as e:
            log(f'Next Up failed: {e}', 'ERROR')
            return []

    def _get_season_art(self, tvshowid, season_num):
        """
        Get artwork for a specific season.
        """
        try:
            result = json_rpc_call('VideoLibrary.GetSeasons', {
                'tvshowid': int(tvshowid),
                'properties': ['art', 'season'],
            })
            
            seasons = result.get('result', {}).get('seasons', [])
            
            for season in seasons:
                if season.get('season') == season_num:
                    return season.get('art', {})
                    
        except Exception as e:
            log(f'Failed to get season art: {e}')
        
        return {}
        
    def get_recent_episodes(self, limit=20):
        """Get recently added episodes with season posters."""
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': self.EPISODE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': self.get_recent_sort()
        })
        
        episodes = result.get('result', {}).get('episodes', [])
        
        for ep in episodes:
            ep['mediatype'] = 'episode'
            
            show_id = ep.get('tvshowid')
            season_num = ep.get('season', 1)
            
            # Get season poster
            season_art = self._get_season_art(show_id, season_num)
            
            ep['art'] = {
                'thumb': ep.get('thumbnail', ''),
                'poster': season_art.get('poster', ''),
                'season.poster': season_art.get('poster', ''),
                'fanart': season_art.get('fanart', '') or ep.get('art', {}).get('fanart', ''),
                'banner': season_art.get('banner', ''),
            }
        
        return episodes
    
    def get_episodes_of_season(self, tvshowid, season, limit=100):
        """Get all episodes of a specific season."""
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': self.EPISODE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': {'order': 'ascending', 'method': 'episode'},
            'filter': {
                'and': [
                    {'field': 'tvshowid', 'operator': 'is', 'value': str(tvshowid)},
                    {'field': 'season', 'operator': 'is', 'value': str(season)}
                ]
            }
        })
        
        episodes = result.get('result', {}).get('episodes', [])
        for ep in episodes:
            ep['mediatype'] = 'episode'
            
        return episodes
    
    # ========== TV SHOW WIDGETS ==========
    
    def get_recently_updated(self, limit=20):
        """Get TV shows that have new episodes."""
        # Get recently added episodes
        recent_eps = self.get_recent_episodes(limit=50)
        
        # Extract unique show IDs in order
        show_ids = []
        seen = set()
        for ep in recent_eps:
            show_id = ep.get('tvshowid')
            if show_id and show_id not in seen:
                show_ids.append(show_id)
                seen.add(show_id)
                if len(show_ids) >= limit:
                    break
        
        # Get show details
        shows = []
        for show_id in show_ids:
            result = json_rpc_call('VideoLibrary.GetTVShowDetails', {
                'tvshowid': int(show_id),
                'properties': self.TVSHOW_PROPERTIES
            })
            show = result.get('result', {}).get('tvshowdetails')
            if show:
                show['mediatype'] = 'tvshow'
                shows.append(show)
                
        return shows
    
    def get_by_random_genre(self, limit=20):
        """Get TV shows from a random genre."""
        # Get all genres
        genres_result = json_rpc_call('VideoLibrary.GetGenres', {
            'type': 'tvshow'
        })
        genres = genres_result.get('result', {}).get('genres', [])
        
        if not genres:
            return []
            
        # Pick random genre
        selected = random.choice(genres)
        genre_name = selected.get('label', '')
        
        log(f'Selected random TV genre: {genre_name}')
        
        # Get shows in this genre
        result = json_rpc_call('VideoLibrary.GetTVShows', {
            'properties': self.TVSHOW_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': {'method': 'random'},
            'filter': {
                'field': 'genre',
                'operator': 'contains',
                'value': genre_name
            }
        })
        
        shows = result.get('result', {}).get('tvshows', [])
        for show in shows:
            show['mediatype'] = 'tvshow'
            show['selected_genre'] = genre_name
            
        return shows
    
    def get_seasons(self, tvshowid, limit=100):
        """Get seasons of a TV show."""
        result = json_rpc_call('VideoLibrary.GetSeasons', {
            'tvshowid': int(tvshowid),
            'properties': self.SEASON_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': {'order': 'ascending', 'method': 'season'}
        })
        
        seasons = result.get('result', {}).get('seasons', [])
        for season in seasons:
            season['mediatype'] = 'season'
            
        return seasons
    
    def get_genres(self):
        """Get list of TV show genres."""
        result = json_rpc_call('VideoLibrary.GetGenres', {
            'type': 'tvshow'
        })
        
        genres = result.get('result', {}).get('genres', [])
        for genre in genres:
            genre['mediatype'] = 'genre'
            
        return genres
    
    # ========== SMART/SUGGESTION WIDGETS ==========
    
    def get_suggestions(self, limit=20):
        """
        Get TV show suggestions based on watched history.
        Finds unwatched shows in genres of watched shows.
        """
        log(f'Getting TV show suggestions (limit: {limit})')
        
        # Get recently watched shows
        watched_result = json_rpc_call('VideoLibrary.GetTVShows', {
            'properties': ['genre', 'lastplayed'],
            'limits': {'start': 0, 'end': 10},
            'sort': {'order': 'descending', 'method': 'lastplayed'},
            'filter': {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'}
        })
        
        watched = watched_result.get('result', {}).get('tvshows', [])
        
        # Extract genres from watched shows
        genres = set()
        for show in watched:
            for genre in show.get('genre', []):
                genres.add(genre.lower())
        
        # Get unwatched shows from those genres
        suggestions = []
        if genres:
            for genre in list(genres)[:3]:
                result = json_rpc_call('VideoLibrary.GetTVShows', {
                    'properties': self.TVSHOW_PROPERTIES,
                    'limits': {'start': 0, 'end': limit // len(genres)},
                    'sort': {'method': 'random'},
                    'filter': {
                        'and': [
                            {'field': 'genre', 'operator': 'contains', 'value': genre},
                            {'field': 'playcount', 'operator': 'is', 'value': '0'}
                        ]
                    }
                })
                shows = result.get('result', {}).get('tvshows', [])
                for show in shows:
                    show['mediatype'] = 'tvshow'
                    show['suggestion_reason'] = f'Similar to {genre} shows you watched'
                suggestions.extend(shows)
        
        random.shuffle(suggestions)
        return suggestions[:limit]
    
    def get_similar(self, dbid, limit=20):
        """Get TV shows similar to the specified show."""
        log(f'Getting shows similar to {dbid}')
        
        # Get reference show details
        result = json_rpc_call('VideoLibrary.GetTVShowDetails', {
            'tvshowid': int(dbid),
            'properties': ['genre', 'studio']
        })
        
        reference = result.get('result', {}).get('tvshowdetails', {})
        genres = reference.get('genre', [])
        
        if not genres:
            return []
            
        # Find shows with matching genres
        similar = json_rpc_call('VideoLibrary.GetTVShows', {
            'properties': self.TVSHOW_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': {'method': 'random'},
            'filter': {
                'and': [
                    {'field': 'genre', 'operator': 'contains', 'value': genres[0]},
                    {'field': 'tvshowid', 'operator': 'isnot', 'value': str(dbid)}
                ]
            }
        }).get('result', {}).get('tvshows', [])
        
        for show in similar:
            show['mediatype'] = 'tvshow'
            
        return similar