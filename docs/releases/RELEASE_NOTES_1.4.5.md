# Video Downloader Pro 1.4.5 (unpublished)

- Includes the native destination-folder picker fix and localized error handling.
- Opens the correct folder for literal percent-containing paths and directory
  selections; missing targets and OS errors no longer report success.
- Prevents malformed optional history metadata from breaking the whole history page.
- Updates Soup Sieve to 4.0 to address three known parsing/matching vulnerabilities.
- Adds hostile nested-HTML and desktop edge-case regression tests.

The earlier 1.4.4 installer was a local candidate. This candidate uses 1.4.5 so
users who installed it can upgrade normally. Publication has not been authorized
for this new candidate. See `docs/testing/DESKTOP_AUDIT_2026-11-15.md` for evidence
and testing limits.
