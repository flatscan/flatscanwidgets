#!/usr/bin/python
# coding: utf-8

"""Tests for the on-disk JSON cache (resources/lib/cache.py)."""

import os
import time
import unittest

from resources.lib import cache


class CacheTest(unittest.TestCase):

    def setUp(self):
        self.name = f'test_{self.id().rsplit(".", 1)[-1]}'

    def tearDown(self):
        try:
            os.remove(cache._path(self.name))
        except OSError:
            pass

    def test_round_trip(self):
        data = {'items': [{'title': 'Pilot', 'season': 1}], 'url': 'http://sonarr'}
        cache.write(self.name, data)
        self.assertEqual(cache.read(self.name), data)

    def test_missing_entry_is_none(self):
        self.assertIsNone(cache.read('does_not_exist'))

    def test_older_than_max_age_is_none(self):
        cache.write(self.name, [1, 2, 3])
        old = time.time() - 3600
        os.utime(cache._path(self.name), (old, old))
        self.assertIsNone(cache.read(self.name, max_age=60))
        # Without a max age, any age is accepted
        self.assertEqual(cache.read(self.name), [1, 2, 3])

    def test_fresh_entry_within_max_age(self):
        cache.write(self.name, 'value')
        self.assertEqual(cache.read(self.name, max_age=60), 'value')

    def test_corrupt_file_is_none(self):
        os.makedirs(cache.CACHE_DIR, exist_ok=True)
        with open(cache._path(self.name), 'w', encoding='utf-8') as f:
            f.write('{not json')
        self.assertIsNone(cache.read(self.name))

    def test_write_leaves_no_temp_file(self):
        cache.write(self.name, {'a': 1})
        self.assertFalse(os.path.exists(cache._path(self.name) + '.tmp'))

    def test_unserialisable_data_does_not_raise(self):
        cache.write(self.name, {'a': object()})
        self.assertIsNone(cache.read(self.name))


if __name__ == '__main__':
    unittest.main()
