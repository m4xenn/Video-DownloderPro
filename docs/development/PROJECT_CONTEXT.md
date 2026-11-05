# Video Downloader Pro — project context

Reviewed on 2026-11-01 against two supplied conversation exports, current source,
the development/release guides and architecture/testing reports. This is a
navigation and handoff note, not a new test run or release acceptance report.

## Product intent and established decisions

- Windows desktop video downloader for public distribution. The desired flow is
  paste a page URL, inspect its actual qualities/tracks, then download with as
  little manual interaction as the source permits.
- Prefer improvements to shared player/protocol discovery over film-URL-specific
  patches. Existing site/player adapters remain useful fast paths.
- Solutions must work for other users, not depend on the developer's personal
  browser profile, installed Python, private VPN, or hard-coded local paths.
- Keep the established navy/blue workspace, fixed outer panel dimensions, inline
  Queue/History/Guide/Settings pages, accessible scrolling and ten-language UI.
- Clip downloading was explicitly deferred. The short clips used in technical
  tests do not mean that a user-facing clip feature was added.
- Preserve existing completed files, settings, queue and history through changes
  and upgrades. Correct output matters more than counting discovered URLs.

## Current version and evidence boundaries

- Development `version.json` is `1.4.3` (unpublished YouTube from-start DVR preview);
  public stable remains `1.4.2`. See [DVR validation](../testing/YOUTUBE_DVR_FROM_START_2026-11-03.md).
  Bundled/development requirement is
  `yt-dlp==2026.8.19`. Verified component updates can supersede the bundled engine
  at the next process startup (`component_runtime.py`).
- The supplied history records publication of 1.2.14 and then 1.3.0. The 1.4.0 release preparation subsequently confirmed the live stable baseline
  and installed payload as 1.3.0; consult the release acceptance report for the
  final 1.4.0 validation.
- The companion source manifest is `0.4.1`. Guided setup, protocol/recovery/live
  improvements and this chat's country search are source developments; do not
  assume that the installed or public 1.3.0 package includes them.
- Source readiness, frozen-app checks, production installation, public release,
  metadata success, bounded media sampling and full-length output verification
  are different states. Always identify which evidence supports a claim.
- Historical test totals (270, 295, 361, 399, 438, etc.) describe different
  milestones. They are not a fresh combined regression result.

## Runtime map

| Area | Entry points and responsibility |
| --- | --- |
| Desktop | `src/main.py`: maximized pywebview window, browser helper/extension bridge lifecycle. |
| Application/API | `src/app.py`: Flask routes, metadata inspection, queue submission, playlists/history, local previews, settings, updates and companion setup. |
| Interface | `src/templates/index.html`, `src/static/workspace.*`, `studio.*`, `help.*`, `history-preview.js`, localization modules, `track-selection.js`, `download-tools.js`, `source-progress.js`, `companion-setup.js`. |
| Queue | `src/core/queue_manager.py`: one shared scheduler/worker pool, restored jobs, retries, progress, conversion semaphore and completion records. |
| Selection/output | `src/core/format_resolver.py`, `output_paths.py`: real source qualities, audio formats, FFmpeg postprocessing, distinct reserved output stems. |
| Transfer | `src/core/downloader.py`: resolve fresh media, retain browser context, apply selected tracks, validate resume, transfer, recover once where permitted, validate completed output. |
| Scheduling/speed | `adaptive.py`: concurrent jobs; `bandwidth.py`: shared native-response byte budget; `fragment_policy.py`: separate opt-in fragment concurrency measurements. |
| Persistence | `services/download_store.py`: SQLite queue/drafts/history and track options; `utils/file_helpers.py`: atomic JSON settings; `state/app_state.py`: live shared state. |
| Native discovery | `site_resolver.py`, `generic_resolver.py`, `site_browser.py`, `webview_frames.py`, `media_discovery.py`, `network_media.py`, `player_activation.py`, `player_controls.py`, `poster_navigation.py`. |
| Extension | `browser-extension/`, `extension_bridge.py`, `companion_setup.py`, `scripts/extension_native_host.py`. |
| Protocols/validation | `hls_metadata.py`, `dash_metadata.py`, `manifest_relations.py`, `source_validation.py`, `media_preflight.py`, `output_validation.py`. |
| Recovery | `source_operation.py`, `source_recovery.py`, `browser_transport.py`, `merge_recovery.py`. |
| Updates | `app_update_service.py` for the application; `component_updater.py` and `component_runtime.py` for media components. |

