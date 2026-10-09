#!/usr/bin/python
# coding: utf-8

"""
TV show widgets - All TV-related content.
"""

import random
import time
from .base import BaseWidget
from resources.lib import cache
from resources.lib.kodi_utils import json_rpc_call
from resources.lib.logger import log
from resources.lib.addon import get_setting

class TVShowWidgets(BaseWidget):
    """TV show and episode widgets."""
    
    # Only what the list items and widget logic use. cast, writer, director,
    # votes and the like roughly double the cost of every query.
    EPISODE_PROPERTIES = [
        'title', 'plot', 'rating', 'firstaired', 'playcount',
        'runtime', 'season', 'episode', 'showtitle', 'thumbnail',
        'file', 'resume', 'tvshowid', 'dateadded', 'lastplayed',
        'art', 'seasonid'
    ]

    TVSHOW_PROPERTIES = [
        'title', 'genre', 'year', 'rating', 'plot',
        'studio', 'mpaa', 'playcount', 'episode',
        'imdbnumber', 'premiered', 'lastplayed',
        'fanart', 'thumbnail', 'file', 'sorttitle',
        'season', 'watchedepisodes', 'dateadded', 'tag',
        'art', 'userrating'
    ]

    # Season titles and cache lifetime for _get_season_details
    SEASON_CACHE_TTL = 24 * 3600

    # Sonarr calendar cache: always fetched for the maximum Days Ahead setting
    # and filtered per widget, so one cache entry serves every `days` value.
    SONARR_CACHE_NAME = 'sonarr_upcoming'
    SONARR_CACHE_DAYS = 30
    SONARR_CACHE_MAX_AGE = 30 * 60

    SEASON_PROPERTIES = [
        'season', 'episode', 'watchedepisodes', 'art', 
        'thumbnail', 'fanart', 'playcount', 'tvshowid',
        'title', 'showtitle'
    ]

    # ========== EPISODE WIDGETS ==========

    def get_recently_added_grouped(self, days=30, limit=100, navigate_to=None):
        """
        Get recently added episodes grouped by time clusters.
        Episodes added within 20h of each other are grouped together.
        """
        from datetime import datetime, timedelta
        from collections import defaultdict

        if navigate_to is None:
            raw_setting = get_setting('recentlyadded.navigation', 'Browse')
            navigate_to = 'first' if raw_setting == 'First Episode' else 'browse'

        # dateadded carries a time, so 'after <date>' means after midnight of that date
        after_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # Get recently added episodes, newest first
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': self.EPISODE_PROPERTIES,
            'sort': self.get_recent_sort(),
            'filter': {'field': 'dateadded', 'operator': 'after', 'value': after_date},
        })

        episodes = result.get('result', {}).get('episodes', [])

        # Pair each episode with its parsed dateadded; skip missing/malformed dates.
        # (fromisoformat, not strptime: strptime raises TypeError in Kodi's embedded Python)
        dated_eps = []
        for ep in episodes:
            try:
                dated_eps.append((datetime.fromisoformat(ep.get('dateadded', '')), ep))
            except (ValueError, TypeError):
                log(f'Skipping episode {ep.get("episodeid")} with invalid dateadded: {ep.get("dateadded")!r}')
        dated_eps.sort(key=lambda pair: pair[0], reverse=True)

        # Group episodes into time clusters (within 20h of the most recent in cluster)
        clusters = []
        current_cluster = []
        cluster_end_time = None  # Track the most recent episode in cluster

        for ep_time, ep in dated_eps:
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
                        ep['art'] = self.episode_art(ep)
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

        # Sort episodes by episode number
        sorted_eps = sorted(episodes, key=lambda x: x.get('episode', 0))
        first_ep = sorted_eps[0]
        art = self.episode_art(first_ep)
        show_title = season_info.get('showtitle', '') or first_ep.get('showtitle', '')

        # Build the title: use season title if available, otherwise "Season X"
        season_title = season_info.get('title', '')
        display_title = f"{show_title} - {season_title}"

        # Build episode list for plot
        plot = '\n'.join([
            f"Episode {e.get('episode')}: {e.get('title', 'Unknown')}"
            for e in sorted_eps
        ])

        return {
            'title': display_title,
            'tvshowtitle': show_title,
            'plot': plot,
            'tvshowid': show_id,
            'season': season_num,
            'season_title': season_title,  # Store for potential skin use
            'first_episode_file': first_ep.get('file'),
            'dateadded': first_ep.get('dateadded'),
            'mediatype': 'season',
            'is_group': True,
            'group_type': 'season',
            'episode_count': len(episodes),
            'art': {
                'poster': art['poster'],
                'fanart': art['fanart'],
                'banner': art['banner'],
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

        # Show-level art is inherited on every episode
        ep_art = first_ep.get('art', {})

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
            'first_episode_file': first_ep.get('file'),
            'dateadded': first_ep.get('dateadded'),
            'mediatype': 'tvshow',
            'is_group': True,
            'group_type': 'show',
            'season_count': len(season_groups),
            'episode_count': len(episodes),
            'art': {
                'poster': ep_art.get('tvshow.poster', ''),
                'fanart': ep_art.get('tvshow.fanart', ''),
                'banner': ep_art.get('tvshow.banner', ''),
            }
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
        """
        Get a season's title and show title by season ID.

        GetSeasonDetails is slow (about 0.1 s per call) and titles rarely
        change, so results are kept in the on-disk cache for a day.
        """
        if not season_id:
            log('Season ID is empty/None!', 'WARNING')
            return {'title': '', 'showtitle': ''}

        key = str(season_id)
        entries = cache.read('season_details') or {}
        now = time.time()

        entry = entries.get(key)
        if entry and now - entry.get('ts', 0) < self.SEASON_CACHE_TTL:
            return {'title': entry['title'], 'showtitle': entry['showtitle']}

        try:
            result = json_rpc_call('VideoLibrary.GetSeasonDetails', {
                'seasonid': int(season_id),
                'properties': ['title', 'showtitle'],
            })
            season = result.get('result', {}).get('seasondetails', {})
            details = {'title': season.get('title', ''), 'showtitle': season.get('showtitle', '')}

            # Drop expired entries while we are rewriting the file anyway
            entries = {k: v for k, v in entries.items() if now - v.get('ts', 0) < self.SEASON_CACHE_TTL}
            entries[key] = dict(details, ts=now)
            cache.write('season_details', entries)
            return details
        except Exception as e:
            log(f'Failed to get season details: {e}', 'ERROR')

        return {'title': '', 'showtitle': ''}

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

        # 'after' is exclusive, so start one day before the cutoff
        after_date = (datetime.now() - timedelta(days=days + 1)).strftime('%Y-%m-%d')

        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'properties': self.EPISODE_PROPERTIES,
            'sort': self.get_recentlyaired_sort(),
            'filter': {'field': 'airdate', 'operator': 'after', 'value': after_date},
            'limits': {'start': 0, 'end': limit}
        })

        episodes = result.get('result', {}).get('episodes', [])
        today = datetime.now().strftime('%Y-%m-%d')

        recent_episodes = []
        for ep in episodes:
            airdate = ep.get('firstaired', '')
            # Skip undated episodes and ones that have not aired yet
            if not airdate or airdate > today:
                continue

            ep['mediatype'] = 'episode'
            ep['art'] = self.episode_art(ep)
            recent_episodes.append(ep)

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

        for ep in episodes:
            ep['mediatype'] = 'episode'
            ep['art'] = self.episode_art(ep)

        log(f'Found {len(episodes)} in-progress episodes')
        return episodes

    def get_next_up(self, limit=20):
        """
        Get next episodes to watch with season posters.
        """
        log(f'Getting next up episodes (limit: {limit})')

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

                    # Season art is inherited on the episode; the show's own art
                    # (already fetched above) takes priority for show-level images
                    show_art = show.get('art', {})
                    art = self.episode_art(ep)
                    art['poster'] = art['poster'] or show_art.get('poster', '')
                    art['tvshow.poster'] = show_art.get('poster', '') or art['tvshow.poster']
                    art['fanart'] = show_art.get('fanart', '') or art['fanart']
                    art['tvshow.fanart'] = art['fanart']
                    art['banner'] = art['banner'] or show_art.get('banner', '')
                    art['clearlogo'] = show_art.get('clearlogo', '') or art['clearlogo']
                    ep['art'] = art

                    next_up.append(ep)

                    if len(next_up) >= limit:
                        break

            log(f'Returning {len(next_up)} next up episodes')
            return next_up

        except Exception as e:
            log(f'Next Up failed: {e}', 'ERROR')
            return []

    def get_recent_episodes(self, limit=20):
        """Get recently added episodes with season posters."""
        episodes = self.get_recently_added('VideoLibrary.GetEpisodes', self.EPISODE_PROPERTIES, limit)

        for ep in episodes:
            ep['mediatype'] = 'episode'
            ep['art'] = self.episode_art(ep)

        return episodes

    def get_episodes_of_season(self, tvshowid, season, limit=100):
        """Get all episodes of a specific season."""
        # tvshowid and season are native GetEpisodes parameters, not filter fields
        result = json_rpc_call('VideoLibrary.GetEpisodes', {
            'tvshowid': int(tvshowid),
            'season': int(season),
            'properties': self.EPISODE_PROPERTIES,
            'limits': {'start': 0, 'end': limit},
            'sort': {'order': 'ascending', 'method': 'episode'},
        })

        episodes = result.get('result', {}).get('episodes', [])
        for ep in episodes:
            ep['mediatype'] = 'episode'
            ep['art'] = self.episode_art(ep)

        return episodes

    # ========== TV SHOW WIDGETS ==========
    
    def get_recently_updated(self, limit=20):
        """Get TV shows that have new episodes."""
        # Only the show ids are needed from the recent episodes
        recent_eps = self.get_recently_added('VideoLibrary.GetEpisodes', ['tvshowid'], 50)
        
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

    def _fetch_sonarr_calendar(self, days):
        """
        Fetch upcoming episodes without a file from the Sonarr calendar.

        Returns:
            List of widget item dicts, or None when Sonarr is not configured
            or the request failed
        """
        import urllib.request
        import urllib.parse
        import json
        from datetime import datetime, timedelta

        sonarr_url = get_setting('sonarr.url', '').rstrip('/')
        api_key = get_setting('sonarr.apikey', '')

        if not sonarr_url or not api_key:
            log('Sonarr not configured')
            return None

        start = datetime.now().strftime('%Y-%m-%d')
        end = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')

        params = urllib.parse.urlencode({'start': start, 'end': end, 'includeSeries': 'true'})
        url = f'{sonarr_url}/api/v3/calendar?{params}'

        try:
            log(f'Fetching Sonarr calendar: {start} to {end}')

            req = urllib.request.Request(url, headers={'X-Api-Key': api_key})
            with urllib.request.urlopen(req, timeout=10) as response:
                episodes = json.loads(response.read().decode('utf-8'))

            items = []
            for ep in episodes:
                if ep.get('hasFile', False):
                    continue

                series = ep.get('series', {})

                # Pick poster and fanart from the series images
                art = {'poster': '', 'fanart': ''}
                for img in series.get('images', []):
                    cover_type = img.get('coverType')
                    if cover_type in art and not art[cover_type]:
                        image_url = img.get('remoteUrl', '')
                        # If remoteUrl is relative, prepend Sonarr URL
                        if image_url.startswith('/'):
                            image_url = f"{sonarr_url}{image_url}"
                        art[cover_type] = image_url

                items.append({
                    'title': ep.get('title', ''),
                    'showtitle': series.get('title', ''),
                    'season': ep.get('seasonNumber', 0),
                    'episode': ep.get('episodeNumber', 0),
                    'firstaired': ep.get('airDate', ''),
                    'mediatype': 'episode',
                    'plot': ep.get('overview', ''),
                    'tvshowid': series.get('tvdbId', 0),
                    'art': art,
                })

            log(f'Found {len(items)} upcoming episodes from Sonarr')
            return items

        except Exception as e:
            log(f'Sonarr API error: {e}', 'ERROR')
            return None

    def refresh_sonarr_cache(self):
        """
        Fetch the Sonarr calendar and store it in the on-disk cache.

        Called by the background service so widget loads never wait on Sonarr
        (or on DNS and the network on the way to it).

        Returns:
            True if the cache was refreshed
        """
        if get_setting('sonarr.enabled', 'false') != 'true':
            return False

        items = self._fetch_sonarr_calendar(self.SONARR_CACHE_DAYS)
        if items is None:
            return False

        cache.write(self.SONARR_CACHE_NAME, {'url': get_setting('sonarr.url', ''), 'items': items})
        return True

    def get_sonarr_upcoming(self, days=None, limit=100):
        """
        Get upcoming episodes from Sonarr.

        Served from the cache the service keeps fresh. If the cache is missing
        or old, fetch live (and fall back to stale data if Sonarr is down).
        """
        from datetime import datetime, timedelta

        if get_setting('sonarr.enabled', 'false') != 'true':
            log('Sonarr not enabled')
            return []

        if days is None:
            days = int(get_setting('sonarr.days', '7'))

        sonarr_url = get_setting('sonarr.url', '')

        if days > self.SONARR_CACHE_DAYS:
            # Longer than the cached window: go straight to Sonarr
            items = self._fetch_sonarr_calendar(days) or []
        else:
            data = cache.read(self.SONARR_CACHE_NAME, max_age=self.SONARR_CACHE_MAX_AGE)
            if not data or data.get('url') != sonarr_url:
                if self.refresh_sonarr_cache():
                    data = cache.read(self.SONARR_CACHE_NAME)
                else:
                    stale = cache.read(self.SONARR_CACHE_NAME)
                    data = stale if stale and stale.get('url') == sonarr_url else None
            items = data['items'] if data else []

        today = datetime.now().strftime('%Y-%m-%d')
        end = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        items = [i for i in items if today <= i.get('firstaired', '') <= end]
        return items[:limit]

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
            
        # Find shows with matching genres. tvshowid is not a filter field, so
        # fetch one extra and drop the reference show here.
        similar = json_rpc_call('VideoLibrary.GetTVShows', {
            'properties': self.TVSHOW_PROPERTIES,
            'limits': {'start': 0, 'end': limit + 1},
            'sort': {'method': 'random'},
            'filter': {'field': 'genre', 'operator': 'contains', 'value': genres[0]}
        }).get('result', {}).get('tvshows', [])

        similar = [show for show in similar if show.get('tvshowid') != int(dbid)][:limit]

        for show in similar:
            show['mediatype'] = 'tvshow'

        return similar