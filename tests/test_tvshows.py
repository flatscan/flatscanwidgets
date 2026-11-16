#!/usr/bin/python
# coding: utf-8

"""Tests for TVShowWidgets (resources/lib/widgets/tvshows.py)."""

import os
import time
import unittest
from datetime import datetime, timedelta
from unittest import mock

from resources.lib import cache
from resources.lib.widgets.tvshows import TVShowWidgets
from tests import kodistub

NOW = datetime(2026, 11, 16, 20, 0, 0)


def ep(show, season, episode, hours_ago, **extra):
    """An episode as VideoLibrary.GetEpisodes returns it, added hours_ago before NOW."""
    item = {
        'episodeid': show * 1000 + season * 100 + episode,
        'tvshowid': show,
        'seasonid': show * 100 + season,
        'season': season,
        'episode': episode,
        'title': f'Episode {episode}',
        'showtitle': f'Show {show}',
        'file': f'/tv/{show}/s{season}e{episode}.mkv',
        'dateadded': (NOW - timedelta(hours=hours_ago)).strftime('%Y-%m-%d %H:%M:%S'),
        'art': {'tvshow.poster': f'poster{show}', 'tvshow.fanart': f'fanart{show}'},
    }
    item.update(extra)
    return item


class RecentlyAddedGroupedTest(unittest.TestCase):

    def group(self, episodes, navigate_to='browse', limit=100):
        widget = TVShowWidgets()
        rpc = mock.patch('resources.lib.widgets.tvshows.json_rpc_call',
                         return_value={'result': {'episodes': episodes}})
        season = mock.patch.object(TVShowWidgets, '_get_season_details',
                                   side_effect=lambda sid: {'title': f'Season {sid % 100}',
                                                            'showtitle': f'Show {sid // 100}'})
        show = mock.patch.object(TVShowWidgets, '_get_show_details',
                                 side_effect=lambda tid: {'title': f'Show {tid}', 'plot': ''})
        with rpc, season, show:
            return widget.get_recently_added_grouped(navigate_to=navigate_to, limit=limit)

    def test_single_episode_stays_an_episode(self):
        items = self.group([ep(1, 1, 1, 1)])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['mediatype'], 'episode')
        self.assertEqual(items[0]['art']['poster'], 'poster1')

    def test_same_season_within_20_hours_becomes_season_group(self):
        items = self.group([ep(1, 2, 3, 1), ep(1, 2, 1, 19), ep(1, 2, 2, 10)])
        self.assertEqual(len(items), 1)
        group = items[0]
        self.assertEqual(group['mediatype'], 'season')
        self.assertEqual(group['group_type'], 'season')
        self.assertEqual(group['episode_count'], 3)
        self.assertEqual(group['season'], 2)
        self.assertEqual(group['title'], 'Show 1 - Season 2')
        self.assertEqual(group['first_episode_file'], '/tv/1/s2e1.mkv')
        self.assertEqual(group['file'], 'videodb://tvshows/titles/1/2/')
        self.assertFalse(group['is_playable'])

    def test_more_than_20_hours_apart_splits_clusters(self):
        items = self.group([ep(1, 1, 2, 1), ep(1, 1, 1, 22)])
        self.assertEqual([i['mediatype'] for i in items], ['episode', 'episode'])
        self.assertEqual([i['episode'] for i in items], [2, 1])

    def test_window_is_measured_from_newest_episode_in_cluster(self):
        # 1 h, 15 h and 25 h ago: the last is only 10 h after the middle one but
        # 24 h after the newest, so it starts a new cluster.
        items = self.group([ep(1, 1, 3, 1), ep(1, 1, 2, 15), ep(1, 1, 1, 25)])
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['mediatype'], 'season')
        self.assertEqual(items[0]['episode_count'], 2)
        self.assertEqual(items[1]['mediatype'], 'episode')
        self.assertEqual(items[1]['episode'], 1)

    def test_exactly_20_hours_is_still_grouped(self):
        items = self.group([ep(1, 1, 2, 0), ep(1, 1, 1, 20)])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['mediatype'], 'season')

    def test_several_seasons_become_show_group(self):
        items = self.group([ep(1, 2, 1, 1), ep(1, 1, 2, 2), ep(1, 1, 1, 3)])
        self.assertEqual(len(items), 1)
        group = items[0]
        self.assertEqual(group['mediatype'], 'tvshow')
        self.assertEqual(group['group_type'], 'show')
        self.assertEqual(group['season_count'], 2)
        self.assertEqual(group['episode_count'], 3)
        self.assertEqual(group['first_episode_file'], '/tv/1/s1e1.mkv')
        self.assertEqual(group['file'], 'videodb://tvshows/titles/1/')
        self.assertEqual(group['art']['poster'], 'poster1')

    def test_shows_in_one_cluster_are_kept_apart(self):
        items = self.group([ep(1, 1, 1, 1), ep(2, 1, 1, 2), ep(2, 1, 2, 3)])
        self.assertEqual(len(items), 2)
        by_show = {i['tvshowid']: i for i in items}
        self.assertEqual(by_show[1]['mediatype'], 'episode')
        self.assertEqual(by_show[2]['mediatype'], 'season')

    def test_first_episode_navigation_plays_first_file(self):
        items = self.group([ep(1, 1, 2, 1), ep(1, 1, 1, 2)], navigate_to='first')
        self.assertTrue(items[0]['is_playable'])
        self.assertEqual(items[0]['file'], '/tv/1/s1e1.mkv')

    def test_invalid_dateadded_is_skipped(self):
        items = self.group([ep(1, 1, 1, 1), ep(2, 1, 1, 2, dateadded=''),
                            ep(3, 1, 1, 3, dateadded='garbage')])
        self.assertEqual([i['tvshowid'] for i in items], [1])

    def test_limit(self):
        episodes = [ep(show, 1, 1, show) for show in range(1, 6)]
        self.assertEqual(len(self.group(episodes, limit=3)), 3)

    def test_navigation_setting(self):
        kodistub.SETTINGS['recentlyadded.navigation'] = 'First Episode'
        try:
            with mock.patch('resources.lib.widgets.tvshows.json_rpc_call',
                            return_value={'result': {'episodes': [ep(1, 1, 2, 1), ep(1, 1, 1, 2)]}}), \
                    mock.patch.object(TVShowWidgets, '_get_season_details',
                                      return_value={'title': 'Season 1', 'showtitle': 'Show 1'}):
                items = TVShowWidgets().get_recently_added_grouped()
        finally:
            kodistub.SETTINGS.clear()
        self.assertTrue(items[0]['is_playable'])


