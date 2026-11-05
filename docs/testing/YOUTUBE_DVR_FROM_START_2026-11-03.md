# YouTube DVR from the beginning — 1.4.3 development preview

The subsequent [release-readiness validation](DVR_RELEASE_READINESS_2026-11-03.md)
includes fixes, a complete multi-hour archive-to-live test, full-file decode,
actual Windows HD/lifecycle checks and installer upgrade acceptance. It supersedes
the incomplete full-archive/native-GUI coverage stated for the initial preview below.

The short HLS manifest used by 1.4.2 exposed only the latest hour of the reported
stream. It could catch that window's edge without downloading preceding hours.
The new YouTube-specific path selects and verifies a from-start adaptive DVR
source instead of treating that short window as the entire broadcast history.

## Implementation

- Re-extract with yt-dlp's from-start setting and a matching MP4 video/M4A audio
  pair. Preserve the video identity, selected resolution/FPS and existing audio
  language filters. Restore the original yt-dlp parameters and compiled format
  selector afterwards. Other sites keep their existing path.
- Verify sequence zero in both tracks before opening any output. Require complete
  self-initialized MP4 fragments and a shared segment duration. Unavailable or
  incompatible beginning falls back before output to the ordinary available HLS
  window; the UI distinguishes **DVR from the beginning** from that window.
- Download up to three fragments concurrently through one shared worker pool.
  Keep three pieces of lookahead per track and a small rewind cache. Each complete
  fragment is limited to 16 MiB; partial/malformed data is never served to FFmpeg.
- Serve ordered fragments through a tokenized loopback HLS view from sequence zero
  to the moving source head. FFmpeg writes one recoverable MKV throughout catch-up
  and live capture, then validates and remuxes the completed recording to MP4.
- A missing fragment after capture starts stops with a fragment error and preserves
  temporary data. It is never silently skipped or replaced with the shorter live
  window. An expired 403 source may refresh only to the same representation IDs,
  retrying the same sequence number.
- Retain public-address checks for every request/redirect, scoped request headers,
  finite network retries and bounded buffers. No signed URL, manifest, cookies or
  credentials are persisted by this service.
- Preserve finish/save, pause behavior, scheduled stop and the total duration cap.
  **The cap includes history**: it must cover the past plus desired live duration
  to reach the live edge. Resuming an interrupted live job still creates a new
  recording; this change does not append a new source to an older partial file.

The interface now retains the initial history duration, labels live percentages
as **Recording limit**, and shows a translated from-start DVR label. The ten
languages and ordinary history-window path remain supported.

The underlying [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp#usage-and-options)
describes `--live-from-start` as experimental. This integration requires sources
that actually retain accessible MP4 DVR fragments; it does not promise every
channel, codec, retention period or access restriction is supported.

## Verification

- **502 Python tests passed**, zero failures/errors/skips, including 12 new DVR
  tests. All **27 JavaScript suites passed**.
- Native local tests consume history in parallel, follow newly published segments
  in the same synchronized audio/video file, strictly decode it, and verify a
  missing old fragment preserves a partial rather than skipping forward.
- Unit checks cover initialized media, source identity/quality preservation,
  selector restoration, cancellation, non-public URLs, inaccessible beginnings,
  matching segment durations and safe source refresh at the same sequence.
- Real-source probes returned HTTP 200 for both sequence zero and pieces older
  than the short HLS window. A source with 4707 five-second sequences advertised
  about 6 h 32 m of history. A native recording of the first minute completed in
  **2.19 wall seconds**, with selected audio and video. This was a bounded beginning
  sample, not the whole broadcast.
- A longer beginning test was deliberately stopped at its six-minute network
  budget after **12317.4 seconds** of media (about 3 h 25 m), with video and audio.
  It correctly remained in catch-up because it had not yet consumed the complete
  roughly 6 h 39 m history. Its manual harness reports the unmet full-catch-up
  assertion; this is not counted as a completed full-broadcast test.
- Separate bounded real-edge validation covered a **65-minute DVR interval**
  through the real moving live edge and continued recording. It produced
  **3990.116780 seconds** of synchronized H.264/AAC in **96.27 wall seconds**,
  including final checks. Video/audio durations differed by about 0.117 seconds.
  Beginning and tail decode checks passed. To bound traffic, this fixture remapped
  upstream sequence numbers/headers only inside the test; broadcast sequence zero
  was verified separately above. Production code has no trimming option.
- The actual packaged application bytecode, Flask download route, queue and
  worker pipeline automatically selected from-start DVR and preserved its history
  scope in progress. A 60-second H.264/AAC output passed FFprobe in **8.95 wall
  seconds**, including fresh metadata extraction, preparation and finalization.
- Rendered UI checks pass in all ten locales, including the Turkish from-start
  DVR/history duration panel and explicit recording-limit percentage.
- PyInstaller preview builds successfully as 1.4.3. Five changed runtime files
  match their packaged hashes and the required modules exist in the PYZ. Two
  native FFmpeg DVR tests also pass using the actual packaged service files.
  The packaged app/native-host messaging check passes headlessly under installed
  Python while the user's production recording stays active.

Evidence is under `build/youtube-dvr-regression/`, `build/youtube-dvr-probe/`,
`build/youtube-dvr-full-check/`, `build/youtube-dvr-edge-check/`,
`build/youtube-dvr-api-check/`, `build/youtube-dvr-package-runtime/`, and the
`build/youtube-dvr-*.log/json` files. UI screenshot:
`build/download-tools-ui/recording-dvr-tr.png`.

## Preview state and limits

Preview executable: `build/youtube-dvr-package/YoutubePro/YoutubePro.exe`. The
entire adjacent `_internal` directory is required. The production application must
finish/stop and close before this preview can open because the single-instance
guard is retained. Existing active recordings do not switch implementation.

No new installer or GitHub release was published and the installed app was not
replaced. Actual Windows bootloader/WebView2 startup with this preview was not
retested while the user's application was recording; packaged code/API/media
checks used the installed Python runtime with the exact bundled app bytecode and
service files. No complete multi-hour archive-to-edge transfer was certified.