Ordinary runtime state lives in `%APPDATA%/YoutubePro`: `settings.json`,
`downloads.sqlite3`, `diagnostics.sqlite3`, `previews/` and media tools in `bin/`.
Some testable services honor `VIDEO_DOWNLOADER_DATA_DIR`; settings use their own
configured constants, so that environment variable alone does not isolate every
settings read/write. Keep diagnostic fixtures away from personal data.

## Discovery and browser handoff

1. `extract_media_info` routes a known FullHD/Rapidvid page through its adapter,
   reuses a pending generic inspection where applicable, and otherwise tries
   native yt-dlp extraction. Eligible native failures enter generic discovery.
2. Generic discovery first reuses a recent resolved source. A connected companion
   is then consulted before the internal WebView2 exploration path. Do not assume
   the current source always tries WebView2 before the extension.
3. The internal browser retains actual iframe ancestry and inspects player APIs,
   DOM and successful network responses, including extensionless manifests.
   Player/frame correlation matters; an arbitrary media URL is insufficient.
4. Known player APIs, labelled play gates and observed watch-state navigation
   trigger playback. Ambiguous ads/players are not selected by blind clicks.
5. Human verification/login can require a visible browser and user action.
   Automatic continuation checks exist; a local LLM/CAPTCHA solver was not added.
6. Preview browser sessions can be handed to the download operation. They are
   retained until initial media bytes arrive or the bounded lifecycle releases
   them; playback is paused to avoid a second competing transfer.

The native path can carry source-scoped request context. Captured Cookie headers
must not become global headers; cached HTTP handlers are rebuilt when necessary.
The companion intentionally does **not** capture personal cookies or Authorization
headers. Its current result payload includes source, page context and media type;
cookie-bound sources may still fail outside the browser.

## Companion distribution and consent

- Chrome, Edge and Brave; MV3 extension, stable public-key-derived identity.
- Settings wizard prepares bundled extension/native-host files, opens the
  browser's extension page, helps select the folder and checks a current-version
  heartbeat. The end user still loads the unpacked extension in Developer mode.
- No browser store publication or silent extension installation is established.
- Explicit setup consent gates per-user native-host registration; status/startup
  checks do not register it. Chrome/Brave share the tested compatible host key.
- Native stdio messaging reaches the application's authenticated loopback bridge.
  Only app-owned pending tabs/jobs are focused or tracked by the workflow.
- The extension distinguishes master/variant/audio/subtitle candidates and can
  automatically select a sole verified HLS master. Independent roots stay manual.
- Version 0.4.1 receives the live app language in each native reply and translates
  popup/job/source labels in all ten languages. Browser language is the initial
  fallback; the last app locale survives disconnect within the browser session.

## Implemented reliability and protocol work

- HLS/DASH, separate audio/video and subtitles, ordinary publisher AES-128,
  rotating keys, fMP4 byte ranges and synthetic live/static DASH coverage.
- Clear media, ordinary encryption, unknown unsupported encryption and known DRM
  have separate outcomes. No general Widevine/PlayReady/FairPlay decryption or
  provider license integration is implemented.
- Single inspected videos can choose source-declared audio/subtitle languages.
  An unavailable explicit choice fails rather than silently changing language.
  Bulk/playlist paths retain automatic/default track behavior.
- Partial files are not appended to a different video, format or selected audio
  language. Changed signed URLs require matching strong resource validators for
  verified resume; signature changes alone are not sufficient.
- Embedded 403 recovery is bounded. Browser-compatible transport can retry once
  where available; source renewal also requires identity/partial-file checks.
- Exact Windows merge-finalization locks have bounded rename-only recovery after
  output validation. This is not a general restart-time temporary-file recovery
  center or a reason to re-download already completed bytes.
- Preflight compares MP4 declared extents with exposed bytes. Final embedded
  validation checks actual streams, expected duration, readable tail packets and
  a short tail decode; artwork is not counted as a video stream.
- Stable embedded transfer defaults to one fragment. Optional measured mode tests
  up to three between jobs and rolls back on failures/no gain; it excludes short,
  overlapping, capped and live measurements. The recorded 1.98x gain was a
  controlled benchmark, not a public-CDN promise.
- Live capture supports one inspected MP4 video, a 1–1440 minute limit, optional
  stop time and finish/save. Temporary recording is preserved on failure/pause;
  resumed live capture starts a new file. Live subtitles, audio-only live output
  and the shared positive bandwidth cap are not supported.