def nep(season, episode, playcount=0, firstaired='', episodeid=None):
    """An episode as Next Up lists them."""
    return {'episodeid': episodeid or season * 100 + episode, 'season': season,
            'episode': episode, 'playcount': playcount, 'firstaired': firstaired}


def order_keys(episodes):
    return [(e['season'], e['episode']) for e in TVShowWidgets._order_for_watching(episodes)]


class WatchOrderTest(unittest.TestCase):

    def test_regular_episodes_by_season_and_episode(self):
        episodes = [nep(2, 1), nep(1, 2), nep(1, 1), nep(2, 2)]
        self.assertEqual(order_keys(episodes), [(1, 1), (1, 2), (2, 1), (2, 2)])

    def test_dated_special_goes_before_first_episode_aired_on_or_after_it(self):
        episodes = [
            nep(1, 1, firstaired='2020-01-01'),
            nep(1, 2, firstaired='2020-01-08'),
            nep(2, 1, firstaired='2021-01-01'),
            nep(0, 1, firstaired='2020-06-01'),
            nep(0, 2, firstaired='2020-01-08'),  # same day as 1x2: comes first
        ]
        self.assertEqual(order_keys(episodes), [(1, 1), (0, 2), (1, 2), (0, 1), (2, 1)])

    def test_specials_after_the_last_episode_and_undated_go_last(self):
        episodes = [
            nep(1, 1, firstaired='2020-01-01'),
            nep(0, 3),
            nep(0, 1, firstaired='2022-01-01'),
            nep(0, 2),
        ]
        self.assertEqual(order_keys(episodes), [(1, 1), (0, 1), (0, 2), (0, 3)])

    def test_regular_episode_without_air_date_does_not_pull_specials_forward(self):
        episodes = [nep(1, 1), nep(1, 2, firstaired='2020-02-01'), nep(0, 1, firstaired='2020-01-01')]
        self.assertEqual(order_keys(episodes), [(1, 1), (0, 1), (1, 2)])


class PickNextUpTest(unittest.TestCase):

    def pick(self, episodes):
        chosen = TVShowWidgets._pick_next_up(episodes)
        return (chosen['season'], chosen['episode']) if chosen else None

    def test_nothing_watched_gives_first_episode(self):
        self.assertEqual(self.pick([nep(1, 2), nep(1, 1)]), (1, 1))

    def test_next_after_furthest_watched(self):
        self.assertEqual(self.pick([nep(1, 1, 1), nep(1, 2, 1), nep(1, 3)]), (1, 3))

    def test_skipped_episodes_do_not_come_back(self):
        episodes = [nep(1, 1), nep(1, 2), nep(1, 3, 1), nep(1, 4)]
        self.assertEqual(self.pick(episodes), (1, 4))

    def test_watched_episodes_after_the_marker_are_skipped(self):
        episodes = [nep(1, 1, 1), nep(1, 2), nep(1, 3, 1), nep(1, 4, 1), nep(1, 5)]
        self.assertEqual(self.pick(episodes), (1, 5))

    def test_finished_show_has_no_next_up(self):
        self.assertIsNone(self.pick([nep(1, 1, 1), nep(1, 2, 1)]))
        self.assertIsNone(self.pick([]))

    def test_special_slotted_in_is_next(self):
        episodes = [
            nep(1, 1, 1, '2020-01-01'),
            nep(0, 1, 0, '2020-01-05'),
            nep(1, 2, 0, '2020-01-08'),
        ]
        self.assertEqual(self.pick(episodes), (0, 1))

    def test_watched_undated_special_does_not_hide_the_show(self):
        episodes = [nep(1, 1, 1), nep(1, 2), nep(0, 1, 1)]
        self.assertEqual(self.pick(episodes), (1, 2))

    def test_unwatched_special_before_marker_is_ignored(self):
        episodes = [
            nep(0, 1, 0, '2019-12-01'),
            nep(1, 1, 1, '2020-01-01'),
            nep(1, 2, 0, '2020-01-08'),
        ]
        self.assertEqual(self.pick(episodes), (1, 2))


