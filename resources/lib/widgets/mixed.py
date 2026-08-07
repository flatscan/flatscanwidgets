#!/usr/bin/python
# coding: utf-8

"""
Mixed media widgets - combines movies, episodes, and other content types.
"""

import random
from .base import BaseWidget
from .movies import MovieWidgets
from .tvshows import TVShowWidgets
from resources.lib.kodi_utils import json_rpc_call, set_window_property
from resources.lib.logger import log

class MixedWidgets(BaseWidget):
    """
    Widgets that combine multiple media types.
    This is where the addon's real power is - Kodi can't do this natively.
    """
    
    def __init__(self, handle=None):
        super().__init__(handle)
        self.movies = MovieWidgets()
        self.shows = TVShowWidgets()
        
    def get_inprogress_media(self, limit=20):
        """
        Get all in-progress content (movies + episodes).
        This is the "Continue Watching" widget.
        
        Args:
            limit: Maximum total items
            
        Returns:
            List of mixed movie and episode dicts, sorted by last played
        """
        log(f'Getting mixed in-progress media (limit: {limit})')
        
        # Get both types
        movies = self.movies.get_inprogress(limit=limit)
        episodes = self.shows.get_inprogress_episodes(limit=limit)
        
        # Add type identifier to each
        for item in movies:
            item['mediatype'] = 'movie'
            
        for item in episodes:
            item['mediatype'] = 'episode'
            # Add episode-specific display info
            item['display_title'] = f"{item.get('showtitle', '')} - {item.get('title', '')}"
            
        # Combine and sort by lastplayed
        combined = movies + episodes
        combined.sort(
            key=lambda x: x.get('lastplayed', ''), 
            reverse=True
        )
        
        result = combined[:limit]
        log(f'Returning {len(result)} mixed in-progress items')
        return result
        
    def get_suggestions_based_on_watched(self, limit=20):
        """
        Get content suggestions based on recently watched items.
        Finds genres of watched content and returns unwatched matches.
        
        Args:
            limit: Maximum items to return
            
        Returns:
            List of suggested movie and episode dicts
        """
        log(f'Getting suggestions based on watched history')
        
        # Get recently watched movies for genre analysis
        watched_movies = json_rpc_call('VideoLibrary.GetMovies', {
            'properties': ['genre', 'lastplayed'],
            'limits': {'start': 0, 'end': 10},
            'sort': {'order': 'descending', 'method': 'lastplayed'},
            'filter': {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'}
        }).get('result', {}).get('movies', [])
        
        # Get recently watched episodes
        watched_eps = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': ['showtitle', 'lastplayed'],
            'limits': {'start': 0, 'end': 10},
            'sort': {'order': 'descending', 'method': 'lastplayed'},
            'filter': {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'}
        }).get('result', {}).get('episodes', [])
        
        # Extract genres from watched movies
        genres = set()
        for movie in watched_movies:
            for genre in movie.get('genre', []):
                genres.add(genre.lower())
                
        # Get unwatched movies from those genres
        suggestions = []
        if genres:
            genre_list = list(genres)[:3]  # Limit to top 3 genres
            
            for genre in genre_list:
                result = json_rpc_call('VideoLibrary.GetMovies', {
                    'properties': MovieWidgets.MOVIE_PROPERTIES,
                    'limits': {'start': 0, 'end': limit // len(genre_list)},
                    'sort': {'method': 'random'},
                    'filter': {
                        'and': [
                            {'field': 'genre', 'operator': 'contains', 'value': genre},
                            {'field': 'playcount', 'operator': 'is', 'value': '0'}
                        ]
                    }
                })
                movies = result.get('result', {}).get('movies', [])
                for m in movies:
                    m['mediatype'] = 'movie'
                    m['suggestion_reason'] = f"Because you watched {genre} movies"
                suggestions.extend(movies)
        
        # Shuffle and limit
        random.shuffle(suggestions)
        result = suggestions[:limit]
        log(f'Returning {len(result)} suggestions')
        return result
        
    def get_similar_to_current(self, dbid, dbtype, limit=20):
        """
        Get items similar to a specific movie or show.
        
        Args:
            dbid: Database ID of reference item
            dbtype: 'movie' or 'tvshow'
            limit: Maximum items
            
        Returns:
            List of similar items
        """
        log(f'Getting similar to {dbtype} {dbid}')
        
        # Get reference item details
        if dbtype == 'movie':
            result = json_rpc_call('VideoLibrary.GetMovieDetails', {
                'movieid': int(dbid),
                'properties': ['genre', 'year', 'cast', 'director']
            })
            reference = result.get('result', {}).get('moviedetails', {})
            
            # Find movies with matching genres
            genres = reference.get('genre', [])
            if genres:
                similar = json_rpc_call('VideoLibrary.GetMovies', {
                    'properties': MovieWidgets.MOVIE_PROPERTIES,
                    'limits': {'start': 0, 'end': limit},
                    'sort': {'method': 'random'},
                    'filter': {
                        'and': [
                            {'field': 'genre', 'operator': 'contains', 'value': genres[0]},
                            {'field': 'playcount', 'operator': 'is', 'value': '0'}
                        ]
                    }
                }).get('result', {}).get('movies', [])
                
                for m in similar:
                    m['mediatype'] = 'movie'
                return similar
                
        elif dbtype == 'tvshow':
            result = json_rpc_call('VideoLibrary.GetTVShowDetails', {
                'tvshowid': int(dbid),
                'properties': ['genre', 'studio']
            })
            reference = result.get('result', {}).get('tvshowdetails', {})
            
            # Find shows with matching genres
            genres = reference.get('genre', [])
            if genres:
                similar = json_rpc_call('VideoLibrary.GetTVShows', {
                    'properties': TVShowWidgets.TVSHOW_PROPERTIES,
                    'limits': {'start': 0, 'end': limit},
                    'sort': {'method': 'random'},
                    'filter': {
                        'and': [
                            {'field': 'genre', 'operator': 'contains', 'value': genres[0]},
                            {'field': 'playcount', 'operator': 'is', 'value': '0'}
                        ]
                    }
                }).get('result', {}).get('tvshows', [])
                
                for s in similar:
                    s['mediatype'] = 'tvshow'
                return similar
        
        return []
        
    def get_by_random_genre(self, limit=20):
        """
        Get content from a random genre that exists in the library.
        Returns both movies and episodes from the genre.
        
        Args:
            limit: Maximum items
            
        Returns:
            Dict with 'genre' name and 'items' list
        """
        # Get all genres from movies
        genres_result = json_rpc_call('VideoLibrary.GetGenres', {
            'type': 'movie'
        })
        genres = genres_result.get('result', {}).get('genres', [])
        
        if not genres:
            return {'genre': '', 'items': []}
            
        # Pick random genre
        selected = random.choice(genres)
        genre_name = selected.get('label', '')
        
        log(f'Selected random genre: {genre_name}')
        
        # Get movies in this genre
        movies = json_rpc_call('VideoLibrary.GetMovies', {
            'properties': MovieWidgets.MOVIE_PROPERTIES,
            'limits': {'start': 0, 'end': limit // 2},
            'sort': {'method': 'random'},
            'filter': {
                'field': 'genre',
                'operator': 'contains',
                'value': genre_name
            }
        }).get('result', {}).get('movies', [])
        
        for m in movies:
            m['mediatype'] = 'movie'
            
        # Get TV shows in this genre  
        shows = json_rpc_call('VideoLibrary.GetTVShows', {
            'properties': TVShowWidgets.TVSHOW_PROPERTIES,
            'limits': {'start': 0, 'end': limit // 2},
            'sort': {'method': 'random'},
            'filter': {
                'field': 'genre',
                'operator': 'contains',
                'value': genre_name
            }
        }).get('result', {}).get('tvshows', [])
        
        for s in shows:
            s['mediatype'] = 'tvshow'
            
        # Combine
        combined = movies + shows
        random.shuffle(combined)
        
        return {
            'genre': genre_name,
            'items': combined[:limit]
        }
        
    def get_more_by_actor(self, actor_name, limit=20):
        """
        Get movies and episodes featuring a specific actor.
        
        Args:
            actor_name: Name of the actor
            limit: Maximum items
            
        Returns:
            List of movies and episodes
        """
        log(f'Getting content for actor: {actor_name}')
        
        # Get movies with this actor
        movies = json_rpc_call('VideoLibrary.GetMovies', {
            'properties': MovieWidgets.MOVIE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'filter': {
                'field': 'actor',
                'operator': 'contains',
                'value': actor_name
            }
        }).get('result', {}).get('movies', [])
        
        for m in movies:
            m['mediatype'] = 'movie'
            
        # Note: Getting episodes by actor requires different approach
        # Kodi's episode filter doesn't support actor directly
        # We'd need to get shows with actor, then episodes from those shows
        
        return movies[:limit]