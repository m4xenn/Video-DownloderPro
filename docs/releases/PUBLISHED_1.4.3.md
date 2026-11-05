# Video Downloader Pro 1.4.3 — published 5 November 2026

Stable/latest release: https://github.com/m4xenn/Video-DownloderPro/releases/tag/v1.4.3

- Release source/tag: `ee9d6e0df6a0cb9d63dbbba65a84e3e4de82888e`.
- Installer: `VideoDownloaderPro_Setup.exe`, **45,631,440 bytes**.
- SHA-256: `4ad541cd437ee10a4ffb34335ebb36b0ec76104f5b64b49a25027e495d1ecfbd`.
- Uploaded assets: installer and `SHA256SUMS.txt`; both GitHub digests matched.
- Public installer downloaded again; size/hash matched the tested candidate.
- Latest-release API returned stable `v1.4.3`; tag resolved to the tested source commit.
- Application update checks: 1.4.2 offered 1.4.3; 1.4.3 correctly reported up to date.
- English release notes are included in the public release and available to the updater.

Local evidence: `releases/v1.4.3/published-verification.json`,
`public-download-verification.json`, `build/publication-source-proof-1.4.3.json`.
Source publication checks matched 76 compiled modules, the entry point and 134
assets, allowing normal Git text newline conversion. No user profiles, cookies,
generated media, executables or diagnostics were added to the source commit.

[Final candidate acceptance](../testing/ENDURANCE_CANDIDATE_2026-11-05.md) covers
607 Python tests, the corrected four-hour recording/full decode, actual frozen
downloads and isolated installer acceptance. Earlier candidate documents describe
their state when written; this publication record supersedes unpublished flags.
The old unpublished local installer was backed up under
`build/superseded-1.4.3-before-publication` before promoting the tested bytes.

The tag stays on the tested release source commit. Later publication-documentation
commits do not change the tag or published installer. No production installation
or personal settings were changed by publication.
