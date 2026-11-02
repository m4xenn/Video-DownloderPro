# Video Downloader Pro 1.4.2 release acceptance

Validated on 2026-11-03 against the installed and public 1.4.1 baseline.

## Changes

Available, safely aligned HLS history downloads first without artificial pacing,
then the same recording follows new live segments. A temporary manifest endpoint
pins the inspected starting windows, preserving audio/video alignment. Sources
without a safe history start retain the existing recording path. The total
duration cap includes history. See [release notes](RELEASE_NOTES_1.4.2.md),
[design/local tests](../testing/LIVE_CATCHUP_2026-11-02.md) and the
[reported speed recheck](../testing/LIVE_RATE_RECHECK_2026-11-03.md).

A separate translated status panel shows catch-up/live state, approximate lag
and media-time pace. Rolling output-rate estimates refresh during segment waits
instead of leaving an old value frozen onscreen.

## Final verification

- **490 isolated Python tests passed**, zero failures/errors/skips; all **27
  JavaScript suites passed**.
- Native FFmpeg tests download 20 seconds of history in less than 3 wall seconds,
  then append newly published audio/video segments without restarting. Both
  multiplexed and separate input paths pass stream/duration and full decode checks.
- Real-source bounded tests of the reported YouTube live stream produced H.264
  video and AAC audio: 60 seconds in 7.16 wall seconds, then 600.003401 seconds /
  53,142,976 bytes in 34.92 wall seconds, including remux and strict decode.
  Output rates after startup ranged from 1.162 to 2.366 MB/s in the longer test.
  A sustained 0.09 MB/s slowdown was not reproduced in these samples.
- Unit checks distinguish small-byte-rate/fast-media progress from slow progress
  and confirm rate aging during a stall. Initial manifest pinning, alignment,
  failure fallback and Origin rejection are covered.
- Actual rendered UI checks pass across all ten locales, including visible
  catch-up/live panel, pace, delay, finish/save, responsive layout and no page errors.
- The final Windows frozen EXE opened its real APIs/assets and exchanged native
  stdio frames with its bundled browser host. Five changed runtime source/assets
  match their packaged SHA-256 hashes; required live modules exist in the PYZ.
- Real frozen-runtime MP4, MP3, M4A, WAV and Opus downloads/conversions passed
  FFprobe. Duplicate preservation, pause/process-restart/resume, failure reporting
  and sanitized diagnostics passed.
- An isolated current-user installer fixture used the actual installed 1.4.1
  payload, upgraded to 1.4.2, and verified **2064 payload file hashes**. Settings,
  language, history, drafts and paused work survived. The upgraded native EXE
  launched and read the preserved state.
- Same-version reinstall and downgrade were rejected. Uninstall preserved profile
  data; a clean application install passed; the final test fixture was removed.
  The user's production installation was not replaced.

## Artifact

- Installer: `VideoDownloaderPro_Setup.exe`
- Size: **61,278,615 bytes**
- SHA-256: `338384de943d0f620d4b6c49af00776ac2b41733c6805646fc64d578ef319c14`
- Browser companion stays **0.4.1**; no extension update is required.

Evidence lives under `build/release-final-tests-1.4.2/`,
`build/release-native-companion-1.4.2/`, `build/release-native-runtime-1.4.2/`,
`build/installer-final-acceptance-1.4.2/`, `build/release-help-1.4.2.log`,
`build/release-final-payload-1.4.2.json` and the two real-source check directories.

## Limits and publication

The first unpublished candidate was archived after the user's speed report.
Earlier headless checks ran packaged bytecode under installed Python while the
production app was recording; they are superseded by the final actual frozen-EXE
and native installer checks above. An initial headless fixture compared mutable
Python cache files and failed its hash check; the final native fixture passes
all payload hashes without that substitution.

No fresh Windows VM, production UAC/shortcut upgrade or publisher signature was
added. Installer fixture identity, privileges, shortcuts and destination were
overridden. Full-hour archive retrieval and prolonged live-edge recording were
not performed; history retention, network throughput and access depend on the
source. No login, bot-check, DRM or regional bypass is added.

Publication uses the matching source commit/tag and exactly the installer and
checksum assets. Post-publication digest/tag verification, public-download hash
and old/current updater checks are retained under `releases/v1.4.2/`.
