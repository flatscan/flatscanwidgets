# TODO

Ordered by usefulness. Tick items off (or delete them) as they are done.

- [ ] **Investigate the `SystemExit` traceback in `kodi.log` when the service stops** (from `threading._shutdown`). Harmless, and it also appeared with the old code; find which thread is still alive if the log noise matters.
