# Compatibility priorities — 1.4.0 baseline and future work

Goal: maximize successful, correct downloads with minimal user intervention. Measure compatibility by discovery + selected audio/video output + recovery, rather than by counting detected URLs. Never advertise universal site support.

## P0 — correct output and reliable failure handling (first milestone implemented)

- Verify that completed embedded files contain the requested stream type before marking a queue item finished. Album artwork does not count as video. Preserve files on validation failure.
- Keep permanent missing-fragment failures fatal, bounded retries and existing partial-file/source identity checks. Do not append a changed source to an unverified partial file.
- Distinguish file-in-use/write-denied and full-disk errors from network/DRM errors. A file-access failure may be a lock or folder permission issue; do not promise automatic recovery or re-download.
- Use default certificate verification. No site compatibility workaround disables TLS validation.

## P1 — HLS compatibility and fewer manual source choices (first milestone implemented)

- Read HLS metadata with a 2 MiB limit, validated manifest header and existing scoped source context.
- Distinguish clear HLS, ordinary AES-128/identity encryption, known DRM key formats and unsupported/unknown encryption. No license/CDM key requests are made by the classifier.
- Preserve explicit media playlist duration when ENDLIST proves VOD; do not invent master/live duration.
- When source evidence supplies multiple typed renditions, preserve video-only/audio-only intermediate formats until final combined format selection. Merge subtitle metadata across sources.
- Automatically choose the sole verified master that connects all observed same-frame HLS candidates. Independent ad streams, multiple roots, cycles and protected roots remain manual or blocked.
- The companion observes encrypted events; an attached MediaKeys object alone is not treated as proof of encrypted playback there. Native WebView2 player API checks remain more conservative and should be unified in a later pass.

## P2 — next compatibility work

1. Implemented in source (2026-10-30): explicit source-declared audio/subtitle language selection for one inspected video, 10 localized controls, strict unavailable-language failure, history/repeat persistence and language-aware duplicate matching. Bulk/playlist downloads retain automatic/all-language defaults.
2. Expand labelled, repeatable site/player acceptance matrices: one metadata check and bounded sample per public page, plus full synthetic multi-track downloads. Separate automatic, human-assisted, site access, protection and transfer outcomes.
3. Improve opaque/blob/player API coverage and extension session continuity, using the normal browser for verification/playback; no CAPTCHA automation or personal profile extraction.
4. Added rotating publisher-provided AES-128 keys, fMP4/byte-range HLS, static DASH and bounded live HLS/DASH capture fixtures. Live HLS 503 retry, exhausted-segment failure, pause preservation and scheduled/manual finish are covered. Longer-running and discontinuity matrices remain future expansion; no universal stream compatibility is claimed.
5. Implemented a bounded in-process final-rename recovery for the exact yt-dlp FFmpegMergerPP permission failure: verify the completed temporary output, retry only rename for up to 8 seconds, continue remaining postprocessors. Persistent restart recovery and other postprocessor failures remain future work. No arbitrary temporary-file promotion or network restart.

## P3 — optional performance and provider integrations

- Stable embedded transfers still default to one fragment. An opt-in measured mode probes 1→2→3 between jobs, excludes overlapping/capped/live measurements and rolls back on errors or no measured gain. The controlled per-connection throttle benchmark measured 1.98× at two fragments; this is not a public-CDN speed promise.
- DRM-protected services require provider-approved licensing/offline integration and supported playback storage. This is separate from exporting a normal MP4. No general Widevine/PlayReady/FairPlay decryption or license bypass is implemented or promised.
- Store-distributed companion installation and signed release acceptance can simplify onboarding once compatibility is stable.

## Release gates

A release needs passing Python/UI/native regression checks; synthetic video+audio+subtitle and AES-128 output inspection; extension master selection; consent/packaging checks for any changed setup components; and representative real-page evidence with limitations reported. Do not label encrypted-but-unknown, 403, expired URL, missing audio or file locks as DRM without evidence.

Protocol references: [RFC 8216](https://www.rfc-editor.org/rfc/inline-errata/rfc8216.html), [W3C EME](https://www.w3.org/TR/encrypted-media/).

## Track selection and recovery follow-up

See [2026-10-30 acceptance evidence](testing/TRACKS_RECOVERY_2026-10-30.md). StreamRecorder profile inspection found a public teaser, not verified full VOD access. Explicit native preview markers now remain labelled through metadata inspection. This does not establish DRM protection or DRM decryption support.

## Seven-part download improvement implementation

The initial implementation of all seven proposed areas is complete in source: bounded preflight, stronger HLS/DASH, strong-validator signed-URL resume, browser continuation, opt-in measured transfer policy, bounded live recording and duration/audio/tail validation. [Acceptance and limits](testing/DOWNLOAD_IMPROVEMENTS_2026-10-30.md). The separate test package passed frozen-app API/assets/native-host checks; it is not a published release or production installation upgrade.

## 1.4.0 release baseline

The milestones above are included in 1.4.0 alongside the Recovery center, durable app closure, single-instance protection, bounded YouTube country-preference search and companion 0.4.1 live language synchronization. Future-work items remain open. See [release notes](releases/RELEASE_NOTES_1.4.0.md) and [release acceptance](releases/RELEASE_ACCEPTANCE_1.4.0.md).
