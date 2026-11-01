# Recovery, restart durability and desktop lifecycle — 2026-11-01

Implemented in working source and an isolated unpacked test build. No installer,
production upgrade, GitHub publication or native-host registration was performed.
Application version remains 1.3.0; this is not a replacement published release.

## User-visible behavior

- A session-local Windows named mutex is acquired before importing the Flask app
  or creating its queue/bridge. Another launch shows an already-running notice
  and exits without starting a second application. Windows releases the handle
  after a crash; no stale lock file needs removal.
- Closing with active/queued/retrying work asks for confirmation. Cancel leaves
  the window and jobs usable. Confirm keeps the GUI alive with a saving screen
  while downloads stop and queue state is written.
- Files already in the conversion stage finish safely before graceful exit.
  Transfer cancellation preserves partial files; it does not delete or silently
  mark them completed.
- Failed queue persistence vetoes closure and shows a safe disk/permission notice.
  An initial failed write leaves the scheduler operational. If a final save fails
  after shutdown has started, jobs stay stopped and closing can be retried after
  the storage problem is resolved.
- The reopened app restores interrupted work paused and opens its queue. The
  Recovery center displays the last saved progress, interruption reason and
  explicit Resume / Refresh source and retry actions. Resume is user-controlled;
  reopening does not silently start network transfers.
- Refresh discards stale discovery caches for the original page and requeues the
  same job. It preserves the reserved filename, source identity and prior partial
  files; normal source/format/strong-validator checks still decide safe resume.
- Live jobs explain that a new capture starts at the current live window. They
  are not implicitly restarted by the old resume-all action.
- Native notices and recovery UI have all ten supported application locales.

## Durability changes

The reserved output template and media source checkpoint are persisted before
media transfer begins, rather than waiting for the next two-second scheduler
checkpoint. Existing periodic queue persistence, SQLite transactions, bounded
retry policies, missing-fragment rejection and source identity checks remain.

Resume state changes roll back if the required queue write fails. Resolver locks
are acquired without holding the manager lock to avoid progress-callback lock
inversion. Window closure waits for worker completion off the native UI thread,
because retained browser cleanup can itself need the UI thread.

## Verification

- Full isolated Python gate: **470 tests, zero failures/errors/skips**.
- All **25 JavaScript UI suites passed**.
- Seven desktop lifecycle tests include real Windows mutex contention across
  processes, release after abrupt termination, cancelled closure, delayed save,
  disk failure and retry, and locale assets.
- Nine recovery tests cover shutdown/restore identity and options, conversion
  completion, failed persistence, pre-transfer checkpointing, refreshed-source
  identity preservation, live exclusions, safe summaries and API origin checks.
- Two real local-media tests ran the actual scheduler/downloader in subprocesses.
  One closed gracefully mid-transfer; the other killed the process. Each new
  process restored the original job ID, resumed with a nonzero HTTP Range and
  produced one complete 1,979,928-byte file with a byte-identical SHA-256 match.
  FFprobe verified both audio and video and the generated 12-second duration.
- Actual WebView2 events passed: Cancel vetoed closure, the window remained
  usable, accepted closure saved asynchronously, and save finished before closed.
  Dialog answers were controlled by the fixture, without asking the user.
- Rendered Chromium acceptance passed ten languages, safe title rendering,
  source-refresh payload, automatic queue navigation, pending/live states,
  small-window button access, saving and save-failure notices. No script errors.
- PyInstaller unpacked test build passed isolated startup/API/assets checks. Its
  live mutex blocked a second source launch before app import. Recovery assets,
  safe APIs and compiled native-host stdio exchange passed; no setup consent was
  bypassed. All changed packaged source/static files match working source.

## Evidence and commands

- `build/recovery-regression/result.json` and `unit.log`.
- `build/recovery-ui/result.json`, `recovery-tr.png`, `recovery-small.png`.
- `build/lifecycle-native/result.json`.
- `build/recovery-package-runtime/result.json`.
- Test app: `build/recovery-package/YoutubePro/YoutubePro.exe` (keep `_internal`
  beside it; this folder is not an installer or a published release).

Targeted checks:

```powershell
python -m unittest discover -s tests -p test_app_lifecycle.py
python -m unittest discover -s tests -p test_recovery.py
python -m unittest discover -s tests -p test_recovery_transfer_local.py
python tests/verify_lifecycle_native.py
python tests/verify_recovery_ui.py
```

The transfer/native/browser checks require local socket/process access; the first
sandboxed transfer attempt was blocked by Windows with WinError 10013. The same
fixture passed outside that restriction. Test profiles and media were isolated
from personal data; the temporary transfer fixtures clean themselves up.

## Limits

Resume depends on the server/protocol and on the original representation still
being available. Changed or unverified sources are not blindly appended. Live
capture cannot recover an unavailable past window. Power loss can lose the latest
progress display checkpoint, while actual partial file bytes remain the basis for
resume. A 12-second synthetic test exercises restart/Range integrity, not hours of
real CDN availability. No new clean Windows VM or installer-upgrade acceptance
was performed here.
