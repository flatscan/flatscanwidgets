#!/usr/bin/python
# coding: utf-8

"""Tests for PathStats (resources/lib/info/pathstats.py)."""

import unittest
from unittest import mock

from resources.lib.info.pathstats import PathStats


class CalculateStatsTest(unittest.TestCase):

    def test_movies(self):
        items = [
            {'type': 'movie', 'playcount': 1},
            {'type': 'movie', 'playcount': 0, 'resume': {'position': 120}},
            {'type': 'movie', 'playcount': 0},
        ]
        stats = PathStats()._calculate_stats(items)
        self.assertEqual(stats, {'count': 3, 'watched': 1, 'unwatched': 2,
                                 'type': 'movie', 'inprogress': 1})

    def test_shows_total_episodes_and_count_partly_watched(self):
        items = [
            {'type': 'tvshow', 'episode': 10, 'watchedepisodes': 10, 'playcount': 1},
            {'type': 'tvshow', 'episode': 8, 'watchedepisodes': 3, 'playcount': 0},
            {'type': 'tvshow', 'episode': 5, 'watchedepisodes': 0, 'playcount': 0},
        ]
        stats = PathStats()._calculate_stats(items)
        self.assertEqual(stats['type'], 'tvshow')
        self.assertEqual(stats['watched'], 1)
        self.assertEqual(stats['episodes'], 23)
        self.assertEqual(stats['watchedepisodes'], 13)
        self.assertEqual(stats['unwatchedepisodes'], 10)
        self.assertEqual(stats['inprogress'], 1)

    def test_mixed_and_untyped(self):
        stats = PathStats()._calculate_stats([{'type': 'movie'}, {'type': 'episode'}])
        self.assertEqual(stats['type'], 'mixed')
        self.assertNotIn('episodes', stats)
        self.assertEqual(PathStats()._calculate_stats([{'filetype': 'file'}])['type'], 'video')

    def test_empty(self):
        stats = PathStats()._calculate_stats([])
        self.assertEqual(stats, {'count': 0, 'watched': 0, 'unwatched': 0,
                                 'type': 'unknown', 'inprogress': 0})


class GetStatsTest(unittest.TestCase):

    def test_ignores_sub_folders(self):
        files = [
            {'type': 'movie', 'filetype': 'file', 'playcount': 1},
            {'type': 'movie', 'filetype': 'file', 'playcount': 0},
            {'filetype': 'directory', 'label': 'Genres'},
            {'type': 'unknown', 'filetype': 'directory', 'label': '2024'},
            {'filetype': 'file', 'playcount': 0},  # plain file from a source or playlist
        ]
        with mock.patch('resources.lib.info.pathstats.json_rpc_call',
                        return_value={'result': {'files': files}}) as rpc:
            stats = PathStats().get_stats('videodb://movies/genres/1/')
        rpc.assert_called_once()
        self.assertEqual(rpc.call_args[0][0], 'Files.GetDirectory')
        self.assertEqual(rpc.call_args[0][1]['directory'], 'videodb://movies/genres/1/')
        self.assertEqual(stats['count'], 3)
        self.assertEqual(stats['watched'], 1)
        self.assertEqual(stats['type'], 'mixed')

    def test_failed_rpc(self):
        with mock.patch('resources.lib.info.pathstats.json_rpc_call', return_value={}):
            self.assertEqual(PathStats().get_stats('x')['count'], 0)


if __name__ == '__main__':
    unittest.main()