## Specific investigations to remember

- **StreamRecorder:** the inspected public sources exposed only 200,000,000 bytes,
  despite MP4 headers describing roughly 6.43/2.64 GB and 4h24m50s. Original-tail
  requests returned 416; the user also could not seek to the end in the browser.
  This was partial preview access, not proven DRM or a supported full VOD.
  A historical indexed Kick page was not proof of a currently available replay.
- **YouTube in this chat:** changing the page locale or preference cookie alone
  failed, but setting `client.gl=DE` in the actual player request worked on the
  same network with the existing engine. A real 5.021-second audio/video sample
  was downloaded and inspected. No whole-video completion was established.
- `youtube_region.py` now tries normal extraction first, then DE/US/GB/NL/FR/CA on
  eligible availability failures. It stops at playable metadata, skips empty,
  storyboard-only and DRM results, respects cancellation and stops on unrelated
  errors/rate limits. Extractor/context changes are instance-scoped and restored.
  Its 45-second budget is checked between calls, not a hard interruption of an
  in-flight extractor. Country preference is not an IP change or universal bypass.

## Remaining work versus already implemented foundations

Still open or only partly covered: long real-world downloads/discontinuities,
broader repeatable site acceptance, broader postprocessor recovery, simpler
ambiguous-source UX, browser store distribution, scheduled queue/night rules,
file organization profiles, and expanded live continuity/splitting. Basic queue
restore, track selection, rename recovery and bounded live capture already exist;
do not propose them as entirely absent features.

Follow-up in this chat (2026-11-01): a queue Recovery center, single desktop
instance, close confirmation and durable asynchronous shutdown are implemented.
Graceful and abrupt process restart passed actual local Range-resume and complete
audio/video integrity checks. A separate unpacked app passed frozen checks;
production installation/public release remain unchanged. See the
[recovery acceptance report](../testing/RECOVERY_AND_SHUTDOWN_2026-11-01.md).

Documentation has historical drift: the root README's source-code footer still
points to 1.2.14, and older scheduler docs mention fragment defaults superseded by
the current embedded policy. Use current code plus the relevant recent report.
The root working source and `source-sync/` checkout must be compared explicitly
before release; do not assume a local edit is committed, mirrored or published.

## Release and validation workflow

- Build via `scripts/build_release.py --version X.Y.Z`: frozen app, bundled
  companion/native host and Inno installer in `releases/vX.Y.Z/`.
- New version, matching source commit/tag; never replace published bytes under an
  existing version. Preserve installer identity and user data.
- Distribution assets: `VideoDownloaderPro_Setup.exe` and `SHA256SUMS.txt`.
  GitHub stable/latest release and digest/update checks follow the publishing
  guide. No credentials belong in the application; no publisher signature is
  currently established by that guide.
- Use targeted isolated tests. Legacy `test_kick.py`, `test_mp4.py` and related
  diagnostics may access external sources/browser sessions at import time; do not
  blindly collect every test as an offline suite.
- New compatibility code needs suitable unit/UI checks, synthetic actual media
  transfer/FFprobe evidence, relevant native/extension checks and packaged tests
  before claiming a production release. Clean Windows VM coverage remains a
  documented gap in historical acceptance.

## Primary local references

- [Development](DEVELOPMENT.md), [release publishing](RELEASE_PUBLISHING.md).
- [Compatibility roadmap](../COMPATIBILITY_ROADMAP.md).
- [Companion setup](../BROWSER_EXTENSION.md).
- [Download improvements](../testing/DOWNLOAD_IMPROVEMENTS_2026-10-30.md).
- [Tracks and merge recovery](../testing/TRACKS_RECOVERY_2026-10-30.md).
- [StreamRecorder verification](../testing/STREAMRECORDER_FULL_VERIFICATION_2026-10-30.md).
- [YouTube investigation and dynamic search](../testing/YOUTUBE_AVAILABILITY_2026-11-01.md).
- [1.3.0 acceptance](../releases/RELEASE_ACCEPTANCE_1.3.0.md).

Live-recording follow-up (2026-11-02): 1.4.1 retains selected audio-only HLS inputs when their codec name is unknown, requires their audio in validation, and fixes live clock/rate display. See [audio fix evidence](../testing/LIVE_AUDIO_AND_RATE_FIX_2026-11-02.md) and [1.4.1 acceptance](../releases/RELEASE_ACCEPTANCE_1.4.1.md).
