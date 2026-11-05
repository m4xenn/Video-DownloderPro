# Link security hardening — unpublished 1.4.3

The user requested transparent protection against malicious links while retaining ordinary media support. This change adds boundaries around the local API, remote inspection browser, HTTP transfers, cover images and live recording. It adds no website reputation subscription, domain blacklist, credential collection or recurring confirmation dialogs.

## Implemented boundaries

- All local Flask routes reject foreign/null origins, foreign referrers, cross-site/same-site browser requests and unexpected Host names. This covers previously unguarded settings, folder, queue and language routes. Native header-less clients remain supported; this is a browser-origin boundary, not authentication against other programs already running as the same Windows user. JSON payloads are bounded to 2 MiB.
- The local UI has anti-framing, MIME-sniffing, permissions and content policies. Remote scripts/frames/objects cannot load into it. The native main window cannot navigate away from its original local origin. Inline handlers remain necessary for the current application UI; this is not a strict nonce-based CSP.
- Input links reject unsafe schemes, embedded credentials, control characters, malformed ports, private/local addresses, numeric IP aliases, multicast/reserved addresses and local hostnames. User-facing protection messages are translated in all ten UI languages.
- yt-dlp Requests/CurlCFFI handlers validate redirects and pin actual connections to checked public IP addresses while retaining the original TLS hostname. Curl canonicalizes international hostnames before both DNS pinning and the request. The guard survives request-director rebuilds and browser-compatible retry. Unprotected alternative transports are not selected. TLS verification remains enabled.
- Source WebView2 windows install navigation/resource guards before the first remote navigation. They deny device/notification/clipboard permissions, automatic downloads, external protocols, native script dialogs, host objects and saved passwords/autofill. The existing pywebview popup delegate was removed because it launched the external browser before later popup handlers ran. The source hostname appears in the window title. Initialization failure closes the helper window rather than loading unprotected content.
- Source browser resource DNS checks use asynchronous deferrals, keeping DNS off the UI thread. Popups, known private endpoints and resources resolving to private addresses are blocked, including child-frame/worker resource events. This retains the browser runtime's own sandbox and permission boundaries; it is not an independent OS process/network sandbox.
- Remote thumbnails are replaced by local identifiers before reaching the UI. The image fetch uses the pinned HTTP client; byte/pixel/time limits apply and valid covers are reencoded as small JPEGs. SVG/HTML and unknown identifiers do not become executable or arbitrary URL-fetching resources. Cache/registration sizes are bounded.
- Non-DVR live inputs now pass through a token-scoped streaming gateway. HLS playlists, keys, nested playlists and DASH BaseURL/template/init URLs are rewritten; opaque HLS/XML responses are inspected as well. Segments, keys and redirects use pooled pinned HTTP sessions. Only exact manifest URLs created by the application's own router receive a local-network capability. Browser requests cannot use the gateway. Sixteen-byte inline AES keys remain supported.
- From-start YouTube DVR and live manifest probes also use pinned sessions. Remote FFmpeg inputs are limited to the HTTP/TLS/media-decryption protocols needed by recording; local conversion/merge remains available. A blocked live reference stops safely and preserves partial work.
- Completed files receive Windows' Internet-zone marker when the destination filesystem supports alternate streams. No signed source URL is written into the marker. This preserves OS protections without changing the media bytes; it does not claim an antivirus scan was performed.

## Validation

- **542 Python tests passed**, zero failures/errors (`build/security-regression/result.json`). One subsequent international-hostname regression case also passes in the seven focused transport/gateway tests.
- All **27 JavaScript test files** pass. Rendered ten-language settings/dynamic errors/persistence pass without page errors.
- Synthetic attack tests cover private IP aliases, credentials/schemes/control characters, mixed public/private DNS answers, cross-origin mutations, DNS-rebinding Host names, native device/download/protocol hooks, thumbnail conversion/limits, redirected media and opaque malicious HLS. A real canary server confirms the private target was never requested.
- Real WebView2: private requests and popups blocked; a normal public HTTPS page loads and host-side evaluation still works (`build/security-native-browser/result.json`).
- Real FFmpeg integration covers HLS and dynamic DASH video/audio, backlog catch-up, graceful finish, recovery, encryption/subtitles in existing VOD flows, source renewal and failures. The catch-up fixture downloads 20 seconds of history in under 3 seconds and then appends live AV content. The gateway's initial DASH namespace/probe incompatibility was fixed and regression-tested.
- Actual frozen EXE: public W3Schools MP4 inspection succeeds, unsafe links/foreign origins are rejected, the main UI remains running, French warning language and settings survive restart (`build/security-native/result.json`). Thirteen compiled runtime/security modules and eight interface assets match the final source (`build/security-payload-verification.json`).

Current preview: `build/security-package/YoutubePro/YoutubePro.exe`, with its accompanying `_internal` directory.
Executable SHA-256: `c1ad0ba9254449876c6337783fcc7b67abdd3f197e954be92c0a161e4d6f6744`.

No release or personal-profile upgrade was performed. The older installer in `releases/v1.4.3` predates this work and must be rebuilt and accepted before publishing. Media parser/runtime security still depends on maintained WebView2, yt-dlp, FFmpeg and image libraries. These checks do not certify every remote source or constitute a third-party penetration test.

## Primary references consulted

- [pywebview local API security](https://pywebview.flowrl.com/guide/security)
- [Microsoft WebView2 security guidance](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/security)
