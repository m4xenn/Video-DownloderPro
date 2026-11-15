# Video Downloader Pro 1.4.4

- Fixes the destination-folder button not opening a picker in the packaged
  Windows application. Uses the application's owned native folder dialog without
  depending on Tkinter.
- Preserves the current destination when selection is cancelled or fails.
- Shows folder-picker errors in the selected application language and prevents
  duplicate dialogs while a selection is pending.
- Validated with 615 Python tests, 28 JavaScript tests, an observed native Windows
  folder dialog, actual frozen downloads and isolated 1.4.3-to-1.4.4 upgrade checks.

Settings, history and paused work are preserved. The browser companion is unchanged.
This is a locally tested candidate and has not been published.
