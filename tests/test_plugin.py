#!/usr/bin/python
# coding: utf-8

"""Tests for plugin.py: the route registry, README coverage, and ListItem URLs."""

import inspect
import os
import re
import sys
import unittest
from unittest import mock

from tests import kodistub

plugin = kodistub.import_plugin()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def readme_table_names(first_header):
    """First-column names of every README table whose header starts with first_header."""
    with open(os.path.join(ROOT, 'README.md'), encoding='utf-8') as f:
        lines = f.read().splitlines()
    names, in_table = set(), False
    for line in lines:
        if line.startswith(f'| {first_header} |'):
            in_table = True
        elif in_table and line.startswith('|'):
            names.update(re.findall(r'`([^`]+)`', line.split('|')[1]))
        else:
            in_table = False
    return names


class RouteRegistryTest(unittest.TestCase):

    def test_every_route_is_documented_in_readme(self):
        documented = readme_table_names('`info`')
        self.assertEqual(set(plugin.ROUTES) - documented, set(),
                         'routes missing from the README widget tables')
        self.assertEqual(documented - set(plugin.ROUTES), set(),
                         'README lists widgets that have no route')

    def test_handlers_take_widgets_params_limit(self):
        for info, entry in plugin.ROUTES.items():
            params = list(inspect.signature(entry['handler']).parameters)
            self.assertEqual(len(params), 3, info)

    def test_menu_entries_have_a_known_category_and_label(self):
        categories = {cat for cat, _, _ in plugin.CATEGORIES}
        for info, entry in plugin.ROUTES.items():
            if entry['category'] is None:
                self.assertIsNone(entry['label'], info)
            else:
                self.assertIn(entry['category'], categories, info)
                self.assertTrue(entry['label'], info)

    def test_required_params_fail_the_directory(self):
        w = plugin.Widgets()
        self.assertIsNone(plugin.ROUTES['seasons']['handler'](w, {}, 100))
        self.assertIsNone(plugin.ROUTES['episodes']['handler'](w, {'dbid': '1'}, 100))
        self.assertIsNone(plugin.ROUTES['seasonshowdetails']['handler'](w, {}, 100))
        self.assertIsNone(plugin.ROUTES['pathstatswidget']['handler'](w, {}, 100))

    def test_upcoming_episodes_needs_sonarr_enabled(self):
        self.assertIsNone(plugin.ROUTES['upcomingepisodes']['handler'](plugin.Widgets(), {}, 100))


class ScriptActionsTest(unittest.TestCase):

    def test_every_action_is_documented_in_readme(self):
        with open(os.path.join(ROOT, 'default.py'), encoding='utf-8') as f:
            source = f.read()
        actions = set(re.findall(r"action == '([a-z]+)'", source))
        for group in re.findall(r'action in \[([^\]]+)\]', source):
            actions.update(re.findall(r"'([a-z]+)'", group))
        self.assertTrue(actions)
        documented = readme_table_names('Action')
        self.assertEqual(actions - documented, set(), 'actions missing from the README')


