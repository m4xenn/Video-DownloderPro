# StreamRecorder full recording availability — 2026-10-30

Page: <https://streamrecorder.io/kick/caglararts>

**Result: the two normally discovered public sources do not expose the complete recording without login.**

The page lists 04:24:50. Both MP4 movie headers report 15,889.928 seconds, consistent with that duration. This is metadata for the original recording, not proof that its full payload is available.

| Source | MP4 declared container extent | Server-exposed bytes | Full-file tail request |
| --- | ---: | ---: | --- |
| 1-mp4 | 6,432,055,465 | 200,000,000 | HTTP 416 |
| 0-mp4 | 2,643,957,116 | 200,000,000 | HTTP 416 |

The declared extents were calculated from top-level MP4 boxes including the extended-size mdat header, without downloading the original files. Initial metadata reads were bounded to 1 MiB per source. Small range samples at the beginning, middle and end of the *exposed 200 MB prefix* succeeded; normal range requests at the original recording tails were rejected. The server reports Content-Range totals of 200,000,000 bytes. These sources are truncated, even though their duration fields describe the full recording.

No login, purchase, alternate private endpoint, source URL modification, license access or key extraction was performed. This result establishes a public-source byte limit, not DRM protection or the availability of an account-based full export. A complete source legitimately offered by the service would need a separate test.

Sanitized machine-readable evidence: [JSON](data/streamrecorder_full_verification_2026-10-30.json). Media URLs, tokens, header values and media bytes are excluded. No application source changes or release were made for this verification.

## Follow-up: normal player investigation

The user confirmed that seeking near the end also stops or errors in their normal browser. The public player script at <https://streamrecorder.io/static/mainpage/js/record-new.js> defines a default preview seek limit of 300 seconds and a "Preview ended" state. Its normal UI directs users to record future streams. This agrees with the server-side 200 MB restriction observed above. The sources and their encrypted URL parameters were left unchanged; no private full-source endpoint was tested.

A source fix now checks MP4 top-level box extents both before postprocessing of embedded files and before final output acceptance. This prevents a readable original duration from disguising a truncated file, and stops a remux from turning the partial source into a misleading short successful download. It reads only box headers, leaves non-MP4 containers to FFprobe, and preserves rejected files. Full download of this StreamRecorder public preview is still unresolved and is not claimed as supported.
