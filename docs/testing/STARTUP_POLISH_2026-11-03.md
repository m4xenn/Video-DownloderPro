# Startup optimization and entrance animation — unpublished 1.4.3 preview

## Changes

- Import BeautifulSoup when HTML page parsing is actually requested, rather than
  during application startup. Load Tkinter/file-dialog modules only when opening
  the folder picker. Removed unused eager Tkinter imports from the Flask module.
- Keep queue restoration, verified-engine activation and durable shutdown behavior
  unchanged. Optional app/component update checks run after two animation frames
  and an idle callback (with a timeout), while ordinary initialization starts
  immediately.
- Use the application's navy background for the native WebView window instead of
  its white default during loading.
- Add a 380 ms opacity/10 px vertical/very small scale entrance to the workspace.
  No loading overlay, click blocking or artificial startup wait is introduced.
  Reduced-motion preference disables the animation. Light and dark themes pass.

## Measured evidence

An initial three-launch sample of the previous Windows candidate reached its HTTP
UI in 1.110, 1.073 and 1.056 seconds. An early comparison during regression load
was noisy and did not establish an improvement; it is not used as speed evidence.
Individual import-time traces were also noisy and are not a speed guarantee.

After the regression finished, five alternating launches of each actual Windows
EXE were measured with the same finer polling interval and separate isolated
profiles:

| Build | Process launch to HTTP UI readiness, seconds | Median |
| --- | --- | --- |
| Previous candidate | 1.327, 1.355, 1.339, 1.565, 1.403 | 1.355 |
| Startup preview | 1.171, 1.244, 1.143, 1.408, 1.256 | 1.244 |

This is approximately **8.2% lower median** on this machine. Filesystem/antivirus
caches, process scheduling and monitoring overhead affect these numbers. It is
not a controlled cold-boot benchmark or a measurement of animation completion.

## Validation

- **519 Python tests passed**, zero failures/errors/skips.
- All **27 JavaScript suites passed**.
- Actual rendered checks cover dark/light entrance, reduced motion, completing
  at full opacity and typing while the entrance is paused midway. No page errors.
- The new Windows EXE starts successfully in all benchmark runs. Four bundled
  source/assets match their hashes; both compiled native entry point and app
  bytecode match the current sources.

Evidence: `build/startup-polish-regression/`, `build/startup-idle-paired/result.json`,
`build/startup-ui/result.json`, `build/startup-ui/` screenshots,
`build/startup-payload-verification.json`, and `build/startup-polish-package-build.log`.

## Artifact state

The new preview is `build/startup-polish-package/YoutubePro/YoutubePro.exe` with
its adjacent `_internal` directory. It has not been published or installed.

The earlier installer under `releases/v1.4.3/` (SHA-256 beginning `55050ed3`) is the
previous DVR candidate and does **not** contain this startup polish. Before any
publication, archive that unpublished artifact, rebuild the installer from the
final source and run the relevant packaged/upgrade gates for the new bytes.
