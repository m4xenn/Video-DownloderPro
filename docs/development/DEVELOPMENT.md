# Development

Run the commands in this guide from the repository root. See the
[documentation index](../README.md) for architecture, testing and release reports.

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
- `docs/development/`: setup, contribution and publishing instructions.
- `docs/architecture/`: source discovery, players and download behavior.
- `docs/testing/`: test guides and diagnostic investigations.
- `docs/releases/`: historical release and acceptance reports.

Local state, downloaded media, credentials and generated installers are intentionally excluded from the repository.

## Site adapter tests (1.2.9 preview)

Run `python -m unittest discover -s tests -p test_site_resolver.py` and `node tests/test_site_inspection_ui.cjs` for isolated adapter/UI checks. `test_site_local_download.py` uses synthetic local HLS and requires FFmpeg/FFprobe. `python tests/preview_site_native.py` starts an isolated Windows WebView2 manual test on localhost:5056; open that URL to test the real hidden browser flow. It never loads your existing download history or settings. Stop the fixture with Ctrl+C.

See [SITE_SUPPORT_1.2.9.md](../architecture/SITE_SUPPORT_1.2.9.md) for scope and validation limits.

## Generic embedded discovery (1.2.11 preview)

Run `python -m unittest discover -s tests -p test_generic_discovery.py` for offline discovery/policy checks. Run `python tests/verify_generic_native.py` on Windows for an automated, isolated WebView2 test using only synthetic local HLS, DASH, and MP4 media. It exercises dynamic cross-origin frames, native extraction fallback, HTML5/JW Player/Video.js, cookie scoping, quality selection, real downloads, and helper cleanup. This fixture requires network loopback access, WebView2, and installed FFmpeg/FFprobe; the production public-address guard is relaxed only inside the fixture for its own temporary local server.

See [GENERIC_SOURCE_DISCOVERY_1.2.11.md](../architecture/GENERIC_SOURCE_DISCOVERY_1.2.11.md) for discovery budgets, supported observation paths, and limitations. Publishing a new release remains a separate step from building a test installer.

## In-place WebView2 frame inspection (1.2.12 preview)

Run `python -m unittest discover -s tests -p test_webview_frames.py` for frame ancestry, source context, DRM, and visible-control lifecycle checks. The native synthetic fixture now requires the nested player to retain its actual parent window. `probe_site_native.py URL --metadata --continue-in-browser` is an explicit diagnostic for a public page, using an isolated browser. Optional `--sample` reads at most 16 KiB from the first HLS segment without saving media. It never exports request header values or media URLs. See [NESTED_PLAYERS_1.2.12.md](../architecture/NESTED_PLAYERS_1.2.12.md) for the actual Aniwatch reproduction and validation limits.

## Automatic muted player activation (unpublished)

Run `python -m unittest discover -s tests -p test_player_activation.py`, `node tests/test_player_activation_ui.cjs`, and `node tests/test_site_inspection_ui.cjs`. The native fixture `python tests/verify_generic_native.py` now withholds its nested JW Player source until the application calls muted playback. See [AUTOMATIC_PLAYER_ACTIVATION.md](../architecture/AUTOMATIC_PLAYER_ACTIVATION.md) for activation budgets, verification handling, automatic rechecks after Continue, and validation limits. No CAPTCHA solver or local LLM is required or included.

## Persistent diagnostics and public-page matrix (unpublished)

Run `python -m unittest discover -s tests -p test_diagnostics.py` and `node tests/test_diagnostics_ui.cjs` for diagnostic privacy, persistence, concurrency, storage failure and UI checks. Use `python scripts/site_matrix.py --all` to explicitly run the sequential public-page metadata matrix. It does not download full videos. See [DIAGNOSTICS_AND_SITE_TESTS.md](../testing/DIAGNOSTICS_AND_SITE_TESTS.md) for scope, the first real baseline, export fields and remaining coverage.

## Lazy player gates and embedded validation (unpublished)

Use `node tests/test_lazy_player_ui.cjs` and `python -m unittest discover -s tests -p test_source_validation.py`. `python scripts/site_matrix.py --all --sample` additionally reads at most 16 KiB from one HLS segment per page and rejects HTML/JSON error samples. The native fixture now requires a labelled play gate to load its lazy iframe. See [LAZY_PLAYERS_AND_SOURCE_VALIDATION.md](../architecture/LAZY_PLAYERS_AND_SOURCE_VALIDATION.md) and `tests/site_matrix_after_lazy.json` for the real-page results and limits.

## Network-first embedded discovery (unpublished)

Run `python -m unittest discover -s tests -p test_network_media.py`. Native verification now includes an extensionless HLS response with no source URL in the DOM and no known player API. Network selection retains DOM/adapter fallbacks and refuses uncorrelated or ambiguous candidates. See [NETWORK_FIRST_DISCOVERY.md](../architecture/NETWORK_FIRST_DISCOVERY.md) and `tests/site_matrix_after_network.json` for scope, selection limits and real-page results.

## Browser handoff, bounded 403 recovery and error UI (unpublished)

Run `python -m unittest discover -s tests -p test_source_handoff.py`, `python tests/test_source_recovery_local.py` and `node tests/test_source_progress_ui.cjs`. Native verification also checks preview-to-download browser ownership and release after first media bytes. See [SESSION_HANDOFF_AND_ERROR_STATES.md](../architecture/SESSION_HANDOFF_AND_ERROR_STATES.md) for resource limits, conservative partial-file rules and queue error-copy behavior. `tests/site_matrix_after_handoff.json` contains the four-page bounded-sample regression result.

## Cross-format output preservation (1.2.14, unpublished)

