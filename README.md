# Video Downloader Pro 🎬

A Windows video and audio downloader with a redesigned blue-and-navy workspace, source-based quality selection, and a persistent download queue.

[⬇️ Download the latest release](https://github.com/m4xenn/Video-DownloderPro/releases/latest) · [📋 Release notes](https://github.com/m4xenn/Video-DownloderPro/releases) · [🐛 Report an issue](https://github.com/m4xenn/Video-DownloderPro/issues)

## ✨ Features

- 🧩 **Optional browser companion** — guided Chrome/Edge/Brave setup, clearer embedded-source labels and automatic synchronization with the app's ten languages. See the [setup guide](docs/BROWSER_EXTENSION.md). Loading the unpacked extension still requires browser approval.
- 🛟 **Recovery center and safe closure** — restore unfinished jobs, refresh expired sources, recover files saved before an interruption and export interrupted live parts. Compatible parts can be joined after acknowledging possible gaps. Confirm closure during downloads and prevent duplicate app instances. Resume depends on source support.
- 📡 **Live recording with catch-up** — download safely aligned, available HLS history quickly, then keep recording the live edge in the same MP4. The queue shows the catch-up stage and approximate delay. Duration limits include history. Live subtitles, audio-only live export and a positive shared speed cap are not supported.
- 🎚️ **Track selection and stronger output checks** — choose offered audio/subtitle languages for one inspected video; identify known truncated sources and verify downloaded streams, duration and file tails.
- 🌐 **YouTube player-country discovery** — try a limited sequence of country preferences on eligible availability errors. This does not change your IP or guarantee every regional restriction can be resolved.

- 🧪 **Embedded video discovery** — when native extraction cannot find a video, an on-demand background browser inspects HTML5, JW Player, Video.js, and nested players for HLS, DASH, or direct media sources. Nested players retain their parent page and actual request context. Use **Continue in browser**, then **Check again** if interaction is needed. DRM and universal site support are outside its scope.

- 🌍 **Automatic language selection** — starts in your system UI language when supported, falls back to English, and remembers your manual language choice.

- 🪟 **A refined desktop interface** — a stable-size workspace with New, Queue, History, Guide, and Settings pages, light/dark themes, and 10 interface languages. The window opens maximized with a new application icon.
- 📖 **Welcome tour and offline guide** — a swipeable first-run introduction and an illustrated feature guide, with screenshots localized for all 10 interface languages.
- 🔎 **Inspect before downloading** — paste a single video link to see its title, duration, and available resolution/FPS choices before adding it to the queue. Estimated size is shown when supplied by the source.
- 🎬 **Source-based video quality** — select a resolution the video actually offers, or use **Auto · Highest quality**. Batch downloads choose the highest available quality for each video, without a fixed 1080p cap.
- 🎵 **Video and audio output** — MP4/MKV video without automatic video re-encoding, and MP3, M4A, WAV, or Opus audio, with metadata and supported cover-art embedding. Known source resolution, frame rate, codec and HDR expectations are checked before completion.
- 🛡️ **Protected media handling** — guarded links and redirects, restricted media processes, output validation and local Defender scanning when available. Warnings and notification preferences follow the selected language.
- 🛡️ **Preserve existing outputs** — audio conversions use a free filename stem so their temporary video files cannot reuse an existing completed video. Concurrent downloads reserve distinct stems.
- 📋 **Single, batch, and playlist downloads** — paste several links at once, or choose individual entries from a playlist before downloading.
- 💾 **Persistent queue** — pending work is saved between sessions, with pause/resume controls and automatic retries for temporary failures.
- ⚡ **Automatic scheduling** — the app manages concurrent downloads, with an optional download speed limit in settings.
- 🕘 **Download history** — revisit completed downloads and receive a warning before downloading the same video again. Completed items stay in history after restarting. Preview saved videos or audio inside the History page, or open them in your system player. Browser playback depends on the media codec.
- 🖼️ **Better previews** — platform cover images are preferred, with frames from inside the downloaded video as a fallback.
- 🔔 **Windows completion notifications** — receive a notification when the download queue finishes, including while the app is open.
- 💬 **Optional subtitles** — embed available subtitles as soft subtitles in supported video output.
- 🔄 **Separate update controls** — application updates and yt-dlp/FFmpeg component updates are managed independently.

Platform support is provided by yt-dlp. YouTube, TikTok, Instagram, and many other sites are supported where their content is accessible; availability can change with platform restrictions, login requirements, or extractor updates.

## 📦 Install on Windows

1. Open the [latest release](https://github.com/m4xenn/Video-DownloderPro/releases/latest).
2. Download **VideoDownloaderPro_Setup.exe** from **Assets**.
3. Close any running copy of the app, run the installer, and follow the setup steps.
4. Choose a destination folder when you open the app.

The installer includes the Python runtime; you do not need to install Python separately. Use the component update controls to check or install the required yt-dlp/FFmpeg components.

**Upgrading from an older release?** Install the current version manually once to get the new in-app update system. The installer allows upgrades and prevents reinstalling the same or an older version over a registered newer installation.

## 🛠️ How to Use

### Download a single video

1. Paste its URL and wait for the video details to appear.
2. Choose your destination, output format, and quality.
3. Click **Start Download** directly, or use **+** to add it to the queue first.

Quality options reflect the source. File size or remaining time may be unavailable until the source provides enough information.

### Download several videos

Paste multiple links, separated by spaces or line breaks, and add them with **+**. Review the queue, then start downloading. With automatic highest quality, each video uses its own best available resolution.

### Select videos from a playlist

Add the playlist link, enable **Download as Playlist**, and start the download flow. Review the available entries and select the videos you want before confirming.

### Export audio

Choose **Audio**, then select MP3, M4A, WAV, or Opus. Metadata and cover-art behavior depend on the output format and player support. WAV produces uncompressed audio, but converting a compressed source to WAV does not restore lost detail or improve the original recording.

## 🔄 Updates

- **Application:** the app checks for newer stable releases at startup; you can also check manually in settings. Download the update in the app, then launch its installer when your active downloads are finished.
- **Components:** the component update button checks yt-dlp and FFmpeg separately. Review the available updates before downloading them. A yt-dlp engine update may require restarting the app.

Updates are user-controlled. The app verifies the downloaded application installer against the SHA-256 information supplied by GitHub. A newer component version does not necessarily mean a newer application version.

## 🐛 Feedback

Found a problem? [Open an issue](https://github.com/m4xenn/Video-DownloderPro/issues) with your app version, Windows version, reproduction steps, and the error message. Remove private links or personal information before sharing logs or screenshots.

## 🧑‍💻 Source Code

The `v1.4.3` tag contains the matching release source. Browse the [documentation index](docs/README.md), [development guide](docs/development/DEVELOPMENT.md), [publishing guide](docs/development/RELEASE_PUBLISHING.md), or [1.4.3 acceptance report](docs/releases/RELEASE_ACCEPTANCE_1.4.3.md). For normal installation, use [Releases](https://github.com/m4xenn/Video-DownloderPro/releases/latest).

## 📄 License

This project is licensed under the [MIT License](LICENSE).
