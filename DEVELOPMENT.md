# Development

## Windows setup

Use Python 3.12 with Tkinter, Microsoft Edge WebView2 Runtime, and a virtual environment. Node.js is needed for the JavaScript regression checks. The requirements record direct dependency versions from the 1.2.5 build environment; transitive dependencies are not fully locked.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/main.py
```

The application uses `%APPDATA%/YoutubePro` for settings and media engine components. Use the component update UI to install/check FFmpeg and FFprobe. Verified engine updates can supersede the bundled yt-dlp version.

## Regression tests

Run these offline suites explicitly:

```powershell
python -m unittest discover -s tests -p test_scheduler.py
python -m unittest discover -s tests -p test_library_features.py
python -m unittest discover -s tests -p test_app_updates.py
python -m unittest discover -s tests -p test_components.py
python -m unittest discover -s tests -p test_audit.py
python -m unittest discover -s tests -p test_studio.py
python -m unittest discover -s tests -p test_source_quality.py
python -m unittest discover -s tests -p test_previews.py
Get-ChildItem tests/test_*ui.cjs | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { throw "UI check failed" } }
```

`test_local_download.py`, `test_bandwidth_local.py`, and `preview_library.py` use synthetic local media and require working FFmpeg/FFprobe components. The preview server listens on localhost port 5056 and uses a temporary data directory. Avoid pointing manual tests at personal media or browser cookies.

## Build an installer

Install Inno Setup 6 and the build dependencies:

```powershell
python -m pip install -r requirements-build.txt
python scripts/build_release.py --version 1.2.6
```

Use a fresh version number for each release. The script updates `version.json`, creates `dist/YoutubePro/`, and writes an installer, SHA-256 checksum, and release metadata to `releases/vX.Y.Z/`. It does not publish to GitHub. Direct distribution of the unpacked application requires the entire `dist/YoutubePro` directory, including `_internal`.

Upload `VideoDownloaderPro_Setup.exe` and `SHA256SUMS.txt` to a stable GitHub release with the matching version tag. GitHub must provide the installer asset digest for in-app updates. Create future release tags from the matching source commit.

The existing v1.2.5 release tag predates this source synchronization; its automatic source archives reflect the older tagged commit. The published installer is unchanged. Use this synchronization commit on `main` for the corresponding updated source.

## Layout

- `src/main.py`: native desktop entry point.
- `src/app.py`: local Flask routes and application integration.
- `src/core/`: scheduler, download execution, bandwidth and retry policy.
- `src/services/`: updates, metadata, previews and persistence.
- `src/static/` and `src/templates/`: interface and local vendor assets.
- `build_assets/`, `YoutubePro.spec`, `scripts/build_release.py`: packaging.

Local state, downloaded media, credentials and generated installers are intentionally excluded from the repository.

## Site adapter tests (1.2.9 preview)

Run `python -m unittest discover -s tests -p test_site_resolver.py` and `node tests/test_site_inspection_ui.cjs` for isolated adapter/UI checks. `test_site_local_download.py` uses synthetic local HLS and requires FFmpeg/FFprobe. `python tests/preview_site_native.py` starts an isolated Windows WebView2 manual test on localhost:5056; open that URL to test the real hidden browser flow. It never loads your existing download history or settings. Stop the fixture with Ctrl+C.

See [SITE_DESTEGI_1.2.9.md](SITE_DESTEGI_1.2.9.md) for scope and validation limits.
