# Video Downloader Pro 1.4.3 candidate acceptance

**Published 5 November 2026:** [stable/latest 1.4.3](https://github.com/m4xenn/Video-DownloderPro/releases/tag/v1.4.3).
[Publication verification](PUBLISHED_1.4.3.md) supersedes unpublished flags below.

**5 November: local candidate acceptance passed; unpublished.** See the
[final evidence](../testing/ENDURANCE_CANDIDATE_2026-11-05.md): corrected four-hour
recording with full decode, 607 Python tests, matching source/PYZ/assets, actual
frozen downloads in six formats, isolated clean install/upgrade and 568 matching
installed files. Production UAC/fresh-VM testing remains outside this fixture.

Current installer: `build/endurance-release/candidate/VideoDownloaderPro_Setup.exe`,
45,631,440 bytes, SHA-256
`4ad541cd437ee10a4ffb34335ebb36b0ec76104f5b64b49a25027e495d1ecfbd`.
The original failed run was investigated and superseded by the passed corrected
run. The installer was rebuilt to include that fix. No publication occurred.

## Historical acceptance (superseded candidates)

Later [startup polish](../testing/STARTUP_POLISH_2026-11-03.md) is a separate tested
preview and requires rebuilding the unpublished installer before publication.

Validated on 2026-11-03 against the installed 1.4.2 baseline. This is a locally
built release candidate; no GitHub tag/release or production installation was
changed by the validation task.

The [complete readiness report](../testing/DVR_RELEASE_READINESS_2026-11-03.md)
records corrections, detailed evidence and limits. [Release notes](RELEASE_NOTES_1.4.3.md)
describe the resulting public behavior.

## Gates passed

- 518 full-regression tests with zero failures/errors/skips, plus a separate
  subsequently added real socket-read-timeout recovery test. Existing 27 UI
  JavaScript suites pass with unchanged interface sources.
- An actual from-start source with about 5 h 19 m of history was captured through
  the moving live edge and at least two additional continuous live minutes.
  The 5 h 33 m output passed a complete strict audio/video decode. This supersedes
  the initial preview's short-window-only and incomplete archive test limits.
- Error injection covers 503/429, reset, truncated data, socket timeout, source
  expiry, missing fragments, pause, source end, source headers and bounded sessions.
- Actual frozen Windows tests cover media conversion, live DVR selection, duration
  caps, 720p/1080p, full decode, pause/restart/resume, finish/save, preserving old
  partial bytes and rejecting a broadcast that ended after inspection.
- Isolated 1.4.2 -> 1.4.3 installer upgrade preserves settings, language, history,
  drafts and paused work; **2066 installed files** match payload hashes. Same-version
  reinstall/downgrade rejection, clean install and profile-preserving uninstall
  pass. The final isolated fixture was removed.
- Seven runtime file hashes and five compiled PYZ modules match current source.
  Actual bundled native-host messaging passes.

## Candidate artifact

**Current candidate:** `build/performance/candidate/VideoDownloaderPro_Setup.exe`, SHA-256 `a57c78a7eaa6673d98ce2d21c6914e4e9befc9e4dc5f32559c15f0f8337eb002` (45,542,963 bytes). This candidate passed isolated clean-install/upgrade acceptance with 554 installed payload file hashes verified. See `docs/testing/PERFORMANCE_OPTIMIZATION_2026-11-04.md` for the final preview, 579-test regression, measurements and scope. No publication occurred; production UAC/fresh Windows VM checks remain outside this fixture's scope. The artifacts listed below are superseded.

**Latest protected-media preview:** `build/protected-package/YoutubePro/YoutubePro.exe` (with `_internal`). See `docs/testing/MEDIA_SECURITY_2026-11-04.md`. It supersedes the audit preview below. The existing installer does not contain these additions; installer/upgrade acceptance and publication remain pending.

**Latest audit preview:** see `docs/testing/VULNERABILITY_AUDIT_2026-11-04.md`. It uses the patched dependency set and Python 3.14.10. This preview supersedes the earlier security preview; installer acceptance still needs to be repeated before publishing.

The latest security preview and evidence are in `docs/testing/SECURITY_HARDENING_2026-11-04.md`. The installer listed below also predates these security changes.

**Superseded preview:** the installer below predates startup polish and notification/localization changes. Rebuild before publishing. See `docs/testing/NOTIFICATION_LOCALIZATION_2026-11-04.md` for the latest preview and validation.

- File: `releases/v1.4.3/VideoDownloaderPro_Setup.exe`
- Size: **61,310,016 bytes**
- SHA-256: `55050ed3a34b9ee006ce52940278b2a2dc687eec63dfd6e6ada43ccc8acf34d3`
- Companion stays **0.4.1**.

No fresh Windows VM, production UAC/shortcut upgrade or publisher signature was
added. This does not certify every source/codec or 24 hours of continuous live
wall time. Source retention/access and connection failures remain external
constraints; the verified failure paths preserve partial work.

Publication must still use the matching committed source/tag and two assets,
verify GitHub digests and latest status, then check the public download and
old/current updater behavior as described in the publishing guide.
