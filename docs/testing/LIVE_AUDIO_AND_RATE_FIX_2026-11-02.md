# Live recording audio and rate fix — 2026-11-02

Correction included in 1.4.1 after the published 1.4.0 release. No existing
published installer was replaced and the original recording was not modified.

## Reproduction and cause

Read-only inspection of the reported completed recording found H.264 video and
no audio stream. Its persisted selected formats contained a video-only HLS input
and a separate audio-only HLS input with `vcodec=none` and `acodec=null`.

The custom live FFmpeg mapper treated a missing audio codec name as proof that
audio was absent. It skipped the selected audio input and optionally mapped audio
from the video-only input. Output validation also did not require audio in that
case, so a silent result could be marked complete.

## Changes

- Treat an explicitly audio-only selected rendition with an unknown audio codec
  as audio, require it in FFmpeg mapping and require audio in final validation.
- When multiplexed audio metadata is unknown, do not silently accept missing
  audio. Explicitly declared video-only sources retain their optional audio map.
- Prefer a known video input before unknown-codec candidates.
- Calculate an approximate live output-byte rate from recent FFmpeg progress,
  propagate it through the queue and include active live capture in the total
  speed display. Native download byte counts remain separate.
- Show live duration as HH:MM:SS and label real-time capture in all ten languages.
  Explain that the displayed recording bitrate is not the internet line limit.
- Preserve live duration/speed through the general localization pass, which
  previously overwrote the live duration with ordinary VOD size/ETA text.

## Verification

- **476 isolated Python tests passed**, zero failures/errors/skips.
- All **27 JavaScript UI suites passed**.
- Eight real local live tests passed, including unknown-codec split HLS with
  audible waveform, missing selected audio rejecting publication, dynamic DASH,
  scheduled/manual finish, pause preservation and segment retry behavior.
- The reported public live source was captured briefly with the actual selected
  metadata shape. The new MP4 contained H.264 video and AAC audio: 24.984 seconds,
  2,058,956 bytes. Audio decoding measured mean -25.1 dB and peak 0 dB, confirming
  it was not an empty/silent audio track. Wall time was 17.19 seconds, including
  available buffered live segments and finalization. This is not a full-broadcast
  or arbitrary-provider performance test.
- Rendered acceptance passed ten languages and asserts that localization retains
  the live clock/rate. No page errors. The separate frozen test build opened with
  an isolated profile and passed bundled-assets/native-bridge checks.

Private raw source URLs, headers, original user paths and media are omitted here.
Evidence remains under ignored `build/live-audio-fix-regression/`,
`build/live-audio-real-check/` and `build/live-audio-fix-package-runtime/`.

## Using the correction

Update the application to 1.4.1 to receive the correction. The earlier unpacked
development evidence remains under `build/live-audio-fix-package/`; it is not an
installer or a replacement for the versioned release asset.

Future live content is generated in real time; increasing the connection speed
cannot fetch it before the broadcaster sends it. Available buffered/archive
content is a separate case. An old file containing no audio stream cannot regain
that missing audio by changing player volume or remuxing alone; matching source
audio would have to be fetched again.
