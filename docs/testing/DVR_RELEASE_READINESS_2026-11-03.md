# DVR release-readiness validation — 1.4.3 candidate

Subsequent [startup polish](STARTUP_POLISH_2026-11-03.md) is tested in a separate
unpublished preview. The installer hash in this report identifies the earlier DVR
candidate; an installer rebuild is required to include the later startup changes.

The user requested deeper validation before publication. This report supersedes
the earlier preview's limits about full-history and actual Windows testing.
The candidate is built and tested locally; it has **not** been published.

## Problems found and corrected

1. Expired source renewal covered media fragments but not live-head requests.
   Both now renew the same representations and retry the same request.
2. Catch-up status depended on output presentation time. It now follows the
   contiguous fragments actually delivered in both inputs, so timestamp jumps
   cannot erase a real historical backlog.
3. A genuinely ended broadcast had no confirmed EOF path. Metadata confirmation
   now triggers fresh final-head checks before emitting end markers. A stall or
   unknown/error status never counts as a confirmed end.
4. Short-lived manifest handler threads retained one HTTP session per head query.
   A direct reproduction retained 20 sessions after 20 handler threads. Head
   sessions are now reused per track, with serialized access and bounded worker
   sessions. Forty-thread resource checks pass.
5. A source Origin header was being forwarded to the native-only DVR loopback
   view and rejected. A real FFmpeg fixture reproduced the failure. Upstream DVR
   requests retain the source headers; local DVR requests omit them. The ordinary
   HLS path accepts only its configured native Origin and rejects browser fetch
   metadata or other Origins. Both native source-header paths pass.
6. Bounded 429 retries now honor a numeric server Retry-After delay, capped to
   keep cancellation and failure handling bounded.

## Complete real-history and live-continuation test

The original user-reported broadcast ended during preparation, correctly
identifying itself as `was_live`; it was not treated as a current live source.
A second public live source (`6creglZ9lyc`) was selected for a complete test.

- The verified beginning exposed approximately **19150 seconds (5 h 19 m 10 s)**
  of history when the recording started.
- Capture started at broadcast sequence zero without fixture sequence remapping.
- It caught up with the actual moving live edge, then continued in live state
  for **at least 120 continuous wall seconds** before the requested test stop.
- The final MP4 contains **19988.735193 seconds (5 h 33 m 8.735 s)** and
  **451,898,961 bytes** of H.264 video plus AAC audio. Additional broadcast content
  arrived during catch-up, which explains the longer final duration.
- The entire file was decoded with `ffmpeg -v error -xerror`, not just a beginning
  or tail sample. It passed. Stream durations were 19988.734000 and
  19988.735193 seconds; their difference is about 1.2 milliseconds.
- Total test time, including finalization and full decode, was **865.39 seconds**
  (about 14 m 25 s). First logged live-state progress was near the end of catch-up;
  the stop condition required the subsequent two-minute continuous live period.
- Engine-process memory plateaued around **81–83 MiB** after warm-up. The test
  retained at most **6 HTTP sessions**, a five-entry cache per input during catch-up
  and three entries near the live edge. FFmpeg was monitored separately.

This is a low-resolution full-history soak, not a five-hour wall-clock soak.
Separate actual Windows tests cover HD operation below.

## Failure and lifecycle tests

Native FFmpeg fixtures verify retries of the **same** fragment after HTTP 503,
HTTP 429, an incomplete body, a connection reset and an actual socket read timeout.
The resulting audio/video files are strictly decoded. Missing old fragments stop
without a false successful MP4 and preserve the recoverable MKV.

Tests also cover source-head expiry/renewal, cancellation with pending downloads,
confirmed broadcast end, fresh final heads, unknown status, contiguous delivery,
quality/identity/language-filter preservation, non-public URLs, matching segment
durations, native Origin handling and browser-origin rejection.

The complete regression ran **518 tests with zero failures/errors/skips**. A
subsequently added real read-timeout scenario also passed separately. The existing
27 JavaScript suites pass with the same UI sources; the previous rendered tests
cover the ten-language DVR label, initial history and recording-limit percentage.

## Actual Windows candidate checks

These supersede the earlier headless-only preview checks:

- The real frozen Windows EXE starts, serves all referenced assets/APIs and
  exchanges native-host frames with its bundled companion bridge.
- Frozen MP4/MP3/M4A/WAV/Opus downloads and conversions pass FFprobe. Duplicate
  preservation, pause/process-restart/resume, error states and diagnostics pass.
- The actual EXE automatically selects from-start DVR through its restored-job
  and resume routes, enforces a one-minute cap and produces strictly decoded
  video plus audio.
- A native live pause -> process restart -> resume starts a new valid recording.
  Finish/save succeeds and the earlier partial MKV remains byte-for-byte intact.
- A source that ended after inspection is rejected without a completed file or
  a false successful history entry.
- Separate **720p and 1080p** from-start DVR recordings pass exact height checks,
  audio presence, duration cap and strict full-file decoding.
- An isolated installer fixture upgrades the actual installed **1.4.2** payload
  to **1.4.3**, verifies installed payload hashes, and preserves settings,
  language, history, drafts and paused work. Same-version reinstall and downgrade
  are blocked; clean install and profile-preserving uninstall pass. The final
  isolated fixture was removed. Production installation was not replaced.
- Seven bundled runtime files match source hashes. Five relevant compiled PYZ
  modules compare equal to compilation of the current source. Installer SHA-256
  matches its release metadata.

## Candidate and evidence

- Installer: `releases/v1.4.3/VideoDownloaderPro_Setup.exe`
- Size: **61,310,016 bytes**
- SHA-256: `55050ed3a34b9ee006ce52940278b2a2dc687eec63dfd6e6ada43ccc8acf34d3`
- Actual tested unpacked application: `dist/YoutubePro/YoutubePro.exe`
- Browser companion stays **0.4.1**.

Ignored local evidence: `build/dvr-release-soak-final/`,
`build/dvr-verified-regression/`, `build/dvr-fault-matrix-final.log`,
`build/dvr-read-timeout-test.log`, `build/dvr-origin-*-fix.log`,
`build/dvr-origin-fallback-tests.log`, `build/dvr-native-companion-1.4.3/`,
`build/dvr-native-runtime-1.4.3/`, `build/dvr-native-live-checks/`,
`build/dvr-native-hd-checks/`, `build/dvr-installer-acceptance-1.4.3/`, and
`build/dvr-final-candidate-hashes.json`.

The first long-test source had ended. An early live test was restarted after the
session-lifetime correction. Its retained partial fixture is not a passing final
test. The final complete soak above passed; follow-up header compatibility cases
and the actual Windows candidate cover the final request-header changes.

## Remaining boundaries

The from-start path requires an actually accessible, compatible YouTube DVR
beginning. Otherwise it retains the existing offered-window behavior and displays
that history scope. The duration cap includes history; a shorter cap intentionally
finishes before the live edge. Network/platform access failures cannot be removed,
but tested failure paths preserve partial work instead of claiming completion.

No 24-hour wall-clock soak, fresh Windows VM, production UAC/shortcut upgrade or
publisher signature was added. The installer fixture overrides identity,
destination, privileges and shortcuts to protect the production installation.
This candidate is ready for the established publication steps; no GitHub release,
tag or user installation was changed by this test task.
