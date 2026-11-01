# Remaining embedded sources — 2026-10-22

The user's corrected confirmation is that **both Dizipal and FilmMakinesi play in their normal Chrome/Edge browser**. These are not classified as unavailable sites.

## Verified improvements

| Source | Current evidence | Limitation |
|---|---|---|
| Hotsflix | Original supplied URL now automatically follows its single same-title, same-origin, same-path cover link into the query-based watch state. Actual application metadata and a 16 KiB direct media sample passed (HTTP 206). | Source duration and full episode contents are not established by the small sample. |
| FilmMakinesi | The unlabelled visual poster is correctly activated. Actual application metadata and a 16 KiB HLS segment sample passed (HTTP 206): Matrix, 8177 seconds, 800p. | Full download/token expiry not tested. |
| AnimeVillage | Hidden Next.js application defers initialization; the normal visible Continue flow now succeeds on the exact supplied encoded URL: 1419 seconds, 1080p, 16 KiB HLS segment passed (HTTP 206). | User-assisted continuation, not an automatic hidden-window success. |
| Aniwaves | After the user completed verification and played Bleach, the diagnostic identified an Artplayer instance with a blob video and no classifiable network responses. New Artplayer API support resolves that same observed public player: 1384 seconds, 720p, 16 KiB HLS sample passed. | The reopened parent-page test passed after user verification/playback: 720p, 1384 seconds and a 16 KiB HLS sample (HTTP 200). This is user-assisted acceptance, not automatic verification. |
| Dizipal | User-assisted playback on the supplied parent page resolved the actual Playerjs episode and 1080p metadata. A follow-up using the same public player configuration and production resolver passed a 16 KiB HLS segment read (HTTP 206) after the browser-compatible 403 retry. | Two-phase discovery/transfer evidence; no final single-run parent-to-sample acceptance or full episode download is claimed. |
| HDFilmCehennemi | Visible verification was attempted in WebView2 and isolated normal Microsoft Edge. | The user could not complete verification in either test session; no source was established. Remains unresolved, despite confirmed playback in the normal user browser. |

## Implementation

- Read a unique same-title image cover link only when it opens a query state of the exact same public page. Reject other origins, paths, credentials, hidden/tiny covers, trailers, download labels, sponsored links and multiple competing targets. The Python traversal validates the boundary again and retains the real parent. Existing depth/document/time budgets remain in force.
- Detect a visual image + SVG play poster matched to the page heading, with pointer cursor and a single explicit lazy iframe in its bounded parent. Anchors/forms/advertising regions, already-loaded frames, CAPTCHA targets and ambiguous layouts are excluded. The normal page click handler initializes the iframe; no site-specific film IDs are hard-coded.
- A hidden Next.js app that has not yielded media now offers the existing visible Continue flow, rather than an unsupported-player error.
- Read public Artplayer instances and original configured URLs/qualities, with container visibility and DRM/mediaKeys checks. This restores the original source when HTML5 only exposes a blob URL. API references: [static instances](https://artplayer.org/document/en/advanced/class), [source and quality options](https://artplayer.org/document/en/start/option). No page scripts are downloaded and evaluated by Python.

## Validation

337 isolated Python tests passed (zero failures/errors/skips). All UI suites passed, including 17 cover-navigation checks, 15 visual-poster checks seven Artplayer source checks, eight advertising exclusion/wait checks and eight Playerjs checks. 27 native WebView2 checks passed using synthetic local media, including real audio/video downloads, query watch-state navigation, visual posters, Artplayer and Playerjs source extraction, opaque HLS response proof, preroll handling, iframe redirects and session cleanup. A separate full synthetic HLS audio/video download passed after a first-fragment 403 and browser-compatible retry. An earlier native network-related body-capture check intermittently failed; unchanged repeat runs, including the final 27-check run, passed.

[Sanitized test evidence](data/remaining_embedded_2026-10-22_checks.json) separates actual application results from player-only and human-assisted media checks. The four-case application batch predates the final Artplayer API addition; it is not an immutable final thirteen-case benchmark.

No public film/episode was downloaded in full. No CAPTCHA solving, login or DRM bypass, browser-security disabling, production profile access, installer build or release was performed. Source changes are unreleased.

## Later human-assisted acceptance

The user started playback in both reopened windows. Aniwaves then completed the entire supplied-parent-URL metadata/sample flow successfully.

Dizipal initially selected a **14-second advertising video**, which strict metadata validation correctly rejected. The fix excludes explicitly labelled advertising regions (including the page's “Reklam” region) from DOM/API player discovery, lazy-gate activation, iframe traversal and automatic playback. Source validation was not weakened and image-like responses were not relabelled as video. The subsequent human-assisted parent-page run resolved the actual episode via documented Playerjs HLS getters. Its first sample encountered HTTP 403. Replaying the same public player configuration through the production resolver confirmed that the one-time Chrome-compatible transfer retry reads the segment successfully. The retry preserves the selected format and scoped cookie jar and is refused once partial media exists. HLS classification requires parsed player HLS state or a bounded response body beginning with #EXTM3U; image responses alone are never promoted. Playerjs API reference: https://playerjs.com/docs/en=apicommands .
