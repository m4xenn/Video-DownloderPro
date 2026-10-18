# ============================================================
#  src/core/format_resolver.py
#  Format/kalite çözümleme motoru
#
#  app.py'den taşındı (FAZ 4a)
# ============================================================

import os
import sys
from services.source_quality import parse_source_quality

# Kök dizini sys.path'e ekle (antigravity_config importu için)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from antigravity_config import CONCURRENT_FRAGMENT_DOWNLOADS, AUDIO_PREFERRED_QUALITY
except ImportError:
    CONCURRENT_FRAGMENT_DOWNLOADS = 5
    AUDIO_PREFERRED_QUALITY = "192"


def get_ydl_opts(format_type, quality, save_path, speed_limit, embed_subs, progress_hook, bin_dir):
    """
    Kullanıcının seçtiği ayarlara göre yt-dlp parametrelerini (ydl_opts) oluşturur.

    Args:
        format_type (str): 'audio' veya 'video'
        quality (str): '8k', '4k', '1080p', 'mp3', 'm4a' vb.
        save_path (str): Kaydedilecek klasör yolu
        speed_limit (str/int): Hız limiti (0 ise limitsiz)
        embed_subs (bool): Altyazı gömülecek mi?
        progress_hook (callable): İndirme ilerlemesini takip edecek fonksiyon
        bin_dir (str): ffmpeg/ffprobe dizini

    Returns:
        dict: yt-dlp için yapılandırılmış seçenekler sözlüğü
    """
    ydl_opts = {
        'progress_hooks': [progress_hook],
        'ignoreerrors': True,
        'verbose': False,
        'nocheckcertificate': True,
        'extract_flat': False,
        'concurrent_fragment_downloads': CONCURRENT_FRAGMENT_DOWNLOADS,
        'ffmpeg_location': bin_dir,
        'writethumbnail': True,
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'nocheckcertificate': True,
        'restrictfilenames': True
    }

    if speed_limit and str(speed_limit) != "0":
        try:
            ydl_opts['ratelimit'] = int(speed_limit)
        except:
            pass

    if format_type == 'audio':
        target_codec = quality if quality in ['mp3', 'm4a', 'wav', 'opus'] else 'mp3'
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': target_codec,
                'preferredquality': AUDIO_PREFERRED_QUALITY,
            },
            {'key': 'FFmpegMetadata'},
        ]
        if target_codec in ['mp3', 'm4a', 'opus']:
            ydl_opts['postprocessors'].append({'key': 'FFmpegThumbnailsConvertor', 'format': 'png'})
            ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail'})
            ydl_opts['postprocessor_args'] = {
                'embedthumbnail+ffmpeg_o': [
                    '-c:v', 'mjpeg',
                    '-vf', "crop='if(gt(ih,iw),iw,ih)':'if(gt(iw,ih),ih,iw)'"
                ]
            }
        else:
            ydl_opts['writethumbnail'] = False
    else:
        source = parse_source_quality(quality)
        if source:
            height, fps = source
            # Extractors may report 30000/1001 as 29.97002997 while the UI rounds it.
            filters = f'[height={height}]' + (f'[fps<={fps + .001:g}]' if fps else '')
            ydl_opts['format'] = f'bestvideo{filters}+bestaudio/best{filters}'
        elif quality == '8k': ydl_opts['format'] = 'bestvideo[height<=4320]+bestaudio/best / best[height<=4320] / best'
        elif quality == '4k': ydl_opts['format'] = 'bestvideo[height<=2160]+bestaudio/best / best[height<=2160] / best'
        elif quality == '1080p': ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best / best[height<=1080] / best'
        elif quality == '720p': ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best / best[height<=720] / best'
        else:
            ydl_opts['format'] = 'bestvideo+bestaudio/best / best'
            ydl_opts['format_sort'] = ['res', 'fps']
        
        ydl_opts['merge_output_format'] = 'mp4'
        
        if 'postprocessors' not in ydl_opts:
            ydl_opts['postprocessors'] = []
            
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        })
        
        if embed_subs:
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitleslangs'] = ['all']
            ydl_opts['postprocessors'].append({'key': 'FFmpegEmbedSubtitle'})
            
        ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata'})
        ydl_opts['writethumbnail'] = False

    return ydl_opts