class DirectoryTest(unittest.TestCase):
    """add_items_to_directory: URLs, folders and properties per media type."""

    def add(self, items, content_type):
        kodistub.DIRECTORY.clear()
        with mock.patch.object(plugin, 'HANDLE', 1):
            plugin.add_items_to_directory(items, content_type)
        return list(kodistub.DIRECTORY)

    def test_library_episode_plays_its_file(self):
        [(url, li, is_folder)] = self.add([{'episodeid': 5, 'tvshowid': 2, 'file': '/tv/a.mkv',
                                            'title': 'Pilot', 'showtitle': 'Show'}], 'episode')
        self.assertEqual(url, '/tv/a.mkv')
        self.assertFalse(is_folder)
        self.assertEqual(li.getProperty('IsPlayable'), 'true')
        self.assertEqual(li.label, 'Show - Pilot')

    def test_sonarr_episode_is_not_playable_and_has_no_dbid(self):
        [(url, li, is_folder)] = self.add([{'title': 'Next', 'showtitle': 'Show', 'season': 1,
                                            'episode': 2, 'sonarr_tvdbid': 12345}], 'episode')
        self.assertEqual(url, '')
        self.assertFalse(is_folder)
        self.assertEqual(li.getProperty('IsPlayable'), 'false')
        self.assertEqual(li.getProperty('dbid'), '')
        self.assertEqual(li.getProperty('TvdbId'), '12345')

    def test_movie_without_file_uses_videodb(self):
        [(url, _, is_folder)] = self.add([{'movieid': 9, 'title': 'Film'}], 'movie')
        self.assertEqual(url, 'videodb://movies/titles/9')
        self.assertFalse(is_folder)

    def test_season_and_show_browse_into_library(self):
        entries = self.add([
            {'tvshowid': 3, 'season': 2, 'mediatype': 'season'},
            {'tvshowid': 3, 'mediatype': 'tvshow', 'title': 'Show'},
        ], 'video')
        self.assertEqual(entries[0][0], 'videodb://tvshows/titles/3/2/')
        self.assertEqual(entries[1][0], 'videodb://tvshows/titles/3/')
        self.assertTrue(entries[0][2] and entries[1][2])
        self.assertEqual(entries[1][1].getProperty('dbid'), '3')

    def test_playable_group_plays_first_episode(self):
        [(url, _, is_folder)] = self.add([{'tvshowid': 3, 'season': 1, 'mediatype': 'season',
                                           'is_playable': True, 'file': '/tv/s1e1.mkv'}], 'season')
        self.assertEqual(url, '/tv/s1e1.mkv')
        self.assertFalse(is_folder)

    def test_set_and_genre_folders(self):
        entries = self.add([
            {'setid': 4, 'mediatype': 'set', 'title': 'Saga', 'watched': 1, 'total': 3},
            {'genreid': 6, 'mediatype': 'genre', 'title': 'Drama'},
        ], 'video')
        self.assertEqual(entries[0][0], 'videodb://movies/sets/4/')
        self.assertEqual(entries[0][1].getProperty('UnwatchedCount'), '2')
        self.assertEqual(entries[1][0], 'videodb://tvshows/genres/6/')
        self.assertTrue(entries[0][2] and entries[1][2])

    def test_resume_point(self):
        [(_, li, _)] = self.add([{'movieid': 1, 'file': '/m.mkv',
                                  'resume': {'position': 60, 'total': 600}}], 'movie')
        self.assertEqual(li.getProperty('ResumeTime'), '60')
        self.assertEqual(li.getProperty('TotalTime'), '600')

    def test_every_item_gets_a_video_info_tag(self):
        # Kodi only reloads widgets on library changes if items have one
        for item, content_type in [
            ({'movieid': 1, 'file': '/m.mkv'}, 'movie'),
            ({'title': 'Drama', 'genreid': 1, 'mediatype': 'genre'}, 'video'),
            ({'title': 'Stats'}, 'video'),
        ]:
            [(_, li, _)] = self.add([item], content_type)
            self.assertIn('setTitle', li.infotag.calls, item)


class RouterTest(unittest.TestCase):

    def run_router(self, query):
        saved = sys.argv
        sys.argv = ['plugin.py', '1', query]
        try:
            with mock.patch.object(plugin, 'add_items_to_directory') as add, \
                    mock.patch.object(plugin.xbmcplugin, 'endOfDirectory') as end:
                plugin.router()
        finally:
            sys.argv = saved
        return add, end

    def test_routes_to_handler_with_params_and_limit(self):
        handler = mock.Mock(return_value=([{'title': 'x'}], 'movie', 'Label'))
        with mock.patch.dict(plugin.ROUTES, {'fake': {'handler': handler, 'category': None, 'label': None}}):
            add, _ = self.run_router('?info=fake&limit=5&path=a%20b')
        _, params, limit = handler.call_args[0]
        self.assertEqual(params['path'], 'a b')
        self.assertEqual(limit, 5)
        add.assert_called_once_with([{'title': 'x'}], 'movie', 'Label')

    def test_default_limit_is_100(self):
        handler = mock.Mock(return_value=([], 'movie', 'Label'))
        with mock.patch.dict(plugin.ROUTES, {'fake': {'handler': handler, 'category': None, 'label': None}}):
            self.run_router('?info=fake')
        self.assertEqual(handler.call_args[0][2], 100)

    def test_handler_errors_fail_the_directory(self):
        handler = mock.Mock(side_effect=RuntimeError('boom'))
        with mock.patch.dict(plugin.ROUTES, {'fake': {'handler': handler, 'category': None, 'label': None}}):
            add, end = self.run_router('?info=fake')
        add.assert_not_called()
        self.assertEqual(end.call_args.kwargs.get('succeeded'), False)

    def test_unknown_info_fails_the_directory(self):
        add, end = self.run_router('?info=nosuchwidget')
        add.assert_not_called()
        self.assertEqual(end.call_args.kwargs.get('succeeded'), False)


if __name__ == '__main__':
    unittest.main()
