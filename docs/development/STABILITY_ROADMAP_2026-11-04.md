# Stability release work — 4 November 2026

**Final state, 5 November: user authorized publication; 1.4.3 PUBLISHED stable/latest.**
See docs/releases/PUBLISHED_1.4.3.md for the unchanged tested installer hash,
release source commit and public download/updater verification. Unpublished or
running-test statements below are historical.

User approved implementing all six roadmap stages, preserving quality/performance.
No publication is authorized yet. Existing 1.4.3 candidates are superseded until
this work is finished and accepted. Root is not a Git checkout; `source-sync` is
the later publishing mirror and must not contain private fixtures/data.

## Current work

Final update, 5 November: corrected four-hour test PASSED (full decode/memory
gate), seven source hashes matched before rebuild. Fresh candidate at
build/endurance-release/candidate/VideoDownloaderPro_Setup.exe passed six-format
frozen media checks, source/PYZ/assets comparison and isolated installer upgrade/
clean/downgrade/uninstall acceptance (568 files). 607 Python tests passed.
See docs/testing/ENDURANCE_CANDIDATE_2026-11-05.md. UNPUBLISHED. Statements below
about a running test, blocking gate or required rebuild are historical.

5 November continuation: original endurance FAILED at 3h07m43.8s. Fixed invalid
fixture memory instrumentation/timestamps and added unconfirmed early-EOF guard.
Current seven-hash repeat: `four-hour-corrected`, exec 32630. Full 607-test
regression PASSED (endurance-review-regression.json). Three-minute real capture
and full decode passed. See docs/testing/LIVE_ENDURANCE_REVIEW_2026-11-05.md. Existing candidate
predates this fix: rebuild/revalidate only after the endurance gate passes.

1. Durable lifecycle/attempt/stage timing: `services/job_lifecycle.py`, integrated
   into queue manager. Publication intent is committed before rename, then the
   created-file identity is committed; `publication_recovery.py` avoids needless
   redownload after a crash between saving and history commit. Fault tests passed.
2. Live session ledger/export/join and guided recovery: implemented and tested.
   Preserve individual parts; never claim unknown continuity is verified. Join
   requires compatible actual stream signatures and explicit gap acknowledgement
   unless continuity is proven. Backend must accept IDs, not client file paths.
3. Quality: MP4/MKV video option and FFmpegVideoRemuxer replace automatic lossy
   VideoConvertor. Height caps no longer have an unrestricted fallback. New
   `media_quality.py` verifies actual selected codec/dimensions/fps/HDR when known.
   API accepts MKV for VOD only; existing live engine stays MP4. UI, ten-language
   messages and quality/history summaries implemented. Actual recovered MKV packet
   hashes match original media; codec/resolution/fps/HDR loss fault tests pass.
4. Resource/queue scaling and progress UX implemented: bandwidth samples bucketed
   into approximately 101 entries, unchanged rows skipped. Actual Chromium with
   1000 queue items: first localization 65 ms, unchanged poll 4.3 ms on this machine.
5. Recovery center implemented: publication completion, MKV retry, folder retry,
   max-quality retry, independent part exports, explicit discontinuous join and
   cancel. Removing queue entries archives part references into history. Actual
   ten-language stage/modal checks pass, no page errors; see build/stability/ui.
6. Final **602-test regression** passed, zero failures/errors/skips; 27 JavaScript
   tests and 23 targeted stability tests passed. Final Windows package passed
   five formats plus actual MKV/Defender, payload/source comparison and restart.
   Final isolated clean/upgrade/downgrade/uninstall acceptance passed (566 files).
   Final preview: build/stability-final-package; installer:
   build/stability/candidate-final/VideoDownloaderPro_Setup.exe. Opening median
   1.085 -> 1.099 seconds (no material difference measured). All prior candidates
   are superseded. Full evidence: docs/testing/STABILITY_RELEASE_2026-11-04.md.
   Four-hour endurance remains RUNNING (~76 minutes), not a passed gate.
   No publication done; do not claim release acceptance complete yet.

## Four-hour endurance already running

`scripts/check_recording_endurance.py --minutes 240 --label four-hour`, exec session
90037. Poll `build/stability/four-hour/result.json` for durable status. Low-bitrate
local HLS producer rotates its segments, captures four hours in real time, samples
RSS/threads/handles every 15 seconds, then strictly decodes the entire output.
Uses only workspace files and an owned loopback fixture; no user stream/account.

DO NOT CHANGE these six service files while the test runs: `live_recording.py`,
`live_network.py`, `live_catchup.py`, `media_process.py`, `windows_sandbox.py`,
`output_validation.py`. The test hashes them at start/end. New orchestration,
quality checks and session management go in new modules/wrappers. Their new
behavior requires additional short fault/recovery tests; the endurance validates
the unchanged capture engine. Do not call an unfinished four-hour test passed.

## Tooling / baseline

- Use `build/python314-secure/python.exe` (3.14.10/OpenSSL 3.5.9); requirements locked.
- Run tests via `build/run_security_tests.py`, elevated sandbox tool permission
  (normal medium Windows user token), which isolates APPDATA/settings/history.
  Native real downloads need the tool network override; do not weaken production guards.
- Previous performance candidate: `build/optimized-package`, installer
  `build/performance/candidate` (now superseded). Previous full regression 579 pass,
  27 JavaScript files pass. New tests/build must cover current changes.
- Do not stop an existing user app/recording. Native tests use the desktop mutex
  and must run sequentially, only after checking no user YoutubePro.exe is active.
- No subagents unless user explicitly asks. Do not modify personal settings,
  installed program, cookies or old release installers. Installation acceptance
  uses a separate identity/profile under build, then removes only that fixture.
