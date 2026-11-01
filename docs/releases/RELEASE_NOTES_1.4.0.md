# Video Downloader Pro 1.4.0

This release builds on 1.3.0 with a browser companion, a Recovery center and
stronger download validation, streaming support and restart handling.

## Browser companion for Chrome, Edge and Brave

- Let your normal browser help find embedded videos when direct extraction
  cannot resolve the source. Play the video or complete site verification when
  prompted; the detected source returns to the application.
- Guided setup in **Settings → Browser companion**, with bundled extension files,
  native bridge, app logo, connection status and help in all ten app languages.
  No separate Python or command-line setup is needed.
- Clearer source labels distinguish the main stream, actual resolutions, audio
  and subtitle tracks. A verified HLS master can be selected automatically;
  unrelated or ambiguous sources still require a choice.
- **Open video in browser** brings the relevant app-owned inspection tab forward.
  Repeated inspections share a pending job instead of opening duplicate tabs.
- Companion 0.4.1 follows the application's language, including source labels and
  connection messages. Language changes synchronize during normal communication;
  the last matched language is kept while disconnected within the browser session.

The companion is an optional unpacked extension, not a browser-store installation.
Preparing its local connection requires explicit consent. The browser still asks
you to enable Developer mode and load the prepared extension folder. Existing
preview users should prepare the updated files and reload their extension.

## Recovery center and safer app closure

- **Recovery center** in the Queue page shows unfinished work, its last saved
  progress and useful Resume / Refresh source and retry actions.
- Interrupted jobs return paused after reopening. The original output target,
  options and source checkpoint are preserved; resume remains user-controlled.
- A second launch now shows an already-running notice instead of opening another
  application instance.
- Closing during queued or active downloads asks for confirmation. Cancel keeps
  working; confirm stops transfers, preserves partial files and saves the queue.
  Files already being processed finish safely before the window closes.
- If queue saving fails, the application stays open and explains the storage
  problem. Output identity is saved before transfer starts, improving recovery
  even after an abrupt process interruption.
- Some Windows merge-finalization file locks can recover with a bounded final
  rename retry, without repeating the download or merge.

## More reliable embedded downloads

- Better common-player, nested-frame, lazy-player and network-source discovery,
  including additional Artplayer/Playerjs and watch-page activation cases.
- Stronger HLS/DASH support for separate audio/video/subtitles, fMP4 byte ranges,
  rotating ordinary AES-128 keys, and static/dynamic DASH test coverage.
- Choose source-declared audio and subtitle languages for a single inspected
  video. Choices persist in history/repeats; an unavailable explicit language
  fails clearly instead of silently selecting another track.
- Expired-source recovery keeps the existing media identity and partial-file
  protections. A changed signed URL can resume only when the required strong
  resource validators and selected media representation match.
- Better compatibility with some embedded servers that reject ordinary HTTP
  transport, using a bounded browser-compatible retry when available.
- Earlier detection of explicitly marked previews and truncated MP4 sources.
  Completion checks verify expected streams, duration and readable file tails
  rather than trusting progress reaching 100%.
- Clearer error categories for file access, storage, unavailable videos and
  regional restrictions, with sanitized diagnostic reports.

## YouTube country preference discovery

On eligible YouTube availability errors, the app can try a bounded sequence of
player country preferences and use the first playable result. This worked for
the tested country-domain restriction without a VPN or proxy. It is not an IP
change and does not guarantee access to every region-restricted video.

## Live recording and measured transfer mode

- Record one inspected live video to MP4 with a duration limit of 1–1440 minutes,
  an optional stop time within the next 24 hours, and a **Finish and save** action.
- Bounded reconnect and supported HLS segment retries reduce interruption loss.
  Detected exhausted segment retries stop with a clear error and preserve the
  captured temporary recording instead of reporting a complete success.
- Stable transfer remains the default. Optional measured acceleration tests
  limited fragment concurrency between eligible jobs and rolls back on errors
  or insufficient gain. Actual speeds depend on the source and your connection.

## Compatibility and limits

- Existing settings, history, drafts and paused jobs are preserved during upgrades.
  Application updates and yt-dlp/FFmpeg component updates remain separate.
- Resume depends on source/server support and a verifiable representation.
  A source refresh does not permit mixing different media into an old file.
- Live recording does not recover unavailable past live windows. Starting again
  creates a new recording. Live subtitles, audio-only live export and the shared
  positive download speed cap are not supported for live capture.
- DRM-protected services still require their supported licensing/offline flow.
  No general DRM decryption, CAPTCHA solver or universal site support is included.
- Known partial previews are not full recordings. Short sample tests and source
  discovery do not establish full-length availability on every website.

Download **VideoDownloaderPro_Setup.exe** to install or upgrade.
**SHA256SUMS.txt** contains the installer checksum.
