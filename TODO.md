# TODO

Ordered by usefulness. Tick items off (or delete them) as they are done.

- [ ] **Add a small test suite.** Stub `xbmc*` and cover: the 20 hour clustering in `get_recently_added_grouped`, the route registry, `PathStats._calculate_stats`, `BaseWidget.episode_art` / `get_recently_added`, and `cache.py`. Needed to catch performance or behaviour regressions without launching Kodi.
- [ ] **Investigate the `SystemExit` traceback in `kodi.log` when the service stops** (from `threading._shutdown`). Harmless, and it also appeared with the old code; find which thread is still alive if the log noise matters.
