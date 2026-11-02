# Video Downloader Pro 1.4.1 release acceptance

Validated on 2026-11-02 against the 1.4.0 stable baseline.

## Changes

Selected audio-only HLS streams with an unknown codec are retained and required
in live output validation. Live rate/clock display is corrected, including the
aggregate queue rate and the general localization pass. All ten languages explain
real-time capture. See [release notes](RELEASE_NOTES_1.4.1.md) and
[live audio evidence](../testing/LIVE_AUDIO_AND_RATE_FIX_2026-11-02.md).

## Verification

- **476 isolated Python tests passed**, zero failures/errors/skips.
- All **27 JavaScript UI suites passed**.
- Real split HLS with unknown audio codec produced audible audio/video; a selected
  source without audio was rejected instead of publishing a silent successful MP4.
  Existing dynamic DASH, live stop/pause/segment retry and recovery checks passed.
- The reported public YouTube live source was tested during this correction:
  H.264 video plus AAC audio, 24.984 seconds and 2,058,956 bytes. Decoded audio
  measured -25.1 dB mean, confirming it was not empty. This was a short sample,
  not a complete long-running broadcast certification.
- Rendered live controls passed ten-language, duration/rate/localization, stop
  action and responsive checks. Guide captures were regenerated for this version.
- The actual 1.4.1 frozen EXE served its bundled assets and APIs, exchanged real
  native-host messages and matched the tested live/queue/interface source files.
- Frozen runtime MP4/MP3/M4A/WAV/Opus downloads passed FFprobe. Duplicate protection,
  pause/restart/resume, error states and safe diagnostic reporting passed.
- Isolated current-user installer acceptance upgraded the actual installed 1.4.0
  payload to 1.4.1. Settings, language, history, drafts and paused work survived;
  all installed payload files matched the distributable hashes.
- Same-version reinstall and downgrade were rejected. Uninstall preserved profile
  data, a fresh application install passed, and the final test fixture was removed.
  The real production installation was not upgraded by these tests.

## Artifact

- Installer: `VideoDownloaderPro_Setup.exe`
- Size: **61,256,644 bytes**
- SHA-256: `485803a600f8e2bbfcc62d279c61cb3b5bb42ca2e862c1b55a4f0772d56743c4`
- Companion remains **0.4.1**; this patch does not require a companion upgrade.

## Evidence and limits

Local evidence is under `build/release-tests-1.4.1/`,
`build/release-runtime-1.4.1/`, `build/release-companion-1.4.1/`,
`build/installer-acceptance-1.4.1/`, `build/release-help-1.4.1.log` and the earlier
`build/live-audio-real-check/` (all ignored by Git).

No fresh Windows VM, production UAC/shortcut upgrade or publisher signature was
added. Fixture identity, destination and privileges were overridden to avoid
modifying the user's real installation. Live capture remains paced by the source;
this patch does not promise accelerated retrieval of past/future broadcast data.
Previously silent files do not acquire missing audio through this update.

Publication follows the exact source commit/tag, two release assets, GitHub digest
verification, public-download hash check and old/current updater checks described
in the publishing guide. Post-publication evidence stays in `releases/v1.4.1/`.
