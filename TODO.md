# TODO

Ordered by usefulness. Tick items off (or delete them) as they are done.

- [ ] **Fix the `seasons` widget labels.** The list shows blank labels (` - `). `get_seasons` returns `title` / `showtitle`, but the `season` branch of `create_listitem` in [plugin.py](plugin.py) reads `tvshowtitle` / `season_title`. It also sets `label2` to "N new episodes", which is wrong for a plain season list (use "N episodes").
- [ ] **Housekeeping (one commit):**
  - [ ] Make the Deploy task in [.vscode/tasks.json](.vscode/tasks.json) use `${env:APPDATA}` instead of the hardcoded `C:\Users\edjackson\...` path.
  - [ ] Fix the inline comment on the `.vscode/settings.json` line in [.gitignore](.gitignore); git only treats `#` as a comment at the start of a line.
  - [ ] Update the stale version and news entry in [addon.xml](addon.xml) (still `v1.0.0 (2024-08-07)`).
  - [ ] Add a `.gitattributes` so line endings stay consistent (the working copy is CRLF, the deployed copy in Kodi is LF).
- [ ] **Rename the Sonarr `tvshowid`.** `_fetch_sonarr_calendar` in [tvshows.py](resources/lib/widgets/tvshows.py) stores Sonarr's `tvdbId` under `tvshowid`, which a skin could mistake for a Kodi DBID (for example when passing `ListItem.DBID` to `seasons`). Use a distinct key such as `sonarr_tvdbid`. Low urgency: those items are not playable.
- [ ] **Add a small test suite.** Stub `xbmc*` and cover: the 20 hour clustering in `get_recently_added_grouped`, the route registry, `PathStats._calculate_stats`, `BaseWidget.episode_art` / `get_recently_added`, and `cache.py`. Needed to catch performance or behaviour regressions without launching Kodi.
- [ ] **Investigate the `SystemExit` traceback in `kodi.log` when the service stops** (from `threading._shutdown`). Harmless, and it also appeared with the old code; find which thread is still alive if the log noise matters.
