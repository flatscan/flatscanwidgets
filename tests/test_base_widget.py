#!/usr/bin/python
# coding: utf-8

"""Tests for BaseWidget (resources/lib/widgets/base.py)."""

import unittest
from unittest import mock

from resources.lib.widgets.base import BaseWidget


class EpisodeArtTest(unittest.TestCase):

    def test_season_art_wins_over_show_art(self):
        ep = {
            'thumbnail': 'thumb.jpg',
            'art': {
                'season.poster': 's-poster', 'tvshow.poster': 't-poster',
                'season.fanart': 's-fanart', 'tvshow.fanart': 't-fanart',
                'season.banner': 's-banner', 'tvshow.banner': 't-banner',
                'tvshow.clearlogo': 'logo', 'tvshow.landscape': 'land',
            },
        }
        art = BaseWidget().episode_art(ep)
        self.assertEqual(art['poster'], 's-poster')
        self.assertEqual(art['fanart'], 's-fanart')
        self.assertEqual(art['banner'], 's-banner')
        self.assertEqual(art['thumb'], 'thumb.jpg')
        self.assertEqual(art['tvshow.poster'], 't-poster')
        self.assertEqual(art['tvshow.fanart'], 't-fanart')
        self.assertEqual(art['clearlogo'], 'logo')
        self.assertEqual(art['landscape'], 'land')

    def test_falls_back_to_show_art(self):
        ep = {'art': {'tvshow.poster': 't-poster', 'tvshow.fanart': 't-fanart',
                      'tvshow.banner': 't-banner', 'thumb': 'art-thumb'}}
        art = BaseWidget().episode_art(ep)
        self.assertEqual(art['poster'], 't-poster')
        self.assertEqual(art['fanart'], 't-fanart')
        self.assertEqual(art['banner'], 't-banner')
        self.assertEqual(art['thumb'], 'art-thumb')
        self.assertEqual(art['season.poster'], '')

    def test_episode_fanart_is_last_resort(self):
        art = BaseWidget().episode_art({'art': {'fanart': 'ep-fanart'}})
        self.assertEqual(art['fanart'], 'ep-fanart')

    def test_no_art(self):
        art = BaseWidget().episode_art({})
        self.assertTrue(all(value == '' for value in art.values()))


def _rpc_result(key, count):
    return {'result': {key: [{'id': i} for i in range(count)]}}


class GetRecentlyAddedTest(unittest.TestCase):

    def _run(self, answers, method='VideoLibrary.GetEpisodes', limit=10):
        calls = []

        def fake_rpc(rpc_method, params):
            calls.append(dict(params, filter=params.get('filter')))
            return answers[len(calls) - 1]

        with mock.patch('resources.lib.widgets.base.json_rpc_call', side_effect=fake_rpc):
            items = BaseWidget().get_recently_added(method, ['title'], limit)
        return items, calls

    def test_stops_at_first_window_with_enough_items(self):
        items, calls = self._run([_rpc_result('episodes', 10)])
        self.assertEqual(len(items), 10)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['filter']['field'], 'dateadded')
        self.assertEqual(calls[0]['sort'], {'order': 'descending', 'method': 'dateadded'})
        self.assertEqual(calls[0]['limits'], {'start': 0, 'end': 10})

    def test_widens_window_then_drops_filter(self):
        items, calls = self._run([
            _rpc_result('episodes', 2),
            _rpc_result('episodes', 5),
            _rpc_result('episodes', 7),
        ])
        self.assertEqual(len(items), 7)
        self.assertEqual(len(calls), 3)
        self.assertIsNotNone(calls[0]['filter'])
        self.assertIsNotNone(calls[1]['filter'])
        # 30 day window is later (narrower) than the 180 day one
        self.assertGreater(calls[0]['filter']['value'], calls[1]['filter']['value'])
        self.assertIsNone(calls[2]['filter'])

    def test_result_key_follows_method(self):
        items, _ = self._run([_rpc_result('movies', 10)], method='VideoLibrary.GetMovies')
        self.assertEqual(len(items), 10)
        items, _ = self._run([_rpc_result('tvshows', 10)], method='VideoLibrary.GetTVShows')
        self.assertEqual(len(items), 10)

    def test_failed_rpc_gives_empty_list(self):
        items, calls = self._run([{}, {}, {}])
        self.assertEqual(items, [])
        self.assertEqual(len(calls), 3)


if __name__ == '__main__':
    unittest.main()
