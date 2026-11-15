# Video Downloader Pro 1.4.6 — unpublished candidate

- Includes the native folder picker, folder-opening, history metadata and Soup
  Sieve security fixes from the earlier local candidates.
- Preserves valid saved preferences when one setting is malformed, without
  modifying the settings file during recovery reads.
- Prevents simultaneous settings/language changes from overwriting the new language.
- Adds deterministic settings-race and malformed-request regression coverage.

See `docs/testing/FINAL_EDGE_AUDIT_2026-11-15.md` for final evidence and limits.
Earlier 1.4.4/1.4.5 builds were local candidates; the higher version permits
upgrading those installations. This candidate has not been published.
