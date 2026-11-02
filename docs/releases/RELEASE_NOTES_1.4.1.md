# Video Downloader Pro 1.4.1

## Live recording audio fix

- Fixed missing audio in some YouTube live recordings. A selected audio-only HLS
  stream is now recorded even when the source does not declare its codec name.
- Recording validation now requires that selected audio stream. Missing audio
  cannot silently produce a successful video-only recording.
- Improved input selection when codec metadata is incomplete.

## Clearer live duration and speed

- Live recordings now show an HH:MM:SS recorded-time/limit display and an
  approximate recording data rate instead of a misleading zero total speed.
- The general interface localization pass no longer replaces live duration with
  ordinary video size/ETA text.
- Added real-time recording explanations in all ten application languages.

A live stream normally arrives in real time; a faster internet connection cannot
fetch future broadcast content. The rate shown is approximately the recorded
stream's bitrate, not your connection's maximum speed. This update does not add
accelerated downloading of arbitrary past live windows.

A short recording from the reported YouTube live source was verified to contain
H.264 video and audible AAC audio. Existing files with no audio stream cannot
recover missing sound through a player setting; matching source audio needs to
be retrieved again.

Settings, history and paused jobs are preserved. Download
**VideoDownloaderPro_Setup.exe** to update. **SHA256SUMS.txt** contains its checksum.
