# User-supplied embedded-video acceptance — 2026-10-22

## Result

13 exact user-supplied public URLs were tested through the real application `/get-info` flow with isolated profiles. The baseline uses an immutable local snapshot of the released 1.3.0 sources; final sources were tested in two isolated sequential batches with the same source fingerprint.

Before: **4 automatic, 4 interaction required, 5 failed**. After: **5 automatic, 3 interaction required, 5 failed**.

Five positive cases also passed an explicit 16 KiB media sample check using the generic resolver. No film or episode was downloaded in full. Browser startup can buffer additional media; 16 KiB is the explicit diagnostic-read cap, not a total traffic cap. Metadata/sample success does not establish complete-download reliability or guarantee correct selection on every visit.

## Per-link comparison

| User link | Before | After | Media sample | Findings |
|---|---|---|---|---|
| [hdfilm-batman](https://www.hdfilmcehennemi.nl/batman-kara-sovalye-yukseliyor-hd-film-izle-hdf-hdf-5/) | failed | failed | not_tested | Plain HTTP returns 403 / Just a moment; app still cannot resolve. No verification bypass attempted. |
| [fullhd-ballerina](https://www.fullhdfilmizlesene.now/film/john-wick-dunyasindan-ballerina/) | automatic | automatic | passed | Metadata duration 7470 s; 266p–800p; bounded media sample passed. Plain HTTP separately returns 404, so it is not representative of the full browser/adapter flow. |
| [dizipal-twd](https://dizipal1591.com/bolum/the-walking-dead-1x1-c31) | failed | failed | not_tested | Native follow-up: page loaded, no visible player/media request, only a zero-size empty iframe. Cause of absent player is not established. |
| [aniwaves-bleach](https://aniwaves.ru/watch/bleach-80678/ep-1) | interaction_required | interaction_required | not_tested | Native follow-up: page loaded, no media/player/iframe evidence; interaction path. Visible server/play selection not tested. |
| [9anime-cyberpunk](https://9anime.si/watch/cyberpunk-edgerunners-episode-1) | automatic | automatic | passed | Metadata duration 1444 s; 1080p; bounded media sample passed. |
| [aniwatchtv-solo](https://aniwatchtv.ro/solo-leveling-episode-1/) | automatic | automatic | passed | Metadata duration 1420 s; 360p/1080p; bounded media sample passed. |
| [filmmakinesi-matrix](https://filmmakinesi.to/film/matrix-izle-1999-fm3/) | failed | failed | not_tested | Plain HTTP returns 403 / Just a moment; app still cannot resolve. No verification bypass attempted. |
| [yomi-aot](https://yomi.to/watch/attack-on-titan-16498/1) | interaction_required | interaction_required | not_tested | One blob player and three HLS responses; one verified variant edge. Remaining network ambiguity is not automatically merged. Visible Continue flow not tested. |
| [animevillage-demon](https://www.animevillage.org/watch/101922/demon-slayer-kimetsu-no-yaiba-rzepv-1551%3Fep%3D1279) | failed | failed | not_tested | Source not resolved. A separate trial replacing encoded %3Fep%3D1279 with ?ep=1279 also failed; the supplied URL was not silently rewritten. |
| [hotsflix-breaking](https://hotsflix.net/serie/breaking-bad_B1396_1_1/) | failed | failed | not_tested | Source not resolved; root cause not yet established. |
| [animexe-blue-lock](https://animexe.com/watch/blue-lock/1/2) | automatic | automatic | passed | Metadata succeeds without a reported duration/quality list; bounded media sample passed. Complete media properties remain unverified. |
| [hianime-arcane](https://hianime.ms/watch-arcane-episode-1-36d59) | interaction_required | interaction_required | not_tested | Interaction-required outcome; visible Continue flow not tested. |
| [freeflix-episode](https://freeflix.live/watch/?id=94664&type=tv&season=1&episode=1) | interaction_required | automatic | passed | Improved from interaction required to automatic. 360p/720p/1080p, duration 1427 s. New-source repeat and bounded media sample passed; unchanged 1.3.0 repeat still required interaction. |

## Implemented common fixes

- Explicit HLS master/rendition relationships are parsed instead of guessing that multiple network URLs belong together. Only already observed successful HLS responses participate; independent candidates and cycles remain ambiguous.
- WebView2 reads a small, already received HLS response through its existing in-process protocol API. Original response content preserves signed/short-lived variant URLs without requiring a fresh HTTP manifest response.
- Response-body collection is limited to six small manifests per helper session; parsing is capped at 96 KiB per manifest. No manifest bodies or credentials are persisted.
- A bounded fallback reads only exact observed public URLs, refuses redirects, and excludes Authorization headers. Relationship evidence is retained for variants observed later. Recreating the visible helper discards old evidence.
- Player evidence, document context, competing-player/ad checks, DRM and verification checks remain in force. No CAPTCHA solving, browser security disabling or site-specific film-ID matching was introduced.

## Validation

- 315 isolated Python tests passed with no failures, errors or skips.
- 19 native WebView2 end-to-end checks passed: cross-origin nested frames, player activation, quality extraction, related manifests, actual synthetic HLS audio/video downloads, browser/session handoff and cleanup.
- The related-manifest native case passed with additional HTTP manifest enrichment disabled, establishing that the browser-response path works.
- Official hls.js demo changed from interaction required to automatic network discovery: 184p, 288p, 480p, 720p, 1080p and a 16 KiB sample.
- Freeflix was repeated: released-source snapshot still required interaction; modified source returned metadata repeatedly and passed its bounded sample.
- The five unresolved sources and three interaction-required pages remain open issues. No visible verification/server-selection completion, long-download token-expiry test, production installer build or release was performed.

## Next work

1. Trace the three interaction pages through an explicit visible Continue/server-selection flow. Distinguish uninitialized player gates from independent or unrelated sources.
2. Reproduce the absent-player cases on Dizipal, Animevillage and Hotsflix and identify the player loading/API failure before adding any host-specific rule.
3. Keep Cloudflare/access cases separate; require normal user verification where the site requests it.
4. Once source selection is reliable, use permitted long-form test media for completion, seek, pause/resume and token-expiry checks.

Changes are in source only; the published 1.3.0 installer is unchanged.

## Evidence

- [Baseline application results](data/user_embedded_2026-10-22_before_app.json)
- [Final application results](data/user_embedded_2026-10-22_after_app.json)
- [Final positive media samples](data/user_embedded_2026-10-22_samples.json)
- [Unit/native verification summary](data/user_embedded_2026-10-22_checks.json)
