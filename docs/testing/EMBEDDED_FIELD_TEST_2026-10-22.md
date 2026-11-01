# Embedded-player field test — 2026-10-22

## Method

Public pages were tested using the current 1.3.0 source, isolated profiles and real Windows WebView2. Each runner visits one page at a time. Two independent passes compare the generic embedded resolver with the actual application `/get-info` flow. No existing browser session is imported. No CAPTCHA is solved and no DRM is removed.

Generic probes read metadata and explicitly request no more than 16 KiB from one accessible HLS segment, parsed DASH fragment or direct media resource. Manifests are bounded to 256 KiB. Player startup may additionally buffer media inside WebView2; the 16 KiB limit applies to the explicit diagnostic sample, not total browser traffic. Samples are never saved. No full downloads, seek/resume, complete playback or long-running token expiry checks are performed.

Player-family labels describe the intended test target. A redirected demo or source-selection form may no longer exercise that player. Observed generic groups are recorded separately; successful application extraction may use yt-dlp without the embedded-browser fallback. Counts describe this handpicked sample, not an internet-wide success rate.

## Results

Generic metadata: {'automatic': 7, 'interaction_required': 5, 'failed': 4}. Application metadata: {'automatic': 7, 'interaction_required': 5, 'failed': 4}.

| Case / public link | Intended family | Generic metadata | Observed groups | Quality heights | Media sample | Application metadata |
|---|---|---|---|---|---|---|
| [aniwatch-nested](https://aniwatch.co.at/one-piece-episode-1-english-subbed/) | Previous regression | automatic | jwplayer, video:0 | 1080p | passed / 16384 B / hls-segment | automatic |
| [fullhd-film](https://www.fullhdfilmizlesene.now/film/batman-2-kara-sovalye/) | Previous regression | automatic | not observed | 360p, 480p, 720p, 1080p, 2160p | passed / 16384 B / hls-segment | automatic |
| [hdfilm-film](https://www.hdfilmcehennemi.nl/batman-kara-sovalye-yukseliyor-hd-film-izle-hdf-hdf-5/) | Previous regression | failed / unsupported | not observed | not reported | not_tested | failed / unsupported |
| [hdfilm-esaret](https://www.hdfilmcehennemi.nl/1-esaretin-bedeli-film-izle-hdf-hdf-6/) | Previous regression | failed / unsupported | not observed | not reported | not_tested | failed / unsupported |
| [html5-w3schools](https://www.w3schools.com/html/html5_video.asp) | HTML5 | automatic | video:0, video:1 | not reported | passed / 16384 B / direct | automatic |
| [videojs-hls](https://videojs.github.io/videojs-contrib-hls/) | Video.js | automatic | video:0 | 234p, 360p, 540p, 720p, 1080p | passed / 16384 B / hls-segment | automatic |
| [plyr-home](https://plyr.io/) | Plyr / current Video.js | interaction_required | video:0 | not reported | not_tested | interaction_required |
| [hlsjs-demo](https://hlsjs.video-dev.org/demo/) | hls.js | interaction_required | video:0 | not reported | not_tested | interaction_required |
| [dashjs-reference](https://reference.dashif.org/dash.js/latest/samples/dash-if-reference-player/index.html) | dash.js | interaction_required | not observed | not reported | not_tested | interaction_required |
| [shaka-angel-one](https://shaka-project.github.io/shaka-player/demo/#asset=https://storage.googleapis.com/shaka-demo-assets/angel-one/dash.mpd;lang=en-US) | Shaka | interaction_required | not observed | not reported | not_tested | interaction_required |
| [bitmovin-stream](https://bitmovin.com/demos/test-stream/) | Bitmovin | interaction_required | video:0 | not reported | not_tested | interaction_required |
| [mediaelement-home](https://www.mediaelementjs.com/) | MediaElement.js | automatic | video:0 | not reported | passed / 16384 B / direct | automatic |
| [clappr-demo](https://clappr.io/demo/) | Clappr | failed / unsupported | not observed | not reported | not_tested | failed / unexpected |
| [jw-stream-tester](https://developer.jwplayer.com/tools/stream-tester/) | JW Player | failed / unsupported | not observed | not reported | not_tested | failed / unexpected |
| [vimeo-iframe](https://player.vimeo.com/video/76979871) | Vimeo | automatic | video:0 | 270p, 360p, 540p, 720p | not_tested / Encrypted sample not inspected | automatic |
| [jw-intel-embed](https://cdn.jwplayer.com/players/EwJonN6F-v2VOXzX8.html) | JW Player | automatic | jwplayer, video:0 | 180p, 270p, 406p, 608p | passed / 16384 B / hls-segment | automatic |


## Findings and next priorities

1. **Manifest-to-player association is the clearest reproduced product gap.** The hls.js follow-up completed page loading, found one HTML5/blob player (area about 116,278 CSS pixels squared), recorded four successful HLS responses, and found zero exact DOM-source matches. No verification screen was detected. Current selection deliberately refuses multiple unlinked network candidates. The evidence points to missing master/rendition association rather than a missing player, although the exact manifest relationships still need bounded parsing to be proven. Prioritize grouping verified master/variant relationships without combining ads or independent videos.
2. **The five interaction outcomes need focused follow-up.** Plyr/current Video.js, hls.js, dash.js, Shaka and Bitmovin reached the interaction-required path in both engines. This is not proof that a human action will resolve them. Test the visible Continue flow and inspect safe candidate evidence before adding player-specific code.
3. **Two previous regression pages now fail in both engines.** Independent bounded HTTP checks returned 403 for both hdfilmcehennemi.nl pages. This supports an access/site-change hypothesis but does not establish the exact browser failure cause. The same pages passed the earlier 2026-10-18 run.
4. **Demo infrastructure limits coverage.** Independent TLS-verified requests to the old Clappr demo and JW stream-tester URL raised SSLError; the application and generic runs also failed on these pages. No certificate checks were disabled. These results do not demonstrate that all Clappr or JW embeds are unsupported. The additional JW CDN iframe referenced in Intel's public workload brief passed in both engines and its sample was readable.
5. **Vimeo metadata succeeded, sample playback remains unverified.** A follow-up identified an AES-encrypted HLS playlist. The diagnostic sampler intentionally does not fetch/decrypt keys, so its initial generic sample failure was reclassified as not tested, with the reason retained. This is a sampler limitation and is not a DRM diagnosis or a proven download failure.

Both passes completed all 16 cases: **7 automatic metadata results, 5 interaction-required results, 4 failures**. Six explicit media samples passed; Vimeo sampling was not performed for the reason above. Other cases did not reach sampling. A passing short sample does not establish full-download reliability.

No production downloader/resolver behavior was changed in this task. Changes are confined to diagnostic tooling, the public-link manifest, tests and this report. The released 1.3.0 installer remains unchanged.

Sanitized raw result tables: [generic](data/embedded_field_2026-10-22_generic.json), [application](data/embedded_field_2026-10-22_app.json).

## Reproduce

```powershell
python scripts/site_matrix.py --manifest tests/site_matrix_extended.json --all --sample --timeout 75 --output build/field-test-2026-10-22-generic.json
python scripts/site_matrix.py --manifest tests/site_matrix_extended.json --all --engine app --timeout 75 --output build/field-test-2026-10-22-app.json
python scripts/render_field_report.py --date 2026-10-22
```

Use `--case ID` for targeted checks and `--resume` to continue an interrupted report with identical engine/sampling options. Process trees are stopped on timeout. Raw probe output is temporary; persisted JSON exports only allowlisted fields and excludes cookies, request-header values and discovered media URLs.
