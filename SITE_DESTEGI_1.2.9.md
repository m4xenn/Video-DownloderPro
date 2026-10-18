# 1.2.9 — FullHDFilmizlesene / Rapidvid site support

## Scope
Initial site-specific support is restricted to HTTPS film pages on fullhdfilmizlesene.now and its www hostname, using Rapidvid /vod/ players. Other domains keep their existing yt-dlp flow. Site/domain changes and other player providers may require adapter updates.

The app first tries a bounded HTTP page read. If it cannot locate the expected player, it creates a hidden pywebview window only on demand. It reads the page DOM to find the iframe, closes the helper when found, and resolves the known player configuration without evaluating fetched JavaScript. It does not import browser profiles or export browser cookies. Verification is completed by the user if needed: Continue in browser, then Check again. A session expires after three minutes; closing the main app also closes the helper.

Only the original page URL is stored in the queue/history. Temporary source URLs remain in a bounded memory cache for two minutes. Source extraction runs again when the download starts; it can reuse a recent known player address to avoid opening the main page again. Supported quality choices are supplied by the existing metadata/quality flow. Raw download URLs are not accepted from the frontend.

## Verification
- 168 offline Python tests passed (including 18 adapter/browser-lifecycle cases).
- 76 JavaScript UI checks passed, including five new interaction checks.
- A real two-second local HLS fixture passed through the site adapter and queue: requested 180p output was verified with FFprobe and contained audio.
- Existing local MP4/MP3 download and bandwidth/pause tests were run again.
- The supplied live page was tested through a real hidden Windows WebView2 helper. Title, duration and 360/480/720/1080/2160p choices appeared without opening a visible helper window.
- The first 16 KB of a live 360p segment returned HTTP 206. The full film was not downloaded.
- Real CAPTCHA completion was not tested; show/cancel UI and same-origin protections are covered by isolated tests.

## User test
Install the unpublished 1.2.9 test package. Paste the supplied fullhdfilmizlesene.now film URL and wait for inspection. Check title and quality choices before adding to the queue. Choose a quality and download. If verification is required, use Continue in browser, complete it yourself, return to the app and click Check again. Changing the input or choosing Cancel dismisses a pending interaction.

This is an initial site adapter, not universal website support. DRM-protected/unavailable sources are not supported. The site's default audio selection is used; a separate audio-language selector is not part of this change.
