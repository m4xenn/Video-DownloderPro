# Video Downloader Pro 1.4.7

This release brings the fixes tested in the local 1.4.4–1.4.6 candidates together.
It upgrades the public 1.4.3 release; those intermediate candidates were not public releases.

## Fixes

- Fixes the destination-folder button in packaged Windows installations. The
  application now uses its owned native folder picker without requiring Tkinter.
- Preserves the destination on cancellation or failure, prevents duplicate picker
  windows and displays picker errors in the selected application language.
- Opens the correct folder for paths containing literal percent characters and
  directory selections. Missing targets and OS errors no longer report success.
- Prevents damaged optional history metadata from breaking the entire history page.
- Preserves valid saved preferences when one field is malformed, without rewriting
  the settings file during recovery reads.
- Prevents simultaneous settings and language changes from restoring an old language.
- Rejects explicitly specified zero network ports instead of treating them as defaults.

## Security and acceptance

- Updates Soup Sieve to 4.0 to address three known HTML/CSS parsing and matching vulnerabilities.
- Passed 630 Python tests and 28 JavaScript suites, a real 50-file queue with
  audio/video validation and history preservation, and 40 hostile Origin/Host
  requests against the actual Windows application's HTTP server.
- Passed an eight-hour continuous local recording, full audio/video decode and
  memory-growth checks. The source hashes matched the tested recorder.
- Actual downloads, Defender checks and isolated clean-install/upgrade checks passed.
  These results do not guarantee every site, codec, network or 24-hour recording scenario.

Download **VideoDownloaderPro_Setup.exe**; **SHA256SUMS.txt** contains its checksum.
Finish or pause active work and close the application before installing.
Settings, history and paused work are preserved. The browser companion remains unchanged.
