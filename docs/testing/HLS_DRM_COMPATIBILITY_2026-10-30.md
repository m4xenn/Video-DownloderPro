# HLS / protection first milestone — 2026-10-30

Source changes are unreleased. The installed application and download concurrency settings were not changed.

## Confirmed behavior

- Typed HLS masters preserve separately declared video and audio until final selection. A local synthetic test downloaded and merged a 360p video rendition with an independent audio rendition, then FFprobe verified both streams.
- A master with external audio and WebVTT subtitle playlists produced an MP4 containing video, audio and an embedded subtitle stream.
- A publisher-provided standard AES-128/identity HLS fixture downloaded to readable audio/video and was classified as ordinary HLS encryption, not DRM.
- A Widevine-tagged synthetic manifest stopped after the manifest request, without contacting the supplied license URI or media payload. Unknown/sample encryption without a known DRM system receives a separate unsupported-encryption result.
- Embedded output verification rejects an audio-only file or album-art-only file when video was requested. It preserves files and prevents the completion callback/history success.
- The companion's verified graph selects a single master for three related same-frame HLS observations. An actual isolated Brave + native host + GenericResolver handoff passed without human source selection. Its fixture uses real local HTTP responses because Playwright page routing does not intercept the extension worker's manifest fetches; the earlier route-mocked multi-list test therefore lacked metadata and correctly did not guess.

## Test scope

382 isolated Python tests passed with zero failures/errors/skips, including four real local HLS cases. All JavaScript UI suites passed. Bridge rejection tests were stabilized by consuming bounded request bodies before responding, preventing a Windows TCP-reset race on invalid tokens. Handoff unit fixtures mock media validation because their payload is deliberately not a media file; real output validation is covered independently and by the local download cases.

27 native WebView2 regression checks passed, including selected-quality/full synthetic audio-video downloads and session cleanup. [Sanitized evidence](data/hls_drm_compatibility_2026-10-30.json) records the final results. No new full public-film download or immutable full site-matrix rerun is claimed. The live DRM distinction is based on manifest evidence and EME event signals; actual third-party DRM licenses, CDM internals and protected-content export were not exercised.

## Remaining limits

Bare media playlists do not inherently identify whether their segments are video-only or audio-only; the new split-stream acceptance uses explicit master rendition declarations. Master playlist duration may remain unknown. Stream presence checks are not full frame-by-frame corruption validation. Native WebView2 still uses conservative player DRM hints in some paths. Automatic source selection falls back to user choice when master relationships cannot be fetched/proved. Locked-file diagnostics do not yet provide finalize-only recovery.

See [priorities](../COMPATIBILITY_ROADMAP.md).
