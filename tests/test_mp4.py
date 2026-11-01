import os
import sys

BIN_DIR = os.path.join(os.environ.get('APPDATA', ''), 'YoutubePro', 'bin')
YTDLP_ZIP = os.path.join(BIN_DIR, 'yt-dlp.zip')
if os.path.exists(YTDLP_ZIP):
    sys.path.insert(0, YTDLP_ZIP)

from yt_dlp import YoutubeDL

ydl_opts = {
    'format': 'bestvideo[height<=360]+bestaudio/best',
    'merge_output_format': 'mp4',
    'writethumbnail': True,
    'ffmpeg_location': BIN_DIR,
    'ignoreerrors': True,
    'postprocessors': [
        {
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        },
        {'key': 'FFmpegMetadata'},
        {'key': 'FFmpegThumbnailsConvertor', 'format': 'png'},
        {'key': 'EmbedThumbnail'}
    ]
}

with YoutubeDL(ydl_opts) as ydl:
    retcode = ydl.download(['https://www.youtube.com/watch?v=jNQXAC9IVRw']) # Me at the zoo
    print("RETCODE:", retcode)