class NextUpCacheTest(unittest.TestCase):

    SHOW = {'tvshowid': 7, 'episode': 3, 'watchedepisodes': 1, 'lastplayed': '2026-11-15 21:00:00'}
    EPISODES = {'result': {'episodes': [nep(1, 1, 1, episodeid=71), nep(1, 2, episodeid=72),
                                        nep(1, 3, episodeid=73)]}}

    def test_choice_is_cached_until_watched_state_changes(self):
        widget = TVShowWidgets()
        choices = {}
        with mock.patch('resources.lib.widgets.tvshows.json_rpc_call',
                        return_value=self.EPISODES) as rpc:
            self.assertEqual(widget._next_up_episode_id(dict(self.SHOW), choices), 72)
            self.assertEqual(widget._next_up_episode_id(dict(self.SHOW), choices), 72)
            self.assertEqual(rpc.call_count, 1)

            changed = dict(self.SHOW, watchedepisodes=2, lastplayed='2026-11-16 21:00:00')
            widget._next_up_episode_id(changed, choices)
            self.assertEqual(rpc.call_count, 2)

        self.assertEqual(choices['7']['episodeid'], 72)

    def test_expired_choice_is_recomputed(self):
        widget = TVShowWidgets()
        sig = [3, 1, '2026-11-15 21:00:00']
        choices = {'7': {'sig': sig, 'episodeid': 99, 'ts': time.time() - 2 * widget.NEXTUP_CACHE_TTL}}
        with mock.patch('resources.lib.widgets.tvshows.json_rpc_call',
                        return_value=self.EPISODES) as rpc:
            self.assertEqual(widget._next_up_episode_id(dict(self.SHOW), choices), 72)
        rpc.assert_called_once()


class SonarrUpcomingTest(unittest.TestCase):

    URL = 'http://sonarr:8989'

    def setUp(self):
        kodistub.SETTINGS.update({'sonarr.enabled': 'true', 'sonarr.url': self.URL, 'sonarr.days': '7'})
        today = datetime.now()
        self.items = [
            {'title': f'In {d} days', 'firstaired': (today + timedelta(days=d)).strftime('%Y-%m-%d'),
             'sonarr_tvdbid': 100 + d, 'mediatype': 'episode'}
            for d in (0, 3, 10)
        ]

    def tearDown(self):
        kodistub.SETTINGS.clear()
        try:
            os.remove(cache._path(TVShowWidgets.SONARR_CACHE_NAME))
        except OSError:
            pass

    def test_served_from_cache_and_filtered_by_days(self):
        cache.write(TVShowWidgets.SONARR_CACHE_NAME, {'url': self.URL, 'items': self.items})
        with mock.patch.object(TVShowWidgets, '_fetch_sonarr_calendar') as fetch:
            items = TVShowWidgets().get_sonarr_upcoming()
        fetch.assert_not_called()
        self.assertEqual([i['title'] for i in items], ['In 0 days', 'In 3 days'])
        self.assertEqual(len(TVShowWidgets().get_sonarr_upcoming(days=14)), 3)

    def test_cache_for_another_url_is_refetched(self):
        cache.write(TVShowWidgets.SONARR_CACHE_NAME, {'url': 'http://old', 'items': self.items})
        with mock.patch.object(TVShowWidgets, '_fetch_sonarr_calendar', return_value=self.items[:1]) as fetch:
            items = TVShowWidgets().get_sonarr_upcoming()
        fetch.assert_called_once_with(TVShowWidgets.SONARR_CACHE_DAYS)
        self.assertEqual([i['title'] for i in items], ['In 0 days'])

    def test_stale_cache_is_used_when_sonarr_is_down(self):
        cache.write(TVShowWidgets.SONARR_CACHE_NAME, {'url': self.URL, 'items': self.items})
        old = time.time() - 2 * TVShowWidgets.SONARR_CACHE_MAX_AGE
        os.utime(cache._path(TVShowWidgets.SONARR_CACHE_NAME), (old, old))
        with mock.patch.object(TVShowWidgets, '_fetch_sonarr_calendar', return_value=None):
            items = TVShowWidgets().get_sonarr_upcoming()
        self.assertEqual(len(items), 2)

    def test_disabled(self):
        kodistub.SETTINGS['sonarr.enabled'] = 'false'
        self.assertEqual(TVShowWidgets().get_sonarr_upcoming(), [])


if __name__ == '__main__':
    unittest.main()
