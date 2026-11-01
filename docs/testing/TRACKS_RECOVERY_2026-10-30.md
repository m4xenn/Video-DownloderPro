# Track selection, merge recovery and public-page acceptance

Source changes only; no release or installed production upgrade.

## Implemented

- One inspected, non-playlist video can select source-declared audio and subtitle languages. Automatic audio/all offered subtitles remain defaults. Controls have Turkish, English, German, Spanish, French, Portuguese, Russian, Chinese, Japanese and Hindi labels; language names use Intl.DisplayNames with the exact source code visible.
- Explicit audio selection filters every audio-bearing yt-dlp fallback. An unavailable language fails instead of switching silently. Subtitle availability is rechecked after fresh resolution and source renewal, before media transfer. No generated subtitle translation or automatic-caption promise.
- Track choices persist in queue options and completed history, survive repeat downloads, and distinguish duplicate checks. Old history schemas migrate on writes; old rows default to automatic/all. Bulk/playlist requests reject explicit per-video language choices.
- Existing partial-file identity checks include the selected audio language. A changed language cannot be appended to an old embedded partial file.
- A Windows sharing lock on the exact completed FFmpeg merge temporary file can recover during the same run. Retry only the final rename for up to eight seconds, after verifying readable video/audio; continue the normal remaining postprocessors. Cancellation, existing output, missing audio, unrelated filesystem errors and expired lock waits preserve files and fail safely. No re-download or repeated FFmpeg merge. Restart-time recovery and other postprocessors are not covered.
- Explicit native DOM teaser markers propagate through DOM/network discovery into metadata and a localized preview warning. Unknown scope stays unknown; extension-only observations without this evidence do not claim full-length content.

## Real page: StreamRecorder

User-supplied page: <https://streamrecorder.io/kick/caglararts>

The application discovered two quality sources in a player explicitly marked `alt-teaser-player`. Metadata inspection passed. A bounded direct media sample returned HTTP 206 and 16,384 bytes; it was not saved as a complete video. The updated pipeline reports `content_scope=preview`. Duration was not declared. No full archive download, DRM license access, key extraction, account login or purchase was performed. A public preview working is not evidence of full VOD availability, encryption status, or DRM decryption.

Raw diagnostic artifacts stay under ignored `build/`; no media URL tokens, cookies, header values, local paths or response media bytes are published here.

## Verification

- Full isolated Python gate: 399 tests passed, no failures/errors/skips.
- All JavaScript UI suites passed, including new language selection, subtitle gating, locale switching, bulk reset and changed-URL cases.
- Real local FFmpeg/HLS acceptance: split video/audio, external audio and WebVTT, selected Turkish audio with English subtitles, ordinary publisher-provided AES-128, protected-manifest early stop, and Windows-locked merge recovery passed. The lock test asserts FFmpeg merge executes once and FFprobe confirms final audio/video.
- Legacy SQLite migration and language-specific duplicates passed.
- Native WebView2 regression: 27 checks passed, including player discovery, selected/max HLS audio-video downloads, browser handoff and helper cleanup.

Ordinary HLS AES-128 support already exists. General Widevine/PlayReady/FairPlay decryption has not been added. Provider-approved licensing/offline integrations need a provider contract/API and are separate from normal MP4 export.

## Follow-up: full recording availability

[Bounded full-recording verification](STREAMRECORDER_FULL_VERIFICATION_2026-10-30.md) established that both exposed sources stop at 200,000,000 bytes, while their MP4 containers describe approximately 6.43 GB and 2.64 GB recordings. Duration metadata matches the listed 04:24:50, but requests for the original file tails return HTTP 416. Public partial sampling must not be reported as full recording success.
