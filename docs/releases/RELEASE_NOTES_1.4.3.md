# Video Downloader Pro 1.4.3

## Stability and recovery

- Persists download attempts, processing stages and publication checkpoints. A
  crash after saving a completed file can be recovered without downloading again;
  changed destination files are preserved and require attention.
- Keeps interrupted live recording parts and their recovery references, including
  after removing the queue item. Export individual parts or explicitly join
  compatible parts without re-encoding. Gaps between sessions are not assumed to
  be continuous; joining requires acknowledgement.
- Adds MP4/MKV selection for downloaded video. Preserves selected video streams
  by remuxing and checks known codec, resolution, frame rate and HDR expectations.
  Container incompatibility and quality mismatch offer guided recovery choices.
- Adds stage elapsed time, clear processing indicators, folder recovery and
  cancellable recording exports in all ten languages. Reduces unchanged queue
  updates and bounds bandwidth telemetry memory.
- Avoids reporting an unconfirmed early live-source exit as a completed recording;
  preserves the partial recording for recovery.
- Passed the corrected four-hour recording test with full audio/video decode and
  memory-growth checks. Final package and installer evidence is tracked in
  `docs/testing/ENDURANCE_CANDIDATE_2026-11-05.md` (607 Python tests, actual frozen
  downloads and isolated clean install/upgrade acceptance).

## Performance and readiness

- Prepares source support in the background while the desktop window initializes, preserving first-link responsiveness.
- Reuses the duration already obtained during media validation for previews. Reuses a completed live validation only within the same job while Windows prevents data writes to that unchanged file; unsupported locks or changed inputs trigger full validation.
- Controlled local MP4 processing took about 12% less time and preview preparation about 39% less time in five-run comparisons. Internet download speeds still depend on the source and connection.
- Passed 607 Python tests, 27 JavaScript suites, actual frozen downloads/security scans, four-hour recording and isolated installer upgrade acceptance. See `docs/testing/PERFORMANCE_OPTIMIZATION_2026-11-04.md` for the earlier controlled performance measurements and `docs/testing/ENDURANCE_CANDIDATE_2026-11-05.md` for the final candidate.

## Protected media processing

- Uses private resumable staging and restricted Windows media processes, with bounded memory, child processes and diagnostic output.
- Verifies actual media contents and streams before publishing a completed download. Existing files are never overwritten.
- Attempts a local Windows Defender scan without extra prompts. Unavailable scans are stated clearly; files requiring review are withheld.
- Adds security progress in all ten languages and preserves interrupted work. USB/network destinations can use a protected local staging area.
- This provides write confinement, not a full AppContainer or complete file-read isolation. See `docs/testing/MEDIA_SECURITY_2026-11-04.md` for validation and scope.

## Vulnerability audit fixes

- Updates eight vulnerable Python dependencies and the bundled Python/OpenSSL runtime to security-patched releases.
- Closes an additional proxy-origin IP validation gap and hardens XML manifests, image decoding and native bridge handling.
- Disables the source-entry interactive debugger. Adds security runtime checks to future builds and pins runtime dependency versions.
- The updated Windows payload requires Windows 10 or later on an x64-compatible system.

## Safer link handling

- Blocks web-page attempts to control the local app and unsafe links targeting local devices or files.
- Adds protected HTTP redirects/IP handling and a guarded network path for live recording, including HLS/DASH resources.
- Restricts the source browser's permissions, downloads, popups and external application launches.
- Fetches cover images through bounded local previews and preserves Windows Internet-zone marking for downloaded media where supported.

## Language and notification preferences

- Application warnings, queue errors and completion notifications follow the selected language in all ten supported languages.
- Completion notifications can always appear, appear only while the app is in the background, or be disabled. The preference is preserved after restarting.
- Language changes also refresh visible queue errors and browser interaction notices.

## YouTube DVR from the beginning

- Compatible YouTube live streams now use a verified from-start DVR source,
  rather than being limited to the recent HLS window.
- Available historical fragments download in bounded parallel requests, in order,
  then the same file continues recording newly published live content.
- The beginning is verified in both selected tracks before capture starts. If a
  compatible beginning is unavailable, the existing offered-window path remains
  available and its initial history duration is shown.
- Catch-up status follows the actual contiguous fragments delivered to the
  recorder, avoiding false live-state changes caused by output timestamps.

## More reliable long recordings

- Expired source renewal covers both fragments and live-head queries.
- Live-head HTTP sessions are reused to prevent connection/session accumulation
  during long recordings.
- Confirmed broadcast end now finishes the recording after checking the final
  source heads. A connection stall or unknown status is not treated as the end.
- Improved bounded retries for server rate limits and source-header compatibility
  through the local recording bridge.
- Missing fragments stop with an error and preserve temporary work instead of
  silently skipping to the live edge or publishing a successful incomplete file.

## Clearer progress

- Displays the initial available history and distinguishes from-start DVR.
- Labels the percentage as **Recording limit**; it is not the percentage of a
  broadcast archive. These controls support all ten application languages.

**The selected duration cap includes history.** Choose enough time to cover the
available past and the additional live recording you want. At the live edge,
recording follows the source's natural pace; future content cannot arrive early.
From-start DVR depends on the source retaining accessible compatible fragments.

Settings, history and paused work are preserved. A paused/interrupted live job
still starts a new recording when resumed; its earlier partial is retained.
The browser companion remains 0.4.1 and does not need an extension update.

Download **VideoDownloaderPro_Setup.exe** to update. **SHA256SUMS.txt** contains the
checksum. Finish or pause active work and close the app before installing.