Run `python -m unittest discover -s tests -p test_output_paths.py` and `python -m unittest discover -s tests -p test_local_download.py`. The real local regression downloads MP4 followed by MP3, M4A, WAV and Opus into one folder and checks that every completed file retains its hash after every conversion. In-process output reservations also prevent simultaneous workers from claiming the same stem, including intermediate files and partial downloads. A resumed job keeps its own checkpoint stem.

For source tests that call real download workers, set `VIDEO_DOWNLOADER_DATA_DIR` to a disposable directory under `build/` before running them; diagnostics otherwise use the normal application profile. This variable isolates queue/diagnostic storage, while existing tests individually isolate settings and update writes. `scripts/check_installed_runtime.py` isolates both APPDATA and LOCALAPPDATA and exercises the frozen EXE with synthetic media. It never opens personal queue/history files. Its component executables use same-volume hard links to avoid duplicating large binaries; it does not run component updates.

## Workspace UI acceptance

The workspace uses navy surfaces, a soft blue composer header, a lime navigation
mark, and separate input and queue areas. Queue navigation opens a dedicated
view with live status filters and title/URL search; New returns to the composer
without discarding drafts or preferences. The current destination is marked with
`aria-current`. Accepted submissions open the queue with filters cleared. Empty
queues offer an Add a link action, and unmatched searches offer Clear filters.
History opens within the workspace shell; settings keeps its dialog. Queue summaries derive from row
statuses, including errors; they do not represent lifetime download statistics.
The published version and installer are unchanged; download execution is preserved.

Run the optional isolated browser acceptance suite with Playwright and Microsoft
Edge installed:

```powershell
python tests/check_workspace_browser.py --output tmp/ui-redesign
```

It serves the application through Flask's test client, isolates settings and
storage in a temporary directory, and mocks metadata, submissions, queue commands,
progress and release checks. It checks the visible change between destinations,
draft preservation, accepted-submission navigation, pause/resume, live status
filter updates, title/URL search, empty-result recovery, adding/removing a link,
keyboard format selection, dialog focus recovery, both themes, all ten navigation
languages, horizontal overflow at
1120/900/600/390 px, and visibility of the primary action in the native 900 × 750
window. Screenshots and a JSON result are written to the chosen output directory.
The screenshots contain synthetic queue examples. This is source UI validation;
it does not replace a frozen installer acceptance run before the next release.

### Welcome tour and illustrated guide

The first-run tour has seven horizontally scrollable feature pages, numbered
navigation tabs, Previous/Next, Skip, keyboard arrows and reduced-motion support.
Its dismissal/completion is stored as `welcome_seen` in application settings via
`POST /onboarding/complete`; it does not depend on WebView browser storage or a
particular localhost origin. Existing users see the new tour once as well.
The Guide navigation opens the same topics with steps, tips and enlargable
screenshots. The tour can be replayed from the guide. Text is Turkish or English
(English fallback for other interface languages); screenshots match each of the ten interface languages with synthetic data. No screenshots are loaded from the internet.

Regression coverage:

```powershell
python -m unittest discover -s tests -p test_onboarding.py
python -m unittest discover -s tests -p test_studio.py
python tests/check_workspace_browser.py
```

To regenerate all 70 bundled screenshots from actual rendered application
controls and synthetic metadata/queue/history fixtures:

```powershell
python tests/capture_localized_help.py
```

Images are saved under `src/static/help/<language>/`; `manifest.json` records the
complete language/topic matrix and PNG dimensions. Review them after changing the UI.
The normal browser suite never overwrites these reference assets; it also checks
first-run completion across a reload after clearing browser storage, native
horizontal scrolling, replay, Skip/Escape, guide navigation and image zoom.


### Localized screenshot validation

`interface-locales.js` and `interface-localization.js` translate the live settings,
playlist/history controls, source-quality hints and queue summaries used in the
captures. Generated pictures are not edited to replace text. Each language also
uses localized demonstration video titles and locale-aware dates and numbers.
Regeneration checks for blank format labels and leftover Turkish UI text in
non-Turkish captures. Speed limits remain present in translated queue summaries.

```powershell
python -m unittest discover -s tests -p test_localized_help.py
node tests/test_interface_localization_ui.cjs
python tests/check_workspace_browser.py
```

The asset test checks all 70 unique PNG files and their dimensions. The browser
suite switches through all ten languages and all seven guide topics, verifies
the selected image path and waits for each image to load. The guide and tour use
the same image resolver. The old `--capture-help` option on the acceptance suite
is deprecated; use the dedicated capture script to keep the whole matrix valid.


### Stable themes and workspace transitions

Theme changes suspend transitions for two animation frames so foregrounds and
surfaces update together. Blanket inherited text-color/opacity transitions are
removed; switching themes keeps existing text nodes and the theme icon in place.
Workspace entrances use a cancellable 180 ms animation. Reduced-motion settings
skip it, repeated selection does not restart it, and a theme change cancels any
unfinished entrance. The shell stays anchored to the top instead of re-centering
when a destination changes height.

History is `#historyView` inside the workspace, with no backdrop, blur, dialog role
or focus trap. Search, pagination and file actions are preserved. Refreshes retain
existing rows until the latest response is ready. Pagination is disabled while a
replacement query is pending; stale responses/errors cannot replace a newer
search. Empty history and unmatched searches offer relevant recovery actions.

The browser suite samples text color, opacity, text-node identity and geometry
across four theme changes; checks a fixed header across all destinations; tests
rapid navigation and reduced motion; and verifies inline history, search recovery
and responsive layouts. Regenerate localized help screenshots after changing the
history layout with `python tests/capture_localized_help.py`.
