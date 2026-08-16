#!/usr/bin/python
# coding: utf-8

"""
TV show widgets - All TV-related content.
"""

from logging import INFO
import random
from .base import BaseWidget
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log
from resources.lib.addon import get_setting

# Test log right after imports
log('=== TVSHOWS MODULE LOADED ===', 'INFO')

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
        'thumbnail', 'fanart', 'playcount', 'tvshowid',
        'title', 'showtitle'
    ]

    def __init__(self, handle=None):
        """Initialize with season artwork cache."""
        super().__init__(handle)
        self._season_art_cache = {}
    
    # ========== EPISODE WIDGETS ==========

    def get_recently_added_grouped(self, days=60, limit=999, navigate_to=None):
        """
        Get recently added episodes grouped by time clusters.
        Episodes added within 24h of each other are grouped together.
        """
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        if navigate_to is None:
            raw_setting = get_setting('recentlyadded.navigation', 'Browse')
            log(f'Setting raw value: "{raw_setting}"', 'INFO')
            navigate_to = 'first' if raw_setting == 'First Episode' else 'browse'
            log(f'Navigate to resolved: "{navigate_to}"', 'INFO')
        
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get recently added episodes
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': self.EPISODE_PROPERTIES,
            'sort': self.get_recent_sort(),
            'limits': {'start': 0, 'end': 999}
        })
        
        episodes = result.get('result', {}).get('episodes', [])
        
        # Filter to recent
        recent_eps = [
            ep for ep in episodes 
            if ep.get('dateadded', '')[:10] >= cutoff
        ]
        
        # Group episodes into time clusters (within 20h of the most recent in cluster)
        clusters = []
        current_cluster = []
        cluster_end_time = None  # Track the most recent episode in cluster
        
        # Sort by dateadded descending (most recent first)
        for ep in sorted(recent_eps, key=lambda x: x.get('dateadded', ''), reverse=True):
            ep_time = datetime.fromisoformat(ep.get('dateadded', '').replace('Z', '+00:00'))
            
            if cluster_end_time is None:
                # Start new cluster with most recent episode
                cluster_end_time = ep_time
                current_cluster = [ep]
            elif (cluster_end_time - ep_time).total_seconds() <= 72000:  # 20 hours = 72000 seconds
                # Within 20h of the most recent in cluster, add to current cluster
                current_cluster.append(ep)
                # cluster_end_time stays the same (most recent)
            else:
                # More than 20h from cluster end, save and start new cluster
                clusters.append(current_cluster)
                cluster_end_time = ep_time
                current_cluster = [ep]
        
        # Don't forget the last cluster
        if current_cluster:
            clusters.append(current_cluster)
            
        
        # Now process each cluster with the season/show grouping logic
        items = []
        for cluster in clusters:
            # Group by show within this time cluster
            show_groups = defaultdict(list)
            for ep in cluster:
                show_groups[ep.get('tvshowid')].append(ep)
            
            for show_id, show_eps in show_groups.items():
                # Now apply season vs show grouping logic
                season_groups = defaultdict(list)
                for ep in show_eps:
                    season_groups[ep.get('season')].append(ep)
                
                if len(season_groups) == 1:
                    # Single season cluster
                    season_num = list(season_groups.keys())[0]
                    season_eps = season_groups[season_num]
                    season_eps.sort(key=lambda x: x.get('episode', 0))
                    season_id = season_eps[0].get('seasonid')
                    
                    if len(season_eps) == 1:
                        # Single episode - return as-is
                        ep = season_eps[0]
                        ep['mediatype'] = 'episode'
                        season_art = self._get_season_art(show_id, season_num)
                        ep['art'] = {
                            'thumb': ep.get('thumbnail', ''),
                            'poster': season_art.get('poster', ''),
                            'fanart': season_art.get('fanart', ''),
                        }
                        items.append(ep)
                    else:
                        # Multiple episodes in season - create season group
                        item = self._create_season_group(show_id, season_id, season_num, season_eps)
                        self._set_navigation(item, navigate_to)
                        items.append(item)
                else:
                    # Multiple seasons - create show group
                    item = self._create_show_group(show_id, show_eps, season_groups)
                    self._set_navigation(item, navigate_to)
                    items.append(item)
                
                if len(items) >= limit:
                    break
            
            if len(items) >= limit:
                break
        
        return items

    def _create_season_group(self, show_id, season_id, season_num, episodes):
        """Create a season-level group item."""
        season_info = self._get_season_details(season_id)
        season_art = self._get_season_art(show_id, season_num)
        
        # Sort episodes by episode number
        sorted_eps = sorted(episodes, key=lambda x: x.get('episode', 0))
        first_ep = sorted_eps[0]
        show_title = season_info.get('showtitle', '')
        
        # Build the title: use season title if available, otherwise "Season X"
        season_title = season_info.get('title', '')
        log(f'Season title: {season_title}', 'DEBUG')
        display_title = f"{show_title} - {season_title}"
        
         
        
        # Build episode list for plot
        ep_list = '\n'.join([
            f"Episode {e.get('episode')}: {e.get('title', 'Unknown')}" 
            for e in sorted_eps
        ])
        
        # Construct plot
        plot = f"{ep_list}"
        
        
        return {
            'title': display_title,
            'tvshowtitle': show_title,
            'plot': plot,
            'tvshowid': show_id,
            'season': season_num,
            'season_title': season_title,  # Store for potential skin use
            # 'episode': sorted_eps[0].get('episode'),
            'first_episode_file': first_ep.get('file'),
            'dateadded': sorted_eps[0].get('dateadded'),
            'mediatype': 'season',
            'is_group': True,
            'group_type': 'season',
            'episode_count': len(episodes),
            'art': {
                'poster': season_art.get('poster', ''),
                'fanart': season_art.get('fanart', ''),
                'banner': season_art.get('banner', ''),
            }
        }

    def _create_show_group(self, show_id, episodes, season_groups):
        """Create a show-level group item."""
        sorted_seasons = sorted(season_groups.items())
        
        season_summary = '\n'.join([
            f"Season {s}: {len(eps)} episodes" 
            for s, eps in sorted_seasons
        ])
        
        show_info = self._get_show_details(show_id)
        
        # Find first episode
        all_eps = []
        for eps in season_groups.values():
            all_eps.extend(eps)
        all_eps.sort(key=lambda x: (x.get('season'), x.get('episode')))
        first_ep = all_eps[0]
    
        plot = show_info.get('plot', '')
        if plot:
            plot = f"{plot}\n{season_summary}"
        else:
            plot = season_summary
        
        return {
            'title': show_info.get('title', ''),
            'tvshowtitle': show_info.get('title', ''),
            'plot': plot,
            'tvshowid': show_id,
            'season': first_ep.get('season'),
            # 'episode': first_ep.get('episode'),
            'first_episode_file': first_ep.get('file'),
            'dateadded': first_ep.get('dateadded'),
            'mediatype': 'tvshow',
            'is_group': True,
            'group_type': 'show',
            'season_count': len(season_groups),
            'episode_count': len(episodes),
            'art': show_info.get('art', {})
        }

    def _set_navigation(self, item, navigate_to):
        """Set navigation URL based on preference."""
        show_id = item['tvshowid']
        
        if navigate_to == 'first':
            # Use stored first episode file from the group
            item['file'] = item.get('first_episode_file', '')
            
            if not item['file']:
                # Fallback: fetch from library
                log(f'Warning: first_episode_file not set for {item.get("title")}, fetching from library')
                result = json_rpc_call('VideoLibrary.GetEpisodes', {
                    'tvshowid': int(show_id),
                    'properties': ['file', 'season', 'episode'],
                    'sort': {'method': 'episode'},
                    'limits': {'start': 0, 'end': 1}
                })
                eps = result.get('result', {}).get('episodes', [])
                if eps:
                    item['file'] = eps[0].get('file')
            
            item['is_playable'] = True
            log(f'Set playable file: {item.get("file")}')
            
        else:
            # Navigate to browse view
            if item['group_type'] == 'season':
                item['file'] = f'videodb://tvshows/titles/{show_id}/{item["season"]}/'
            else:
                item['file'] = f'videodb://tvshows/titles/{show_id}/'
            item['is_playable'] = False
            log(f'Set browse URL: {item["file"]}')

    def _get_season_details(self, season_id):
        """Get season details directly by season ID."""
        log(f'Getting season details for season_id: {season_id} (type: {type(season_id)})', 'DEBUG')
        
        if not season_id:
            log('Season ID is empty/None!', 'WARNING')
            return {'title': '', 'art': {}}
        
        try:
            log(f'SEASON_PROPERTIES: {self.SEASON_PROPERTIES}', 'DEBUG')
            
            result = json_rpc_call('VideoLibrary.GetSeasonDetails', {
                'seasonid': int(season_id),
                'properties': self.SEASON_PROPERTIES,
            })
            
            log(f'Raw result: {result}', 'DEBUG')
            
            season = result.get('result', {}).get('seasondetails', {})
            log(f'Season details dict: {season}', 'DEBUG')
            
            title = season.get('title', '')
            log(f'Extracted title: "{title}"', 'DEBUG')

            showtitle = season.get('showtitle', '')
            log(f'Extracted showtitle: "{showtitle}"', 'DEBUG')
            
            return {
                'title': title,
                'art': season.get('art', {}),
                'showtitle': showtitle
            }
        except Exception as e:
            log(f'Failed to get season details: {e}', 'ERROR')
            import traceback
            log(traceback.format_exc(), 'ERROR')
        
        return {'title': '', 'art': {}, 'showtitle': ''}

    def _get_show_details(self, show_id):
        """Get TV show details."""
        try:
            result = json_rpc_call('VideoLibrary.GetTVShowDetails', {
                'tvshowid': int(show_id),
                'properties': self.TVSHOW_PROPERTIES,
            })
            return result.get('result', {}).get('tvshowdetails', {})
        except Exception as e:
            log(f'Failed to get show details: {e}')
        return {}

    def get_recently_aired(self, days=90, limit=20):
        """
        Get episodes that aired in the last X days.
        """
        from datetime import datetime, timedelta
        
        log(f'=== Recently Aired: Starting (last {days} days) ===')
        
        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        log(f'Cutoff date: {cutoff_date}')
        
        # Get episodes - try without firstaired first to see if it exists
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': self.EPISODE_PROPERTIES,
            'sort': self.get_recentlyaired_sort(),
            'limits': {'start': 0, 'end': 50}
        })
        
        episodes = result.get('result', {}).get('episodes', [])
        log(f'Total episodes retrieved: {len(episodes)}')
        
        if not episodes:
            log('No episodes found in library')
            return []
        
        # Debug: Log first few episodes to see data format
        for i, ep in enumerate(episodes[:3]):
            log(f'Episode {i}: {ep.get("showtitle")} S{ep.get("season")}E{ep.get("episode")} - firstaired: "{ep.get("firstaired")}"')
        
        # Filter episodes
        recent_episodes = []
        for ep in episodes:
            airdate = ep.get('firstaired', '')
            
            # Skip if no airdate
            if not airdate:
                continue
                
            # Handle different date formats
            try:
                # Kodi usually returns YYYY-MM-DD
                if airdate >= cutoff_date:
                    ep['mediatype'] = 'episode'
                    
                    # Get season artwork
                    show_id = ep.get('tvshowid')
                    season_num = ep.get('season', 1)
                    season_art = self._get_season_art(show_id, season_num)
                    
                    ep['art'] = {
                        'thumb': ep.get('thumbnail', ''),
                        'poster': season_art.get('poster', ''),
                        'season.poster': season_art.get('poster', ''),
                        'fanart': season_art.get('fanart', ''),
                        'banner': season_art.get('banner', ''),
                    }
                    
                    recent_episodes.append(ep)
                    
                    if len(recent_episodes) >= limit:
                        break
            except Exception as e:
                log(f'Error processing episode airdate "{airdate}": {e}')
        
        log(f'=== Recently Aired: Returning {len(recent_episodes)} episodes ===')
        return recent_episodes
    
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
        """Get season artwork with simple per-season caching."""
        cache_key = (tvshowid, season_num)
        
        if cache_key not in self._season_art_cache:
            try:
                result = json_rpc_call('VideoLibrary.GetSeasons', {
                    'tvshowid': int(tvshowid),
                    'properties': ['art', 'season'],
                })
                
                seasons = result.get('result', {}).get('seasons', [])
                
                # Cache all seasons from this show
                for season in seasons:
                    key = (tvshowid, season.get('season'))
                    self._season_art_cache[key] = season.get('art', {})
                    
            except Exception as e:
                log(f'Failed to get season art: {e}')
                return {}
        
        return self._season_art_cache.get(cache_key, {})
        
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

    def get_sonarr_upcoming(self, days=None):
        """
        Get upcoming episodes from Sonarr.
        """
        import urllib.request
        import urllib.parse
        import json
        from datetime import datetime, timedelta
        
        if not get_setting('sonarr.enabled', 'false') == 'true':
            log('Sonarr not enabled')
            return []
        
        sonarr_url = get_setting('sonarr.url', '').rstrip('/')
        api_key = get_setting('sonarr.apikey', '')
        
        if not sonarr_url or not api_key:
            log('Sonarr not configured')
            return []
        
        if days is None:
            days = int(get_setting('sonarr.days', '7'))
        
        start = datetime.now().strftime('%Y-%m-%d')
        end = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Build URL with parameters
        params = urllib.parse.urlencode({'start': start, 'end': end, 'includeSeries': 'true'})
        url = f'{sonarr_url}/api/v3/calendar?{params}'
        
        headers = {'X-Api-Key': api_key}
        
        try:
            log(f'Fetching Sonarr calendar: {start} to {end}', 'INFO')
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                episodes = json.loads(response.read().decode('utf-8'))

     
            items = []
            for ep in episodes:
                log(f'Full episode keys: {ep.keys()}', 'INFO')
                log(f'Series value: {ep.get("series")}', 'INFO')
                log(f'Episode title: {ep.get("title")}', 'INFO')
                if ep.get('hasFile', False):
                    continue
                
                series = ep.get('series', {})

                log(f'Series: {series.get("title")}, has images: {"images" in series}', 'INFO')
                if 'images' in series:
                    log(f'Images: {series["images"]}', 'INFO')
                else:
                    log(f'No images key in series', 'INFO')
                # Find poster image specifically
                poster_url = ''
                images = series.get('images', [])
                for img in images:
                    if img.get('coverType') == 'poster':
                        poster_url = img.get('remoteUrl', '')
                        break
                
                # If remoteUrl is relative, prepend Sonarr URL
                if poster_url and poster_url.startswith('/'):
                    poster_url = f"{sonarr_url}{poster_url}"

                if series.get('images'):
                    log(f"Images for {series.get('title')}: {series['images']}", 'INFO')
                           
                
                item = {
                    'title': ep.get('title', ''),
                    'showtitle': series.get('title', ''),
                    'season': ep.get('seasonNumber', 0),
                    'episode': ep.get('episodeNumber', 0),
                    'firstaired': ep.get('airDate', ''),
                    'mediatype': 'episode',
                    'plot': ep.get('overview', ''),
                    'tvshowid': series.get('tvdbId', 0),
                    'art': {
                        'poster': poster_url,
                        'fanart': '',  # Could add fanart lookup similarly
                    }
                }
                items.append(item)
            
            log(f'Found {len(items)} upcoming episodes from Sonarr', 'INFO')
            return items
            
        except Exception as e:
            log(f'Sonarr API error: {e}', 'ERROR')
            return []
    
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