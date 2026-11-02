# Live history rate and visible progress recheck

The user reported an initial fast transfer followed by approximately 0.09 MB/s,
with no recognizable history/live indicator. The installed production payload was
confirmed as **1.4.1**, which does not include the new catch-up planner. Its recent
segments can arrive in a burst before recording follows newly broadcast content.
This explains that behavior if the installed application was used; it does not
prove the executable used for every user observation.

## Bounded real-source measurement

The reported public YouTube live source was accessible during this recheck.

- A 60-second H.264/AAC history sample completed in **7.16 wall seconds**.
- A longer sample captured **600.003401 seconds** and **53,142,976 bytes** in
  **34.92 wall seconds**, including final remux and strict full decode validation.
- After the first five seconds, observed rolling output rates ranged from
  **1.162 to 2.366 MB/s**. The final estimated lag remained about 3029 seconds,
  correctly identified as history catch-up rather than live recording.
- No sustained fall to 0.09 MB/s was reproduced in these bounded samples.

Reports contain codec metadata and numeric progress, not signed media URLs.
Local evidence: `build/live-catchup-real-check/result.json` and
`build/live-catchup-sustained-check/result.json`. These are short samples from
available history, not a complete hour-long archive or a long live-edge soak.
Throughput remains dependent on the server, connection and stream bitrate.

## Changes after the report

- Add a separate visible recording-state panel outside the ordinary speed row,
  with translated catch-up/live state, approximate lag and media-time pace.
- A pace of 12x means twelve seconds of broadcast captured per wall second.
  A low byte rate alone does not establish a slow media-time pace.
- Refresh output telemetry during an FFmpeg segment wait. The rolling rate and
  pace decay to zero instead of leaving the last number frozen onscreen.
- Preserve the same single output, audio validation and history-to-live flow.

Meaningful checks cover low-bitrate/fast-media progress, rate aging during a
stall, visible catch-up/live states, hiding the panel when paused, localization
and actual audio/video history-to-live transition. See the
[1.4.2 acceptance report](../releases/RELEASE_ACCEPTANCE_1.4.2.md) for final gates.
