#!/usr/bin/python
# coding: utf-8

"""
Small JSON file cache in the add-on profile folder.

Plugin and script calls each run in a fresh Python process, so in-memory
caches never survive between widget loads. Anything worth keeping (for example
slow network lookups the service refreshes in the background) goes here.
"""

import json
import os
import time

from resources.lib.addon import ADDON_DATA_PATH
from resources.lib.logger import log

CACHE_DIR = os.path.join(ADDON_DATA_PATH, 'cache')


def _path(name):
    return os.path.join(CACHE_DIR, f'{name}.json')


def read(name, max_age=None):
    """
    Read a cached value.

    Args:
        name: Cache entry name
        max_age: Maximum age in seconds, or None to accept any age

    Returns:
        The stored data, or None when missing, unreadable or too old
    """
    try:
        path = _path(name)
        age = time.time() - os.path.getmtime(path)
        if max_age is not None and age > max_age:
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write(name, data):
    """Store a JSON-serialisable value. The write is atomic so readers never see a partial file."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        path = _path(name)
        tmp = f'{path}.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except (OSError, TypeError, ValueError) as e:
        log(f'Cache write failed for {name}: {e}', 'WARNING')
