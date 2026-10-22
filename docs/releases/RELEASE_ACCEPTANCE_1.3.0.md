# Video Downloader Pro 1.3.0 release acceptance

Validated on 2026-10-22 before publication.

## Scope

Redesigned workspace with New, Queue, History, Guide and Settings pages; stable shell size; smoother theme/navigation changes; first-run tour; ten-language illustrated offline guide; saved-media history previews; new icon; maximized startup. Clip downloading remains excluded.

## Completed checks

- 295 isolated Python tests passed with no failures, errors or skips. External-site diagnostic scripts that read browser sessions are excluded from this test run.
- All 15 JavaScript regression suites passed.
- Edge browser acceptance passed: onboarding persistence/swipe/keyboard access, queue operations, inline history and settings, previews, long-list navigation, stable shell dimensions, scroll restoration, rapid navigation, theme switching, reduced motion and responsive layouts. No page errors.
- 70 live-UI guide screenshots regenerated for ten languages. Asset dimensions and localization schemas passed.
- Packaged EXE launched using an isolated profile and served version 1.3.0. Every packaged static/template asset and the bundled icon match the release sources.
- Frozen EXE acceptance passed using synthetic localhost media: MP4, MP3, M4A, WAV and Opus outputs verified by FFprobe; duplicate output protection; pause, process restart and resume; failed-download state; sanitized diagnostics.
- Isolated current-user installer fixture upgraded the actual 1.2.14 payload to 1.3.0. All 1,958 installed payload files matched distributable hashes. Settings, language, history, drafts and paused jobs survived.
- Same-version reinstall and downgrade were rejected. Uninstall preserved the test profile; a clean application install also succeeded.
- Startup options and completion-notification dispatch were covered by tests. Completion notification dispatch is independent of the app being open.

## Artifact

- Installer: `VideoDownloaderPro_Setup.exe`
- Size: 46,867,059 bytes
- SHA-256: `14e4a4637dfda51d8c6dea7734a3440d5b2fe0175754ae3d0e7f9d0b59709ed1`

## Validation limits

The installer fixture overrides only identity, destination, privileges and shortcuts, and does not replace the personal production installation. No clean Windows VM, production UAC upgrade or new shortcut acceptance was performed for this release. Browser preview playback depends on installed browser codecs. Windows notification appearance remains subject to Windows notification preferences. No publisher signature is added. Public digest, source-tag and updater checks are performed after publication and stored with the local release artifacts.
