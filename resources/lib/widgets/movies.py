#!/usr/bin/python
# coding: utf-8

"""
Movie widgets - provides movie-specific content.
"""

from datetime import datetime, timedelta
from .base import BaseWidget
from resources.lib.addon import get_setting
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log

class MovieWidgets(BaseWidget):
    """Widgets for movie content."""
    
    # Only what the list items use; cast, writer, director, streamdetails and
    # the like are never read from widget items and make queries much slower.
    MOVIE_PROPERTIES = [
        'title', 'genre', 'year', 'rating', 'plot',
        'lastplayed', 'playcount', 'studio', 'mpaa',
        'country', 'imdbnumber', 'runtime', 'set',
        'fanart', 'thumbnail', 'file', 'sorttitle',
        'resume', 'setid', 'dateadded', 'art', 'userrating',
        'premiered'
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
        
    def get_recently_released(self, days=365, limit=20, unwatched_only=False):
        """
        Get movies released (premiered) in the last X days, newest first.

        Kodi has no premiered filter for movies, so the query is narrowed by
        year and the exact date window and sort are applied here. Movies with
        a future premiered date (pre-release copies) are included.

        Args:
            days: How far back to look
            limit: Maximum number of items
            unwatched_only: Only return unwatched movies

        Returns:
            List of movie dicts
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        filters = [{'field': 'year', 'operator': 'greaterthan', 'value': str(int(cutoff[:4]) - 1)}]
        if unwatched_only:
            filters.append(self.get_unwatched_filter())

        result = json_rpc_call('VideoLibrary.GetMovies', {
            'properties': self.MOVIE_PROPERTIES,
            'filter': {'and': filters} if len(filters) > 1 else filters[0]
        })
        movies = result.get('result', {}).get('movies', [])

        # Undated movies compare as '' and fall before the cutoff
        released = [m for m in movies if m.get('premiered', '') >= cutoff]
        released.sort(key=lambda m: m['premiered'], reverse=True)
        log(f'Found {len(released)} movies released since {cutoff}')
        return released[:limit]

    def _get_sets(self):
        """
        Get the movies of every movie set, each set in release order.

        Listing every set movie with full properties takes over a second, so
        only the fields needed to work out watch progress are requested.

        Sets named in the nextincollection.exclude setting (comma-separated,
        case-insensitive) are skipped, for themed sets that are not a series.

        Returns:
            Dict of setid -> list of lean movie dicts
        """
        excluded = {name.strip().lower() for name in get_setting('nextincollection.exclude', '').split(',')
                    if name.strip()}

        result = json_rpc_call('VideoLibrary.GetMovies', {
            'properties': ['setid', 'set', 'playcount', 'premiered', 'year', 'title',
                           'sorttitle', 'imdbnumber', 'lastplayed'],
            'filter': {'field': 'set', 'operator': 'isnot', 'value': ''}
        })
        movies = result.get('result', {}).get('movies', [])

        sets = {}
        for movie in movies:
            if movie.get('setid') and movie.get('set', '').lower() not in excluded:
                sets.setdefault(movie['setid'], []).append(movie)

        for set_movies in sets.values():
            set_movies.sort(key=lambda m: (m.get('premiered') or str(m.get('year') or 9999),
                                           m.get('sorttitle') or m.get('title', '')))
        return sets

    @staticmethod
    def _film_key(movie):
        """Identify a film across copies (editions, versions) of it."""
        return movie.get('imdbnumber') or movie.get('title')

    def _next_in_set(self, set_movies):
        """
        Pick the first unwatched movie after the furthest one watched, or None.

        A second copy of a watched movie sorts beside it and must not come up
        as the next one.
        """
        watched = [i for i, m in enumerate(set_movies) if m.get('playcount', 0) > 0]
        if not watched:
            return None
        seen = {self._film_key(m) for m in set_movies if m.get('playcount', 0) > 0}
        for movie in set_movies[watched[-1] + 1:]:
            if not movie.get('playcount', 0) and self._film_key(movie) not in seen:
                return movie
        return None

    def get_next_in_collection(self, limit=20):
        """
        Get the next movie to watch in each movie set that has been started.

        Each set is put in release order and the pick is the first unwatched
        movie after the furthest one watched, as Next Up does for episodes.
        Sets are ordered by when one of their movies was last played. The
        sets are listed lean (see _get_sets) and details are fetched for the
        picks only.

        Args:
            limit: Maximum number of items

        Returns:
            List of movie dicts
        """
        sets = self._get_sets()

        picks = []
        for set_movies in sets.values():
            pick = self._next_in_set(set_movies)
            if not pick:
                continue
            lastplayed = max(m.get('lastplayed', '') for m in set_movies)
            picks.append((lastplayed, pick['movieid']))

        picks.sort(key=lambda p: p[0], reverse=True)
        log(f'Found next movies in {len(picks)} of {len(sets)} collections')

        details = []
        for _, movieid in picks[:limit]:
            result = json_rpc_call('VideoLibrary.GetMovieDetails', {
                'movieid': movieid,
                'properties': self.MOVIE_PROPERTIES
            })
            movie = result.get('result', {}).get('moviedetails')
            if movie:
                details.append(movie)
        return details

    def get_collections_in_progress(self, limit=20):
        """
        Get movie sets that are partly watched, most recently watched first.

        A set is in progress when at least one film in it is watched and at
        least one is not, in any order. Copies of the same film count once.

        Args:
            limit: Maximum number of items

        Returns:
            List of set dicts (mediatype 'set') with the set's own artwork
        """
        sets = self._get_sets()

        progress = []
        for setid, set_movies in sets.items():
            films = {}
            for movie in set_movies:
                key = self._film_key(movie)
                films[key] = films.get(key, False) or movie.get('playcount', 0) > 0
            watched = sum(films.values())
            if not 0 < watched < len(films):
                continue
            lastplayed = max(m.get('lastplayed', '') for m in set_movies)
            progress.append((lastplayed, setid, watched, len(films), self._next_in_set(set_movies)))

        progress.sort(key=lambda p: p[0], reverse=True)
        log(f'Found {len(progress)} of {len(sets)} collections in progress')
        if not progress:
            return []

        result = json_rpc_call('VideoLibrary.GetMovieSets', {'properties': ['title', 'plot', 'art']})
        set_details = {s['setid']: s for s in result.get('result', {}).get('sets', [])}

        items = []
        for lastplayed, setid, watched, total, next_movie in progress[:limit]:
            details = set_details.get(setid, {})
            art = details.get('art', {})
            items.append({
                'mediatype': 'set',
                'setid': setid,
                'title': details.get('title') or sets[setid][0].get('set', ''),
                'plot': details.get('plot', ''),
                'art': art,
                'thumbnail': art.get('thumb') or art.get('poster', ''),
                'watched': watched,
                'total': total,
                'next_title': next_movie.get('title', '') if next_movie else '',
                'lastplayed': lastplayed,
            })
        return items

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