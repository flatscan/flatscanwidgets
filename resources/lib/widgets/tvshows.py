#!/usr/bin/python
# coding: utf-8

"""
TV show widgets - provides TV show and episode content.
"""

from .base import BaseWidget
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log

class TVShowWidgets(BaseWidget):
    """Widgets for TV show content."""
    
    EPISODE_PROPERTIES = [
        'title', 'plot', 'votes', 'rating', 'writer', 
        'firstaired', 'playcount', 'runtime', 'director', 
        'productioncode', 'season', 'episode', 'originaltitle', 
        'showtitle', 'cast', 'fanart', 'thumbnail', 'file', 
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
    
    def get_inprogress_episodes(self, limit=20):
        """
        Get episodes currently in progress.
        
        Args:
            limit: Maximum number of items
            
        Returns:
            List of episode dicts
        """
        log(f'Getting in-progress episodes (limit: {limit})')
        
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': self.EPISODE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': self.get_lastplayed_sort(),
            'filter': self.get_inprogress_filter()
        })
        
        episodes = result.get('result', {}).get('episodes', [])
        log(f'Found {len(episodes)} in-progress episodes')
        return episodes
        
    def get_next_up(self, limit=20):
        """
        Get next episodes to watch (first unwatched after watched).
        This is more complex - requires finding next episode per show.
        
        Args:
            limit: Maximum number of items
            
        Returns:
            List of episode dicts
        """
        log(f'Getting next up episodes (limit: {limit})')
        
        # Get all unwatched episodes
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': self.EPISODE_PROPERTIES,
            'sort': {'order': 'ascending', 'method': 'episode'},
            'filter': self.get_unwatched_filter()
        })
        
        unwatched = result.get('result', {}).get('episodes', [])
        
        # Group by show and find first unwatched per show
        shows = {}
        for ep in unwatched:
            show_id = ep.get('tvshowid')
            if show_id not in shows:
                shows[show_id] = ep
                
        # Return limited list, sorted by show title
        episodes = list(shows.values())[:limit]
        episodes.sort(key=lambda x: x.get('showtitle', '').lower())
        
        log(f'Found {len(episodes)} next up episodes')
        return episodes
        
    def get_recent_episodes(self, limit=20):
        """
        Get recently added episodes.
        
        Args:
            limit: Maximum number of items
            
        Returns:
            List of episode dicts
        """
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': self.EPISODE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': self.get_recent_sort()
        })
        return result.get('result', {}).get('episodes', [])
        
    def get_recently_updated_shows(self, limit=20):
        """
        Get TV shows that have new episodes.
        
        Args:
            limit: Maximum number of items
            
        Returns:
            List of TV show dicts
        """
        # Get recently added episodes
        recent_eps = self.get_recent_episodes(limit=50)
        
        # Extract unique show IDs
        show_ids = []
        seen_ids = set()
        for ep in recent_eps:
            show_id = ep.get('tvshowid')
            if show_id and show_id not in seen_ids:
                show_ids.append(show_id)
                seen_ids.add(show_id)
                if len(show_ids) >= limit:
                    break
        
        # Get show details
        shows = []
        for show_id in show_ids:
            result = json_rpc_call('VideoLibrary.GetTVShowDetails', {
                'tvshowid': show_id,
                'properties': self.TVSHOW_PROPERTIES
            })
            show = result.get('result', {}).get('tvshowdetails')
            if show:
                shows.append(show)
                
        return shows