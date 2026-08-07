#!/usr/bin/python
# coding: utf-8

"""
Widgets package - provides content widgets for Kodi skins.
"""

from .base import BaseWidget
from .movies import MovieWidgets
from .tvshows import TVShowWidgets
from .mixed import MixedWidgets

__all__ = ['BaseWidget', 'MovieWidgets', 'TVShowWidgets', 'MixedWidgets']