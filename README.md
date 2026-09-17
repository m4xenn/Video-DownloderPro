# Video Downloader 🎵

A sleek, lightning-fast, and open-source media downloader supporting YouTube and 1000+ platforms.

![App Icon](icon.ico)

Welcome to **Video Downloader**! This tool is designed to be the ultimate, fastest, and most elegant media downloader for your PC. It supports not only YouTube but over 1000+ different platforms (Twitter, Instagram, TikTok, Reddit, Soundcloud, Twitch, Vimeo, Bilibili, and many more).

---

## 🚀 Core Features

- **Batch & Playlist Downloading:** You can download single videos, entire playlists, or paste multiple links at once. Just toggle the "Download as Playlist" switch if the link is a playlist, and the app will automatically fetch all videos within it.
- **Auto-Update System:** You never have to worry about the downloader breaking. The app has a built-in auto-updater for its core engines (`yt-dlp` and `FFmpeg`). It silently keeps itself up-to-date with the latest web standards so downloads never fail.
- **Smart UI & Multi-Language Support:** The interface is highly responsive and supports both Light and Dark themes. More importantly, it natively supports **10 different languages** with real-time switching!
- **Native OS Notifications:** You don't need to keep the app open to check progress. Once all your downloads are successfully completed, you will receive a native Windows notification right on your desktop.

---

## 🎥 Video Downloads

When you select **"Video (MP4)"**, the app intelligently fetches the absolute highest quality video available and merges it perfectly with the highest quality audio.
- **Supported Resolutions:** 8K (4320p), 4K (2160p), 1080p (Full HD), and 720p (HD).
- **Codec Conversion:** If a video is originally in an unsupported or heavy codec (like VP9), the app will automatically convert it to a standard, highly compatible MP4 format using FFmpeg so it works perfectly in editors like Premiere Pro and After Effects.

---

## 🎵 Audio Formats & Cover Art (Metadata)

When you select **"Audio (MP3/WAV)"**, the application behaves like a high-end music ripper. However, you must pay attention to the format you choose, as they have different capabilities regarding cover arts (thumbnails) and ID3 tags.

1. **MP3 & M4A (Highly Recommended)**
   - *Quality:* Excellent balance of high-quality sound and small file size.
   - *Cover Art Support:* **YES!** The application will automatically download the video's thumbnail, crop it into a perfect square, and embed it deep inside the audio file. When you play the song on your phone, car, or media player, you will see the album cover perfectly.

2. **WAV**
   - *Quality:* Pure, lossless, uncompressed audio. This is the absolute highest quality you can get, but the file size will be significantly larger.
   - *Cover Art Support:* **NO.** The WAV container format does not natively support embedded image tags. The app will skip cover art embedding to prevent corruption.

3. **Opus**
   - *Quality:* A modern, highly efficient format that provides incredible sound quality at incredibly small file sizes.
   - *Cover Art Support:* **NO.** Similar to WAV, embedding cover arts is not fully supported across most standard players for Opus files.

---

## 🛠️ How To Use & Playlist Downloading

1. **CHOOSE A DESTINATION FOLDER**
   Click the "Please Select a Folder..." button at the top to choose where your files will be saved.

2. **SELECT FORMAT & QUALITY**
   Use the two dropdown menus to select your desired format (e.g., Video MP4 or Audio MP3) and the maximum quality you want.

3. **ADDING LINKS TO THE QUEUE**
   Paste the URL of your video or song into the input box and press ENTER (or click the "+" button). The item will instantly appear in the "Queue" list below. You can repeat this process to add as many videos as you want before starting the download.

4. **THE PLAYLIST FEATURE (CRUCIAL DETAIL)**
   There are two distinct ways to download multiple videos:
   - **The Manual Queue (Custom Playlist):** If you manually paste 5 different links into the queue one by one, the app will download all 5 of them together. To keep things organized, it will automatically create a sub-folder named "Toplu_Indirmeler" (Batch Downloads) in your chosen directory and place all 5 files in there.
   - **The "Download as Playlist" Toggle:** If you have a link to an actual YouTube Playlist (or Spotify Album) that contains 50 songs, you DO NOT need to paste 50 links. Instead, simply paste the ONE link of the playlist into the box, and **TURN ON the "Download as Playlist" switch** (the toggle button below the format options). When you start the download with this switch turned on, the app will scan the link, find all 50 videos inside that playlist, and download them sequentially. It will also automatically create a folder named after the actual Playlist's title!

5. **START THE DOWNLOAD**
   Once your queue is ready and your playlist switch is set according to your needs, click "Start Download". 

*The progress bar will show you exact percentages and states ("Downloading..." means it's fetching data from the internet, "Converting..." means FFmpeg is attaching cover arts or fixing codecs). Do not close the application while it is converting.*

=============================================================
**Enjoy your downloads!**
