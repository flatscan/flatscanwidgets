# TODO

Ordered by usefulness. Tick items off (or delete them) as they are done.

- [ ] **Add a `.gitattributes`** so line endings stay consistent (the working copy is CRLF, the deployed copy in Kodi is LF).
- [ ] **Rename the Sonarr `tvshowid`.** `_fetch_sonarr_calendar` in [tvshows.py](resources/lib/widgets/tvshows.py) stores Sonarr's `tvdbId` under `tvshowid`, which a skin could mistake for a Kodi DBID (for example when passing `ListItem.DBID` to `seasons`). Use a distinct key such as `sonarr_tvdbid`. Low urgency: those items are not playable.
- [ ] **Add a small test suite.** Stub `xbmc*` and cover: the 20 hour clustering in `get_recently_added_grouped`, the route registry, `PathStats._calculate_stats`, `BaseWidget.episode_art` / `get_recently_added`, and `cache.py`. Needed to catch performance or behaviour regressions without launching Kodi.
- [ ] **Investigate the `SystemExit` traceback in `kodi.log` when the service stops** (from `threading._shutdown`). Harmless, and it also appeared with the old code; find which thread is still alive if the log noise matters.
