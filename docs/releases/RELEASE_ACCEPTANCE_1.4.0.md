# Video Downloader Pro 1.4.0 release acceptance

Validated on 2026-11-01 before publication, against the 1.3.0 stable baseline.

## Scope

Browser companion 0.4.1 and guided Chrome/Edge/Brave setup; ten-language live
synchronization; improved shared embedded discovery and HLS/DASH handling; track
selection; partial-source and completed-output validation; safe source recovery;
YouTube player-country search; measured fragment mode; bounded live recording;
Recovery center, single application instance and durable close/restart behavior.
See [release notes](RELEASE_NOTES_1.4.0.md) for user-visible changes and limits.

## Completed checks

- **473 isolated Python tests passed**, zero failures/errors/skips. This includes
  generated HTTP/HLS/DASH downloads, track selection, ordinary AES-128, output
  validation, strong-validator signed-URL resume, live interruption handling,
  graceful and abrupt process restart/Range recovery, lifecycle and language sync.
- All **26 JavaScript UI suites passed**.
- All **27 native WebView2 checks passed**, including nested/lazy/network player
  cases, selected/highest-quality audio-video downloads, browser lifetime and
  preview-to-download handoff cleanup.
- A separate real Brave profile passed companion 0.4.1/native-host handoff and
  automatic selection of one verified HLS master with three observed playlists.
  The temporary native-host test registration was removed afterward.
- The 70 base guide captures plus ten companion and ten live-recording captures
  were refreshed from the 1.4.0 rendered app. Setup consent, ten locales, live
  payload, preserved track choices, measured-mode settings and partial-source
  rejection passed the associated rendered acceptance checks.
- The release EXE passed real MP4/MP3/M4A/WAV/Opus transfer and FFprobe checks,
  duplicate output preservation, pause/process restart/resume, 404 failure state,
  sanitized reports and bundled static asset serving in an isolated profile.
- Packaged companion/native executable exchange passed. French/Japanese/Turkish
  application language changes reached the actual native-host replies. The
  release EXE held the desktop mutex and a second launch exited before app import.
  Setup without consent did not write installation/registration files.
- Native close-event acceptance passed Cancel, continued window usability,
  asynchronous confirmed shutdown and saving before window closure.
- The original reported YouTube page resolved through the actual application
  metadata API and default motor options, exposing seven quality choices. This
  final check did not transfer the whole video.
- Isolated installer acceptance upgraded the actual installed 1.3.0 payload to
  1.4.0. **2,062 installed payload files** matched distributable SHA-256 hashes.
  Settings, language, history, drafts and paused jobs survived and the app opened.
- Same-version reinstall and downgrade were rejected without changing payloads.
  Uninstall preserved profile data, followed by a successful fresh application
  install. The final isolated fixture was removed; production installation stayed
  unchanged.

## Artifact

- Installer: `VideoDownloaderPro_Setup.exe`
- Size: **61,277,813 bytes**
- SHA-256: `702d119c3cb39f3bad96aea29a0a839d78979a7dc5a5e8e7f1a1fca5e1d2f994`
- Companion: **0.4.1**, stable public identity preserved.
- The full frozen app is `dist/YoutubePro/`; installer and checksum are under
  `releases/v1.4.0/`. Source tag must be created from the matching committed source.

## Evidence

Local artifacts are intentionally ignored by Git:

- `build/release-tests-1.4.0/result.json` and `unit.log`.
- `build/release-native-1.4.0.log`, `release-brave-1.4.0.log`.
- `build/release-help-1.4.0.log`, `release-close-1.4.0.log`.
- `build/release-companion-1.4.0/result.json`.
- `build/release-runtime-1.4.0/result.json`.
- `build/installer-acceptance-1.4.0/result.json`.
- `build/release-youtube-1.4.0/result.json`.

Publication requires the GitHub asset digest/source-tag checks and a public
installer download hash comparison; the publishing workflow stores that evidence
under `releases/v1.4.0/` after publication.

## Limits

No clean Windows VM or production UAC/shortcut upgrade was performed. Installer
fixtures override identity, destination, privileges and shortcuts to avoid
modifying the user's real installation. No publisher signature is added.

The browser companion remains an opt-in unpacked extension and needs browser
approval. No universal site success, CAPTCHA solving or general DRM decryption
is claimed. Country preferences do not change network exit. Resume requires a
supported and verified source. Public samples/metadata are not whole-film
completion tests. Live capture limits and provider-specific restrictions remain
as described in the release notes.
