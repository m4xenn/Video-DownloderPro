# Publishing a release

Repository: https://github.com/m4xenn/Video-DownloderPro

## Prepare

1. Use a new stable version in `version.json`. Never replace an already published
   installer with different bytes under the same version.
2. Run the regression checks in [DEVELOPMENT.md](DEVELOPMENT.md), including real
   local download/conversion tests. Keep test data and diagnostics isolated.
3. Build with `python scripts/build_release.py --version X.Y.Z`. The build creates
   the full `dist/YoutubePro/` directory and an Inno Setup installer under
   `releases/vX.Y.Z/`, plus `SHA256SUMS.txt` and `release-info.json`.
4. Test the packaged executable, installation and upgrade. Preserve the legacy
   installer identity so existing installations are upgraded rather than duplicated.
5. Commit the corresponding source. Create the release tag from that exact commit.
   Check that user profiles, cookies, local logs and generated media are not staged.

## Publish

1. Create a draft GitHub Release with the matching tag and English release notes.
2. Upload exactly `VideoDownloaderPro_Setup.exe` and `SHA256SUMS.txt` from that
   version's output directory. Preserve the installer's exact filename.
3. Compare GitHub's SHA-256 asset digest and size with `release-info.json`.
4. Publish as a stable release and mark it latest. Do not select prerelease.

The build script does not upload or publish anything. GitHub Releases is the
distribution and update channel; no repository credentials belong in the app.

## Verify after publishing

- The latest-release API returns the expected stable tag and installer digest.
- The tag resolves to the source commit used for the package.
- An older application version is offered the new installer; the current version
  is not incorrectly offered an update.
- Download the public installer and compare its SHA-256 with the local artifact.
- Test installing the update when a suitable older installation is available.
  Active media downloads must block installation. No-network or API errors must
  be displayed as errors rather than a false up-to-date result.

Application updates and yt-dlp/FFmpeg component updates are independent.
SHA-256 checks integrity; the project does not currently add a publisher signature.

## 1.2.14 acceptance

See [RELEASE_ACCEPTANCE_1.2.14.md](RELEASE_ACCEPTANCE_1.2.14.md). Production
1.2.8 to 1.2.14 upgrade, personal-data preservation, installed payload hashes,
shortcuts and frozen-executable download/conversion checks passed. No clean
Windows VM was used. Local 1.2.13 artifacts are rejected and must not be published.
