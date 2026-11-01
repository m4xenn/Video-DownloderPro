# YouTube availability investigation — 2026-11-01

**Final result: resolved for the supplied video using a scoped Germany player API context, without a remote relay. Earlier infrastructure conclusions below are superseded by the follow-up verification.**

URL: https://www.youtube.com/watch?v=_hJNUVZPRuc&t=4s

## Reproduction

- Bundled/development yt-dlp 2026.08.19: `Video unavailable` with default clients, and also with the web client and Node enabled.
- Isolated yt-dlp 2026.10.26 + yt-dlp-ejs 0.8.0 + Node 24.22.1: `Video unavailable. This content is not available on this country domain due to a legal complaint from the government.`
- Both tests used the same machine/network without personal cookies. No media downloaded.
- The timestamp parameter was accepted; extraction failed on platform availability before media selection.
- Existing diagnostics classified this as `unexpected`. The old engine does not expose the detailed restriction reason on this request.

## Change and validation

Classify platform availability and explicit regional/legal restrictions separately, expose fixed safe messages in metadata responses and queue labels, and avoid asserting a regional reason when the engine only says unavailable.

11 diagnostics tests passed, including endpoint classification and secret redaction. JavaScript syntax check passed.

The production installation and engine were not modified. The latest engine was installed only into build/youtube-engine-probe for comparison. No release was built or published. Updating the engine provides a clearer reason but did not restore access on this network. This change improves error reporting; it does not remove the platform restriction.

## Public solution follow-up

All six explicitly selected clients (web, web_embedded, android_vr, tv, mweb, ios) returned the same country-domain legal restriction. Three additional attempts (US page locale, yt-dlp US geo-bypass setting, English web client with US forwarded-IP header) also failed. These are metadata-only probes; no playable formats were obtained. Results: build/probe_youtube_clients.json and build/probe_youtube_region.json.

A per-user VPN requirement does not meet the product requirement. No existing relay/proxy hosting or deployment configuration was found in src, scripts, or docs. A general fallback requires a maintained remote network exit where the specific content is available, followed by a real extraction and download test from that exit. Availability from a different country remains unverified.

Proposed product flow: local extraction first; offer remote processing only after an explicit regional restriction and user opt-in; the service resolves and transfers media through the same exit; return an expiring download job to the desktop app. Do not forward signed source URLs for local downloading without testing IP binding. Never send browser cookies or account credentials to the relay. Use authenticated jobs, bounded quotas, cancellation, short retention, and fixed YouTube host allowlists to avoid creating a public open proxy. A remote processing notice must explain that the video URL is sent to the service. No automatic uploads or routing were added.

Deployment depends on an operator-controlled host, region, credentials and operating budget. There is no shared endpoint in the repository. No per-user proxy UI was added, and no public download guarantee can be established with the current network alone.

## Germany player context: successful local solution

The user's browser observation led to a different test: set `client.gl=DE` in the actual InnerTube player request context. This differs from changing the page query, preference cookie, language or forwarded-IP header.

- Germany page query + preference cookie alone: failed.
- Germany player API context: 49 formats with isolated yt-dlp 2026.10.26; 48 formats with the application's existing yt-dlp 2026.08.19.
- Real 5-second video+audio sample downloaded using the latest engine.
- Real 5-second sample also downloaded using the application's existing engine and the new automatic fallback helper. Initial normal extraction failed, then automatic Germany-context extraction and media transfer succeeded on the same local network.
- FFprobe: AV1 video, Opus audio, 5.021 seconds, 87,463 bytes.
- No VPN, proxy, GoodbyeDPI, personal browser cookies, account login or remote relay used.

Implementation: services/youtube_region.py first attempts normal extraction. On a YouTube country-domain/legal-complaint/unavailable response, retry exactly once with an instance-scoped YoutubeIE subclass that deep-copies the player context and sets Germany as its locale. Restore the original extractor and ignoreerrors option even if retry fails. Integrated into the shared metadata/download resolver, playlist previews, and queue playlist expansion. No global monkey patch or system networking change.

Validation: 5 new fallback tests, 11 diagnostics tests, 25 site resolver tests, 28 library tests and 8 source-quality tests passed (77 total). Tests cover bounded retries, no retry on unrelated hosts/errors, context copy, restoration on failure, and independence of other engine instances.

Limits: real transfer verification used a short sample, not the full video. This is a verified fix for the supplied video on the current network, not a guarantee for all geographical restrictions. Packaged/installed executable not rebuilt or updated in this task. The existing engine works for this sample; this fix does not complete broader JS-runtime packaging work.

## Bounded dynamic country discovery

Replaced the fixed Germany retry with a sequential search across DE, US, GB, NL, FR and CA. Normal extraction remains first. Search starts only on an availability/country error, and stops at the first result containing a playable, non-DRM media format (not just a title or storyboard). Invalid/empty results are skipped. Authentication/removal/copyright failures, network failures and HTTP 403/429 do not trigger more country attempts. Country changes are scoped to the current engine and restored on exit.

The search checks cancellation and a 45-second budget between extractor calls. Fallback uses an at-most-8-second socket timeout and disables extractor retries, restoring prior options afterwards. The time budget does not forcibly interrupt in-flight yt-dlp calls or all internal requests, so actual elapsed time can exceed it. Country discovery uses metadata only; requested transfer begins after discovery. UI shows a country-search progress message.

Validation: 12 dynamic-country tests, 25 site resolver tests, 28 library tests and 16 source handoff tests passed (81 tests). Tests include later-country success, invalid/DRM/storyboard rejection, exhaustion, time budget, cancellation, rate limiting, extractor isolation and option restoration. JavaScript syntax check passed.

A fresh real sample with the existing engine and dynamic helper automatically selected DE, downloaded 87,463 bytes and passed FFprobe inspection: video and audio, 5.021 seconds. Sample: build/youtube-dynamic-country-sample/sample.webm. This remains a short-sample transfer test, not full-length validation or a guarantee that changing the player locale defeats IP-based regional restrictions. No VPN or server added. Installed executable remains unchanged until rebuilt.
