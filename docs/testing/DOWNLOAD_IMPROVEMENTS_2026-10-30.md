# Download improvements — 2026-10-30

All seven proposed areas have an initial tested implementation. This is an unreleased development build; installed production v1.3.0 was not replaced. The companion source is version 0.4.0, with its existing stable public identity.

| Area | Implemented behavior | Evidence |
| --- | --- | --- |
| Source preflight | Bounded MP4 box/header reads compare declared extent with exposed bytes; explicit preview and unknown access remain distinct from a checked container. Known truncated sources stop before full transfer. | StreamRecorder returned `partial`: 200,000,000 exposed bytes versus 6,432,055,465 declared bytes, before media download. |
| HLS/DASH | Typed protection checks, HLS rendition inspection, rotating publisher AES-128 keys, separate audio/video/subtitles, fMP4 byte ranges, static DASH and dynamic live DASH capture. | Real synthetic downloads and FFmpeg/FFprobe output checks. Protection classifiers never request a license. |
| Recovery | Existing same-source resume remains. A changed signed query can resume only with the same inspected strong ETag, resource identity, byte length, media identity and selected tracks. Content query parameters are retained; only known signature/expiry fields are excluded from the identity hash. | Real Range resume produced byte-identical output; a changed validator preserved the partial file without transferring media. |
| Browser flow | App action focuses its pending extension-owned tab; successful playback hands the source back. Concurrent inspections of one page share a job. Live playback and DASH observations are supported; explicit preview scope is preserved. | Isolated Brave/native-host handoff, focus-counter/tab-isolation tests and a real rendered app continuation flow. |
| Transfer speed | Stable remains default. Opt-in measured mode probes at most three fragments between completed jobs; rolls back without at least 10% gain or on errors, with a ten-minute cooldown. Short, overlapping, rate-capped and live observations do not authorize a probe. | Controlled per-connection throttle: 15.906 s with one fragment, 8.032 s with two; both 2,686,619-byte outputs passed media validation. This is not a prediction for a public CDN. |
| Live capture | Explicit single-source MP4 recording, 1–1440 minute limit, optional stop time within 24 hours, finish-and-save action, bounded reconnect and HLS same-segment retries. Recoverable MKV is retained until MP4 publication succeeds. | Real live HLS and dynamically produced DASH tests. Manual/scheduled finish, pause preservation, successful 503 retry and exhausted retry rejection passed. |
| Completion validation | Original MP4 extents are checked before remuxing; final checks cover expected audio/video, duration consistency, tail packets and a short tail decode when FFmpeg is available. | Truncated originals, remuxed short previews, missing expected audio and unreadable tails are rejected. |

## User experience

- New controls use ten application languages. The live recording guide has ten screenshots captured from the real rendered controls.
- The live form offers duration and stop time, with details explaining restart behavior and limits. Live subtitles are disabled rather than silently ignored.
- A recording can be finished from its queue row. Pausing preserves the temporary recording; restarting creates a new file and does not append a later live window to an old capture.
- Settings distinguish stable transfer from measured acceleration. The outer window remains fixed; smaller windows scroll the content rather than hiding the action.
- A browser continuation button appears only while extension inspection is pending and disappears when the source returns. It cannot focus arbitrary user tabs.

## Verification

- Python regression gate: **438 passed**, zero failures/errors/skips. A subsequently added dynamic live DASH test also passed against the same application source.
- All JavaScript UI suites passed.
- Native WebView2 acceptance: **27 checks passed**.
- Isolated Brave: current extension/native-host connection and automatic blob/HLS handoff passed; no personal browser profile used.
- Rendered app acceptance passed: ten locales, live payload, preserved language choice, stable shell on view changes, small viewport action access, transfer preference save, partial-source rejection, browser continuation and finish-recording action. No page script errors.
- PyInstaller test package built successfully. Frozen-app smoke checks passed: new APIs/assets/defaults, ten live guide images, no setup writes without consent, and real bundled native-host stdio exchange. No permanent registration or installed production change was made.

## Limits

Container checks are not a promise that every byte has been decoded or that an unknown source is complete. Servers without reliable Range responses/validators remain unknown. Changed HLS fragment URLs do not gain arbitrary unsafe resume permission.

Live capture records the currently available live window, not unavailable earlier content. Interruptions can leave gaps: detected exhausted HLS segment retries stop the recording and preserve any captured data rather than publishing a success. Live subtitles and audio-only live export are not included. Live FFmpeg transport does not support the application's shared bandwidth cap, so an active cap is rejected explicitly. Long-running broadcasts and every vendor-specific DASH error behavior have not been certified.

StreamRecorder's public preview is still limited; no full archive access or DRM decryption is claimed. Source URLs, cookies, token values, header values and media payloads are omitted from published evidence.

Machine-readable evidence: [download_improvements_2026-10-30.json](data/download_improvements_2026-10-30.json).
