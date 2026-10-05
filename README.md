# Flatscan Widgets

A widget and helper add-on for Kodi 21 (Omega) skins. It provides library-backed widget paths, window-property helpers for skins, and a background service for fanart rotation.

- **Add-on ID:** `script.flatscan.widgets`
- **Requires:** Kodi 21 (Python 3)
- **License:** GPL-2.0-or-later

## Installation

1. Zip the repository contents so that `addon.xml` is inside a folder named `script.flatscan.widgets`.
2. In Kodi: **Settings → Add-ons → Install from zip file**.

## Using the widgets

Browse **Add-ons → Video add-ons → Flatscan Widgets** to pick a widget in your skin's widget editor, or use a path directly:

```
plugin://script.flatscan.widgets/?info=<widget>&limit=<n>
```

`limit` is optional and defaults to **100**. Some widgets take extra parameters, listed below. Parameters marked *(required)* make the widget fail (empty directory) when missing.

### TV Shows

| `info` | Description | Extra params |
|---|---|---|
| `inprogressepisodes` | Partially watched episodes | |
| `nextup` | Next unwatched episode of shows you are watching | |
| `recentepisodes` | Recently added episodes | |
| `recentlyaired` | Episodes that aired in the last N days, newest first. Episodes not yet aired are excluded | `days` (default 90) |
| `recenttvshows` | Recently updated shows | |
| `recentlyaddedgrouped` | Recently added episodes, grouped into season/show items (episodes added within 20 hours of each other are grouped) | `days` (default 30) |
| `upcomingepisodes` | Upcoming episodes from Sonarr (needs [Sonarr](#sonarr-integration) enabled). Items are informational and not playable | `days` (default: the *Days Ahead* setting) |
| `tvshowgenres` | TV show genres | |
| `tvshowsbyrandomgenre` | Shows from a random genre | |
| `tvsuggestions` | Suggested shows | |
| `tvsimilar` | Shows similar to a given show | `dbid` *(required)* |
| `seasons` | Seasons of a show | `dbid` *(required)* |
| `episodes` | Episodes of a season | `dbid`, `season` *(required)* |

### Movies

| `info` | Description | Extra params |
|---|---|---|
| `inprogressmovies` | Partially watched movies | |
| `recentmovies` | Recently added movies | `unwatched=true` |
| `randommovies` | Random movies | |

### Mixed (movies and shows)

| `info` | Description | Extra params |
|---|---|---|
| `inprogressmedia` | Continue watching | |
| `suggestions` | Suggestions based on watch history | |
| `byrandomgenre` | Movies and shows from a random genre | |
| `similarmovies` | Movies similar to a given movie | `dbid` *(required)* |
| `similartvshows` | Shows similar to a given show | `dbid` *(required)* |
| `morebyactor` | Movies featuring an actor | `actor` *(required)* |

### Info widgets

| `info` | Description | Extra params |
|---|---|---|
| `seasonshowdetails` | Single item with show episode/watched counts | `dbid` *(required)* |
| `pathstatswidget` | Single item with total/watched/unwatched counts for a path | `path` *(required)* |

Examples:

```
plugin://script.flatscan.widgets/?info=recentlyaired&days=30&limit=20
plugin://script.flatscan.widgets/?info=recentmovies&unwatched=true
plugin://script.flatscan.widgets/?info=seasons&dbid=$INFO[ListItem.DBID]
```

## Script actions (for skins)

Call with `RunScript(script.flatscan.widgets,action=<action>,...)`.

| Action | Arguments | Result |
|---|---|---|
| `tvshowdetails` / `seasondetails` / `showdetails` | `dbid` *(required)*, `idtype` (default `season`), `window` (default 10000) | Sets TV show detail window properties |
| `pathstats` / `stats` | `path` *(required)*, `prop` (default `PathStats`), `window` (default 10000) | Sets `<prop>.Count`, `.Watched`, `.Unwatched`, `.InProgress` (plus `.Episodes`, `.WatchedEpisodes`, `.UnwatchedEpisodes` for TV paths) |
| `refreshwidgets` | | Pulses the `FlatscanWidgetUpdate` home window property (same signal the service sends on library updates) |
| `restartservice` | | Asks the background service to restart and re-read its settings |

Example:

```
RunScript(script.flatscan.widgets,action=pathstats,path=videodb://tvshows/titles/,prop=MyStats)
```

## Background service

When enabled, the service:

- Rotates random fanart from movies, TV shows and music artists, exposed through the `FlatscanBackground`, `FlatscanBackgroundTitle` and `FlatscanBackgroundType` home window properties.
- Pre-caches widget artwork.
- Sets the `FlatscanWidgetUpdate` home window property briefly (about 100 ms) whenever the video library updates, so skins can refresh widgets.
- Pauses during the screensaver and restarts when settings change.

To refresh a skin container when the library changes, key it off the property, for example with a visibility or reload condition on `Window(Home).Property(FlatscanWidgetUpdate)`.

## Settings

| Category | Options |
|---|---|
| General | Enable background service, debug logging |
| Background Fanart | Enable, rotation interval (seconds), include movies / TV shows / music |
| Widget Behavior | Recently Added navigation: `Browse` or `First Episode` |
| Sonarr Integration | Enable, URL, API key, days ahead (1-30) |

### Sonarr integration

The `upcomingepisodes` widget reads your Sonarr calendar (`/api/v3/calendar`) and lists episodes that do not have a file yet, with poster and fanart from the series images.

1. In the add-on settings, open **Sonarr Integration** and enable it.
2. Set the Sonarr **URL** (for example `http://localhost:8989`) and the **API key** (Sonarr → Settings → General).
3. Choose how many days ahead to show (1-30). The `days` URL parameter overrides this per widget.

The request has a 10 second timeout, so a slow or unreachable Sonarr server makes the widget load slowly or show nothing.

## Troubleshooting

- **Enable debug logging** in the General settings. Without it, the add-on's debug messages are hidden; with it, they appear at INFO level in `kodi.log`. Look for lines containing `script.flatscan.widgets`.
- **A widget is empty:** check that required parameters (`dbid`, `season`, `actor`, `path`) are present, and look for `Error in router` in the log.
- **Upcoming Episodes is empty:** confirm Sonarr is enabled, the URL is reachable from the Kodi device, and the API key is correct. Failures are logged as `Sonarr API error`.
- **Large `limit` values are slow** for widgets that look up season artwork per episode (such as `recentlyaired`). Use a modest `limit` for home-screen widgets.

## Development

Widget routes are defined in a registry in `plugin.py`. Each route is registered once with a decorator; the browsing menus (root and category folders) are generated from the same registry.

To add a widget:

1. Add a method to the matching widget class in `resources/lib/widgets/` (`tvshows.py`, `movies.py` or `mixed.py`). It returns a list of dicts with Kodi JSON-RPC fields and an `art` dict.
2. Register a handler in `plugin.py`:

   ```python
   @route('myinfo', 'tvshows', 'My Widget')   # info id, menu category, menu label
   def route_myinfo(w, params, limit):
       return w.shows.get_my_widget(limit=limit), 'episode', 'My Widget'
   ```

   A handler returns `(items, mediatype, label)`, or `None` to fail the directory (for example when a required parameter is missing). Omit the category and label to register a route that does not appear in the menus.
3. Add it to the tables in this README.

Tips:

- Prefer server-side filters and sorting in `VideoLibrary` JSON-RPC calls (for example `airdate` / `dateadded` with the `after` operator) over fetching large lists and filtering in Python.
- Kodi's embedded Python behaves differently from desktop Python in places. For example `datetime.strptime` can raise `TypeError`; use `datetime.fromisoformat` instead.
- You can exercise a widget without a skin by calling `Files.GetDirectory` over JSON-RPC with the `plugin://` path.

## Project layout

```
addon.xml            Add-on manifest
default.py           Script entry point (RunScript actions)
plugin.py            Plugin entry point (route registry, widget paths and browsing)
service.py           Service entry point
resources/
  settings.xml       Add-on settings
  lib/
    addon.py         Add-on handle and settings helper
    kodi_utils.py    JSON-RPC helper
    logger.py        Logging (honours the debug setting)
    widgets/         Widget data providers (tvshows, movies, mixed)
    info/            Window-property info providers
    service/         Fanart, artwork-cache services and monitor
```

## Links

- Source: <https://github.com/flatscan/flatscanwidgets>
- Discussions: <https://github.com/flatscan/flatscanwidgets/discussions>
