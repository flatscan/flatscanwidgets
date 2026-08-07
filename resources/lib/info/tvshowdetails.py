#!/usr/bin/python
# coding: utf-8

"""
TV Show Details provider.
Returns show-level information when browsing seasons.
Useful for showing total episode counts, watched status, etc. at season level.
"""

from .base import InfoProvider
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log


class TVShowDetails(InfoProvider):
    """
    Provides TV show details at the season level.
    
    When browsing seasons, Kodi only provides season-specific info.
    This provider returns show-level data (total episodes, watched, rating, etc.)
    that can be displayed while viewing seasons.
    """
    
    def __init__(self):
        super().__init__()
        self.property_prefix = 'tvshow'
        
    def get_info(self, dbid, idtype='season'):
        """
        Get TV show details by season or episode DBID.
        
        Args:
            dbid: Database ID
            idtype: 'season' or 'episode'
            
        Returns:
            Dict with show details
        """
        log(f'Getting TV show details for {idtype} {dbid}')
        
        # Get TV show ID from season or episode
        tvshow_id = self._get_tvshow_id(dbid, idtype)
        
        if not tvshow_id:
            log(f'Could not find TV show ID for {idtype} {dbid}')
            return {}
            
        # Get full TV show details
        result = json_rpc_call('VideoLibrary.GetTVShowDetails', {
            'tvshowid': int(tvshow_id),
            'properties': [
                'title', 'rating', 'plot', 'studio', 'genre',
                'episode', 'season', 'watchedepisodes',
                'mpaa', 'cast', 'art'
            ]
        })
        
        show = result.get('result', {}).get('tvshowdetails', {})
        
        if not show:
            return {}
            
        # Calculate unwatched episodes
        total = show.get('episode', 0)
        watched = show.get('watchedepisodes', 0)
        unwatched = total - watched
        
        info = {
            'dbid': tvshow_id,
            'title': show.get('title', ''),
            'rating': str(show.get('rating', 0)),
            'plot': show.get('plot', ''),
            'studio': show.get('studio', []),
            'genre': show.get('genre', []),
            'seasons': show.get('season', 0),
            'episodes': total,
            'watchedepisodes': watched,
            'unwatchedepisodes': unwatched,
            'mpaa': show.get('mpaa', ''),
            'art': show.get('art', {})
        }
        
        log(f'Returned show info: {info["title"]} ({info["episodes"]} episodes)')
        return info
        
    def set_window_properties(self, dbid, idtype='season', window_id=10000):
        """
        Set window properties for skin consumption.
        
        Args:
            dbid: Database ID
            idtype: 'season' or 'episode'
            window_id: Window ID to set properties on
        """
        info = self.get_info(dbid, idtype)
        
        if not info:
            self.clear_properties(window_id)
            return
            
        # Set properties with prefix
        prefix = self.property_prefix
        
        self.set_property(f'{prefix}.dbid', info['dbid'], window_id)
        self.set_property(f'{prefix}.title', info['title'], window_id)
        self.set_property(f'{prefix}.rating', info['rating'], window_id)
        self.set_property(f'{prefix}.plot', info['plot'], window_id)
        self.set_property(f'{prefix}.seasons', str(info['seasons']), window_id)
        self.set_property(f'{prefix}.episodes', str(info['episodes']), window_id)
        self.set_property(f'{prefix}.watchedepisodes', str(info['watchedepisodes']), window_id)
        self.set_property(f'{prefix}.unwatchedepisodes', str(info['unwatchedepisodes']), window_id)
        self.set_property(f'{prefix}.mpaa', info['mpaa'], window_id)
        
        # Art
        art = info.get('art', {})
        self.set_property(f'{prefix}.fanart', art.get('fanart', ''), window_id)
        self.set_property(f'{prefix}.poster', art.get('poster', ''), window_id)
        self.set_property(f'{prefix}.clearlogo', art.get('clearlogo', ''), window_id)
        
    def _get_tvshow_id(self, dbid, idtype):
        """Get TV show ID from season or episode ID."""
        if idtype == 'tvshow':
            return dbid
            
        elif idtype == 'season':
            result = json_rpc_call('VideoLibrary.GetSeasonDetails', {
                'seasonid': int(dbid),
                'properties': ['tvshowid']
            })
            return result.get('result', {}).get('seasondetails', {}).get('tvshowid')
            
        elif idtype == 'episode':
            result = json_rpc_call('VideoLibrary.GetEpisodeDetails', {
                'episodeid': int(dbid),
                'properties': ['tvshowid']
            })
            return result.get('result', {}).get('episodedetails', {}).get('tvshowid')
            
        return None