# Embedded source follow-up — 2026-10-22

The user confirmed that Aniwaves and Hianime both play in their normal browser. They must not be classified as dead sites merely because the isolated helper cannot initialize them.

## Implemented changes

- Parse explicit subtitle, alternate-video and trick-play HLS playlist relationships in addition to video/audio variants. Auxiliary playlists no longer create false competing-video ambiguity. This follows [RFC 8216, section 4.3.4](https://www.rfc-editor.org/rfc/rfc8216.html#section-4.3.4).
- Retry an already resolved public media URL once with yt-dlp's available Chrome-compatible HTTP transport after a 403 response. Keep the existing scoped cookie jar and headers. No login, DRM or verification bypass is attempted. Pin curl_cffi and include its native dependencies in the packaging specification; a new installer has not been built or verified.
- Recognize localized verification titles so the Turkish Cloudflare page offers the normal browser interaction flow instead of an unsupported-source error.
- Activate a single visible, centrally placed, explicitly labelled play poster only when it belongs to a bounded player region containing one empty iframe. Ambiguous controls, adverts, forms, verification and DRM remain excluded.
- Retain native iframe navigation redirect evidence. A DOM iframe may refer to the original URL while its actual document is redirected to a different player origin. Accept this relationship only if the native chain ends at the observed document, retaining the original parent and visible-area bounds. Stale or unrelated navigation evidence is rejected.
- Add bounded network diagnostics recording host/status or Chromium error code only. Cookies, headers, media URLs and response bodies are not persisted in reports.

## Outcome

Follow-up per-link results: **7 automatic, 2 interaction required, 4 unresolved**, compared with the previous 5/3/5 result. The automatic cases are FullHD Ballerina, 9anime, AniwatchTV, Yomi, Animexe, Hianime and Freeflix. Interaction cases are HDFilmCehennemi and Aniwaves.

This is a sequential diagnostic round: the redirect fix was added during the batch, and Hianime was also independently checked in the final actual application flow. It is not presented as one immutable-source benchmark. See [sanitized per-link evidence](data/user_embedded_2026-10-22_followup_app.json).

## Confirmed improvements

**Yomi / Attack on Titan:** source selection, actual application metadata and a 16 KiB HLS segment sample passed; 1080p, duration 1556 seconds. Explicit auxiliary playlist relationships fix selection; the compatible HTTP retry fixes the subsequent media 403.

**Hianime / Arcane:** automatic source resolution and actual application metadata passed; 360p/720p, duration 2605 seconds. A 16 KiB HLS segment sample passed with HTTP 206. The poster and native redirect fixes resolve this case without user verification in the successful run.

**HDFilmCehennemi:** now correctly classified as interaction required on the localized verification page. This is an error/continuation improvement, not proof of successful download.

## Remaining cases

- **Aniwaves:** its isolated visible helper loads Cloudflare Turnstile frames titled “Checking your Browser” and receives challenge-related failures. No media player becomes available. The user's normal browser plays the episode; completion of normal verification in the helper remains unverified. No automatic challenge solving is implemented.
- **Dizipal:** the hidden page has no initialized media player; a visible follow-up exposes an Oynat control but still does not establish a downloadable source.
- **FilmMakinesi:** the browser loads the Matrix page but only advertising/player placeholder regions are observed. Plain HTTP separately encounters Cloudflare; that alone does not establish the browser failure's cause.
- **AnimeVillage:** no player on the exact supplied URL; separately trying a normal ?ep=1279 query also failed. The supplied URL is not silently rewritten.
- **Hotsflix:** episode page loads, but observed iframe is a small advertising region and no actual media player/source is established. The “Download in HD” advertising button is not treated as a player.

## Validation and limits

325 isolated Python tests passed, including a real local HLS retry test requiring the correct cookie and asserting no cookie is sent outside its path/host scope. All JavaScript UI suites passed. 21 native WebView2 checks passed, including actual synthetic audio/video downloads and the redirected iframe case. One earlier run stopped at the related-manifest fixture because browser response evidence was missing; an unchanged-code repeat passed. This timing sensitivity remains an open concern. See [validation and new media samples](data/user_embedded_2026-10-22_followup_checks.json).

Only small explicit public-media samples were read; browser playback may buffer additional media. Full public film/episode downloads, long-running token expiry and the packaged transport are unverified. The changes remain unreleased; published 1.3.0 is unchanged.
