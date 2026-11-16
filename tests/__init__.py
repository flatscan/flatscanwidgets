#!/usr/bin/python
# coding: utf-8

"""
Unit tests for Flatscan Widgets, run with desktop Python:

    python -m unittest discover -s tests -t .

Importing this package installs stand-ins for Kodi's modules (see
kodistub.py) before any add-on code is imported.
"""

from tests import kodistub

kodistub.install()
