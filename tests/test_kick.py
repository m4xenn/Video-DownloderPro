import sys
import yt_dlp

url = "https://kick.com/jahrein"

ydl_opts = {
    'verbose': True,
    'format': 'bestvideo+bestaudio/best',
    'simulate': True,
    'cookiesfrombrowser': ('edge', )
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        ydl.download([url])
    except Exception as e:
        print("Exception:", e)
