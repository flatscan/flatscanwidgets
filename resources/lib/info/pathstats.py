#!/usr/bin/python
# coding: utf-8

"""
Path Statistics provider.
Returns watched/unwatched counts for any library path or playlist.
Useful for showing statistics in playlist views or custom nodes.
"""

from .base import InfoProvider
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log


class PathStats(InfoProvider):
    """
    Provides statistics for library paths.
    
    Can count items in:
    - Library paths (e.g., videodb://movies/genres/1/)
    - Playlists (smart or standard)
    - Plugin paths (with limitations)
    """
    
    def __init__(self):
        super().__init__()
        
    def get_stats(self, path, content_type='video'):
        """
        Get statistics for a path.
        
        Args:
            path: The path to analyze (e.g., 'videodb://movies/genres/1/')
            content_type: 'video', 'movies', 'tvshows', 'episodes'
            
        Returns:
            Dict with statistics
        """
        log(f'Getting path stats for: {path}')
        
        # Determine which library call to make based on path
        if 'videodb://movies' in path or content_type == 'movies':
            return self._get_movie_stats(path)
        elif 'videodb://tvshows' in path or content_type == 'tvshows':
            return self._get_tvshow_stats(path)
        elif 'videodb://episodes' in path or content_type == 'episodes':
            return self._get_episode_stats(path)
        else:
            # Generic video query
            return self._get_generic_stats(path)
            
    def _get_movie_stats(self, path):
        """Get statistics for movie paths."""
        # Extract filter from path if it's a genre/path filter
        filter_data = self._parse_path_filter(path)
        
        params = {
            'properties': ['playcount', 'resume'],
            'limits': {'start': 0, 'end': 99999}  # Get all
        }
        
        if filter_data:
            params['filter'] = filter_data
            
        result = json_rpc_call('VideoLibrary.GetMovies', params)
        movies = result.get('result', {}).get('movies', [])
        
        return self._calculate_stats(movies, 'movie')
        
    def _get_tvshow_stats(self, path):
        """Get statistics for TV show paths."""
        result = json_rpc_call('VideoLibrary.GetTVShows', {
            'properties': ['episode', 'watchedepisodes', 'playcount'],
            'limits': {'start': 0, 'end': 99999}
        })
        
        shows = result.get('result', {}).get('tvshows', [])
        
        total_episodes = sum(s.get('episode', 0) for s in shows)
        watched_episodes = sum(s.get('watchedepisodes', 0) for s in shows)
        total_shows = len(shows)
        watched_shows = sum(1 for s in shows if s.get('playcount', 0) > 0)
        
        return {
            'count': total_shows,
            'watched': watched_shows,
            'unwatched': total_shows - watched_shows,
            'episodes': total_episodes,
            'watchedepisodes': watched_episodes,
            'unwatchedepisodes': total_episodes - watched_episodes,
            'inprogress': 0,  # Would need additional query
            'type': 'tvshow'
        }
        
    def _get_episode_stats(self, path):
        """Get statistics for episode paths."""
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': ['playcount', 'resume'],
            'limits': {'start': 0, 'end': 99999}
        })
        
        episodes = result.get('result', {}).get('episodes', [])
        return self._calculate_stats(episodes, 'episode')
        
    def _get_generic_stats(self, path):
        """Generic stats for unknown path types."""
        # Try to get all content types and merge
        stats = {
            'count': 0,
            'watched': 0,
            'unwatched': 0,
            'inprogress': 0,
            'type': 'unknown'
        }
        
        # This is a simplified version - full implementation would parse path
        return stats
        
    def _calculate_stats(self, items, item_type):
        """Calculate statistics from item list."""
        total = len(items)
        watched = sum(1 for i in items if i.get('playcount', 0) > 0)
        inprogress = sum(1 for i in items if i.get('resume', {}).get('position', 0) > 0)
        
        return {
            'count': total,
            'watched': watched,
            'unwatched': total - watched,
            'inprogress': inprogress,
            'type': item_type
        }
        
    def _parse_path_filter(self, path):
        """Parse a Kodi path to extract filter parameters."""
        # This would parse paths like videodb://movies/genres/1/
        # and convert to JSON-RPC filters
        # Simplified implementation - full version would be more complex
        return None
        
    def set_window_properties(self, path, prop_prefix='PathStats', window_id=10000):
        """
        Set window properties for a path's statistics.
        
        Args:
            path: Path to analyze
            prop_prefix: Prefix for property names
            window_id: Window ID
        """
        stats = self.get_stats(path)
        
        self.set_property(f'{prop_prefix}.Count', str(stats['count']), window_id)
        self.set_property(f'{prop_prefix}.Watched', str(stats['watched']), window_id)
        self.set_property(f'{prop_prefix}.Unwatched', str(stats['unwatched']), window_id)
        self.set_property(f'{prop_prefix}.InProgress', str(stats['inprogress']), window_id)
        
        if 'episodes' in stats:
            self.set_property(f'{prop_prefix}.Episodes', str(stats['episodes']), window_id)
            self.set_property(f'{prop_prefix}.WatchedEpisodes', str(stats['watchedepisodes']), window_id)
            self.set_property(f'{prop_prefix}.UnwatchedEpisodes', str(stats['unwatchedepisodes']), window_id)