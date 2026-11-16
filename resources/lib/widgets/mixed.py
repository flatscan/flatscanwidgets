#!/usr/bin/python
# coding: utf-8

"""
Mixed media widgets - combines movies, episodes, and other content types.
"""

import random
from .base import BaseWidget
from .movies import MovieWidgets
from .tvshows import TVShowWidgets
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log

class MixedWidgets(BaseWidget):
    """
    Widgets that combine multiple media types.
    This is where the addon's real power is - Kodi can't do this natively.
    """
    
    def __init__(self):
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
