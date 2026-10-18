# ============================================================
#  src/core/downloader.py
#  Temel indirme fonksiyonları ve progress kancaları
#
#  app.py'den taşındı (FAZ 4d)
# ============================================================

import time
import os
import sys

# Kök dizini sys.path'e ekle (modül importları için)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from state.app_state import state, state_actions
    from utils.formatters import clean_ansi
    import shutil
except ImportError:
    pass

def progress_hook(d):
    url = d.get('info_dict', {}).get('webpage_url')
    
    if url and state["cancel_flags"].get(url):
        state_actions.update_item_progress(url, status="paused")
        raise Exception("DOWNLOAD_PAUSED")

    if d['status'] == 'downloading':
        try:
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            percent = 0
            if total:
                percent = round((downloaded / total) * 100, 1)

            speed = d.get('_speed_str', 'Hesaplanıyor...')
            if speed:
                speed = clean_ansi(speed)
            
            if url:
                state_actions.update_item_progress(url, percent=percent, speed=speed, status="downloading")
        except: pass
    elif d['status'] == 'finished':
        if url:
            state_actions.update_item_progress(url, percent=100, status="converting")

def _download_single(url, ydl_opts, save_path, req_opts, folder_id=None):
    try:
        from yt_dlp import YoutubeDL
        with YoutubeDL(ydl_opts) as ydl:
            budget = req_opts.get('_budget')
            if budget:
                from core.bandwidth import attach_budget
                attach_budget(ydl, budget, lambda: bool(state['cancel_flags'].get(url)),
                              req_opts.get('_record', lambda _: None))
            # We need to extract info first to get the filename and title!
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("Video bilgisi alınamadı (Gizli veya kullanılamıyor olabilir).")
            if req_opts.get('_metadata'):
                req_opts['_metadata'](info)
            if budget:
                from yt_dlp.downloader import get_suitable_downloader
                formats = info.get('requested_formats') or [info]
                native = True
                for selected in formats:
                    downloader = get_suitable_downloader(selected, ydl.params)
                    if not downloader or downloader.__name__ not in ('HttpFD', 'HlsFD', 'DashSegmentsFD'):
                        native = False
                if req_opts.get('_protocol_support'):
                    req_opts['_protocol_support'](native)
                if budget.rate and not native:
                    raise ValueError('Bu yayın türü toplam hız sınırını desteklemiyor. Sınırı kaldırarak tekrar deneyin.')
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'Video')
            thumb = info.get('thumbnails', [{'url': ''}])[-1]['url'] if info.get('thumbnails') else ''
            
            # 1. Dosya varsa (1), (2) şeklinde isimlendir
            if req_opts.get("format") == "audio":
                final_ext = req_opts.get("quality", "mp3")
                if final_ext not in ['mp3', 'm4a', 'wav', 'opus']:
                    final_ext = "mp3"
            else:
                final_ext = "mp4"

            base_name = os.path.splitext(filename)[0]
            final_filename = f"{base_name}.{final_ext}"

            if os.path.exists(final_filename) and not req_opts.get('_resume_target'):
                i = 1
                while os.path.exists(f"{base_name} ({i}).{final_ext}"):
                    i += 1
                
                safe_base = base_name.replace('%', '%%')
                new_outtmpl = f"{safe_base} ({i}).%(ext)s"
                
                if isinstance(ydl.params.get('outtmpl'), dict):
                    ydl.params['outtmpl']['default'] = new_outtmpl
                else:
                    ydl.params['outtmpl'] = new_outtmpl
                
                final_filename = f"{base_name} ({i}).{final_ext}"
                filename = final_filename

            if req_opts.get('_target'):
                template_base = os.path.splitext(final_filename)[0].replace('%', '%%')
                req_opts['_target'](template_base + '.%(ext)s')

            # Reuse the resolved media information rather than extracting the URL again.
            result = ydl.process_ie_result(info, download=True)
            if result and os.path.isfile(final_filename):
                if req_opts.get('_preview_dir'):
                    from services.preview_service import create_preview
                    preview=create_preview(ydl,info,final_filename,ydl_opts.get('ffmpeg_location') or '',
                        req_opts['_preview_dir'],req_opts['_preview_id'],req_opts.get('format')!='audio')
                    if req_opts.get('_thumbnail'):
                        req_opts['_thumbnail'](preview)
                if req_opts.get('_completed'):
                    req_opts['_completed'](final_filename)
                # Update status
                state_actions.update_item_progress(url, status="finished")
                return True

    except Exception as e:
        if state['cancel_flags'].get(url) or str(e) == "DOWNLOAD_PAUSED":
            state_actions.update_item_progress(url, status='paused')
            pass # Handled
        else:
            print("Download error:", e)
            if req_opts.get('_error'):
                req_opts['_error'](str(e))
            state_actions.update_item_progress(url, status="error")
    return False
