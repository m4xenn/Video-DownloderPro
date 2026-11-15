# Video Downloader Pro 1.4.7 — published 15 November 2026

Stable/latest: https://github.com/m4xenn/Video-DownloderPro/releases/tag/v1.4.7

- Tested source/tag: `50f13c74bd34e06391490f89b689785b263b30e7`.
- Installer: `VideoDownloaderPro_Setup.exe`, 45,658,020 bytes.
- SHA-256: `fb3693254ccfa4b89aca9fa3a91d020ede32c7204205a849faef130e348fe8c6`.
- Installer and SHA256SUMS.txt uploaded; GitHub asset digests matched.
- Public installer downloaded again; size/hash matched the tested artifact.
- Stable/latest API and source tag verified. Version 1.4.3 was offered the update;
  1.4.7 correctly reported up to date. Release notes were available to the updater.
- Publication evidence: `releases/v1.4.7/published-verification.json` and
  `public-download-verification.json` (local generated evidence, excluded from Git).
- Source/package comparison: 76 compiled modules, main entry and 134 assets
  matched, allowing normal Git text newline conversion. Private data excluded.

[Acceptance evidence](../testing/FIELD_ACCEPTANCE_2026-11-15.md): eight-hour
recording/full decode/memory-growth gate, 630 Python and 28 JavaScript tests,
50 real queued media outputs, 40 rejected hostile frozen-HTTP requests and isolated
installer acceptance passed. The documented limits remain applicable.

Earlier 1.4.4–1.4.6 builds were local candidates, not public releases. Their
unpublished markers describe historical snapshots. This record supersedes the
unpublished markers in the 1.4.7 acceptance notes. Later documentation commits
do not move the tested source tag or change published installer bytes.

No production installation, personal settings or browser profiles were changed.
