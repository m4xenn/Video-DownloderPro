# Video Downloader Pro 1.4.2

## Catch up with a live stream, then keep recording

- Supported HLS live streams now download their available history as fast as the
  source and connection allow, then continue recording newly published content
  into the same file automatically.
- Separate audio and video inputs are aligned using shared broadcast timestamps.
  The initial playlist snapshots are retained to prevent a rolling history window
  from shifting one input while the other is opened.
- The queue shows **Catching up**, an approximate remaining delay, and the actual
  download data rate. It switches to **Real time** near the live edge.
- A separate, prominent recording status displays the catch-up pace, such as
  **12x** for twelve seconds of broadcast captured per second. Output-rate
  estimates refresh while waiting for data instead of freezing the last value.
- The recording explanation and new progress labels support all ten app languages.

Only history still exposed by the source can be retrieved. Sources without a safe
history start retain the existing live recording behavior. This feature does not
bypass login, bot verification, DRM or regional access restrictions.

**The selected total recording duration includes history.** Choose enough time
to cover the available history and the additional live recording you want.
Once caught up, recording follows the broadcast's natural pace.

Existing live audio validation, finish/save controls and interrupted-recording
recovery are retained. Settings, history and paused jobs are preserved. The
browser companion remains 0.4.1; no extension update is required.

Download **VideoDownloaderPro_Setup.exe** to update. **SHA256SUMS.txt** contains its
checksum. Finish or pause active work and close the app before installing.
