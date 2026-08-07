#!/usr/bin/python
# coding: utf-8

"""
Movie widgets - provides movie-specific content.
"""

from .base import BaseWidget
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log

class MovieWidgets(BaseWidget):
    """Widgets for movie content."""
    
    MOVIE_PROPERTIES = [
        'title', 'genre', 'year', 'rating', 'director', 
        'trailer', 'tagline', 'plot', 'plotoutline', 
        'originaltitle', 'lastplayed', 'playcount', 'writer', 
        'studio', 'mpaa', 'cast', 'country', 'imdbnumber', 
        'runtime', 'set', 'showlink', 'streamdetails', 
        'top250', 'votes', 'fanart', 'thumbnail', 'file', 
        'sorttitle', 'resume', 'setid', 'dateadded', 
        'art', 'userrating'
    ]
    
    def get_inprogress(self, limit=20):
        """
        Get movies that are currently in progress.
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of movie dicts
        """
        log(f'Getting in-progress movies (limit: {limit})')
        
        result = json_rpc_call('VideoLibrary.GetMovies', {
            'properties': self.MOVIE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': self.get_lastplayed_sort(),
            'filter': self.get_inprogress_filter()
        })
        
        movies = result.get('result', {}).get('movies', [])
        log(f'Found {len(movies)} in-progress movies')
        return movies
        
    def get_recent(self, limit=20, unwatched_only=False):
        """
        Get recently added movies.
        
        Args:
            limit: Maximum number of items
            unwatched_only: Only return unwatched movies
            
        Returns:
            List of movie dicts
        """
        filters = []
        if unwatched_only:
            filters.append(self.get_unwatched_filter())
            
        params = {
            'properties': self.MOVIE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': self.get_recent_sort()
        }
        
        if filters:
            params['filter'] = {'and': filters} if len(filters) > 1 else filters[0]
            
        result = json_rpc_call('VideoLibrary.GetMovies', params)
        return result.get('result', {}).get('movies', [])
        
    def get_random(self, limit=20):
        """
        Get random movies.
        
        Args:
            limit: Maximum number of items
            
        Returns:
            List of movie dicts
        """
        result = json_rpc_call('VideoLibrary.GetMovies', {
            'properties': self.MOVIE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': self.get_random_sort()
        })
        return result.get('result', {}).get('movies', [])
        
    def get_by_genre(self, genre, limit=20):
        """
        Get movies by genre.
        
        Args:
            genre: Genre name
            limit: Maximum number of items
            
        Returns:
            List of movie dicts
        """
        result = json_rpc_call('VideoLibrary.GetMovies', {
            'properties': self.MOVIE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': self.get_random_sort(),
            'filter': {
                'field': 'genre',
                'operator': 'contains',
                'value': genre
            }
        })
        return result.get('result', {}).get('movies', [])