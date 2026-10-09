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

    Counts whatever Kodi lists for the path (Files.GetDirectory), so it works
    for filtered library nodes (e.g. videodb://movies/genres/1/), smart and
    standard playlists, and plugin paths.
    """

    MEDIA_TYPES = ('movie', 'tvshow', 'season', 'episode', 'musicvideo')

    def get_stats(self, path):
        """
        Get statistics for a path.

        Args:
            path: The path to analyze (e.g., 'videodb://movies/genres/1/')

        Returns:
            Dict with count/watched/unwatched/inprogress/type. When the path
            lists TV shows or seasons it also has episodes/watchedepisodes/
            unwatchedepisodes totals.
        """
        log(f'Getting path stats for: {path}')

        result = json_rpc_call('Files.GetDirectory', {
            'directory': path,
            'media': 'video',
            'properties': ['playcount', 'resume', 'episode', 'watchedepisodes'],
        })
        files = result.get('result', {}).get('files', [])

        # Library nodes also list sub-folders (genres, years, ...); only count media
        items = [
            f for f in files
            if f.get('type') in self.MEDIA_TYPES
            or (f.get('filetype') == 'file' and not f.get('type'))
        ]
        return self._calculate_stats(items)

    def _calculate_stats(self, items):
        """Calculate statistics from a list of directory items."""
        total = len(items)
        watched = sum(1 for i in items if i.get('playcount', 0) > 0)

        types = {i.get('type') or 'video' for i in items}
        item_type = types.pop() if len(types) == 1 else ('mixed' if types else 'unknown')

        stats = {
            'count': total,
            'watched': watched,
            'unwatched': total - watched,
            'type': item_type,
        }

        # Shows and seasons: in progress = partly watched; also total the episodes
        group_items = [i for i in items if i.get('type') in ('tvshow', 'season')]
        if group_items:
            episodes = sum(i.get('episode', 0) for i in group_items)
            watched_episodes = sum(i.get('watchedepisodes', 0) for i in group_items)
            stats['episodes'] = episodes
            stats['watchedepisodes'] = watched_episodes
            stats['unwatchedepisodes'] = episodes - watched_episodes

        def in_progress(item):
            if item.get('type') in ('tvshow', 'season'):
                return 0 < item.get('watchedepisodes', 0) < item.get('episode', 0)
            return item.get('resume', {}).get('position', 0) > 0

        stats['inprogress'] = sum(1 for i in items if in_progress(i))
        return stats

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