# Live history catch-up — unpublished development change

Available HLS history now downloads without input pacing before the same FFmpeg recording follows newly published segments. The queue distinguishes catch-up from real-time recording and shows approximate remaining delay in all ten application languages. The duration limit includes downloaded history: a limit shorter than the available history can finish before reaching the live edge.

## Implementation

- Inspect bounded variant playlists with verified public URLs and bounded redirects/timeouts. Use the earliest available segments, rather than the usual recent-segment start.
- Separate audio/video renditions require a shared UTC program-time boundary. Initial discontinuities, unknown alignment, failed inspection, ended playlists and non-HLS sources retain the existing recording path.
- Pin the inspected initial manifests behind a temporary tokenized loopback endpoint so a rolling-window update while opening the second input cannot shift its starting point. Subsequent manifest requests refresh upstream. Segment bytes still travel directly to FFmpeg; relative media/key/map references become absolute. The endpoint rejects browser Origin requests and closes with the recording.
- Use stream copy and the existing retry, gap detection, recoverable MKV and validated MP4 completion path. No process restart or second output file is needed at the live edge. Source manifests and signed URLs are held in memory, not written to diagnostic reports.
- FFmpeg HLS option reference: [official formats documentation](https://ffmpeg.org/ffmpeg-formats.html#hls). Setting the earliest live start does not make unavailable or expired segments accessible.

## Validation

- Final isolated regression: **488 tests passed, zero failures/errors/skips**, report `build/live-catchup-final-regression/result.json`.
- All **27 JavaScript suites passed**, including translated catch-up state and delay rendering.
- Two native FFmpeg fixtures: 20 seconds of history captured in less than 3 wall seconds, followed by newly published live segments in the same file; both multiplexed and separate inputs. Finished files contain synchronized audio/video and pass a complete strict decode.
- Planner tests cover shared program-time alignment, safe fallback, cancellation, malformed/oversized playlists, pinned-first/reloaded-next manifests and endpoint Origin rejection.
- Real rendered UI acceptance passes in all ten languages, with catch-up status/delay assertions and no page errors. Screenshots are under `build/download-tools-ui`.
- Earlier manifest-only inspection of the reported YouTube source found 720 segments / 3600 seconds in each selected rendition, aligned at indices 0/0. The subsequent short real capture attempt was blocked by YouTube's bot verification, so a real YouTube catch-up recording is **not validated** in this change. No full-hour transfer was attempted.
- PyInstaller preview built successfully at `build/live-catchup-package/YoutubePro/YoutubePro.exe`. Four changed runtime sources and ten live guide images match their packaged SHA-256 hashes. GUI smoke could not open its API because the installed application was already running; the duplicate-instance guard correctly prevented a second app. The installed process was left running.

## Release state

This is an unpublished preview based on 1.4.1. No installer, public release, updater metadata or installed application was replaced. Close the installed application before opening the preview. Available history and download throughput depend on the source and connection; reaching the live edge then returns to the stream's natural recording data rate.
