import sys
import os

# Kök dizini sys.path'e ekle (antigravity_config importu için)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from antigravity_config import (
        CURRENT_VERSION, GITHUB_REPO,
        CONCURRENT_FRAGMENT_DOWNLOADS, AUDIO_PREFERRED_QUALITY,
        DEFAULT_CONCURRENT_DOWNLOADS
    )
except ImportError:
    CURRENT_VERSION = "v1.0.0"
    GITHUB_REPO = "m4xenn/Video-DownloderPro"
    CONCURRENT_FRAGMENT_DOWNLOADS = 5
    AUDIO_PREFERRED_QUALITY = "192"
    DEFAULT_CONCURRENT_DOWNLOADS = 3

# Activate a verified Python engine before any yt_dlp import.
from services.component_runtime import activate_engine, BIN_DIR as COMPONENT_BIN_DIR
activate_engine()
BIN_DIR = str(COMPONENT_BIN_DIR)

from flask import Flask, render_template, request, jsonify
import threading
import subprocess
import platform
import time
import tkinter as tk
from tkinter import filedialog
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
import webview

from state.app_state import state, state_actions
from core.format_resolver import get_ydl_opts
from services.notification_service import show_notification
from services.folder_service import open_folder_dialog
from services.updater_service import check_app_update as check_app_update_logic
from services.component_updater import ComponentUpdater, component_status
from core.queue_manager import DownloadManager
from utils.download_settings import normalize_settings, bytes_per_second
from services.app_update_service import AppUpdater
from services.download_store import DownloadStore
from services.media_catalog import MediaCatalog
from services.language_service import SUPPORTED_LANGUAGES, system_language
# --- FAZ 1: Utils modülleri ---
from utils.i18n import py_i18n, get_i18n
from utils.file_helpers import (
    load_settings, save_settings_to_file
)
from utils.formatters import clean_ansi
# ------------------------------
app_updater = AppUpdater(GITHUB_REPO, CURRENT_VERSION)
component_updater = ComponentUpdater()
operation_lock = threading.RLock()
download_store = DownloadStore()
media_catalog = MediaCatalog()
download_manager = DownloadManager(store=download_store)


def ensure_download_state():
    with operation_lock:
        if not download_manager.restored:
            try:
                download_manager.restore()
                settings = load_settings()
                download_manager.configure(settings['concurrency_mode'], settings['concurrent_downloads'], bytes_per_second(settings))
            except Exception as exc:
                download_manager.restored = True
                download_manager.storage_error = 'Kuyruk kaydı okunamadı: ' + str(exc)
                download_store.read_error = download_manager.storage_error


def media_download_active():
    return download_manager.busy()

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    # If static folder exists in the future, it can be passed here as well
    # static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=os.path.join(sys._MEIPASS, 'static'))
else:
    app = Flask(__name__)


# --- AUTO UPDATE AYARLARI ---
# CURRENT_VERSION ve GITHUB_REPO artık antigravity_config.py'den geliyor
# ----------------------------

# load_settings, save_settings_to_file, load_history, save_history,
# add_to_history → utils/file_helpers.py (FAZ 1)
# py_i18n, get_i18n → utils/i18n.py (FAZ 1)


@app.route('/get-settings')
def get_settings_route():
    return jsonify(load_settings())

@app.route('/save-settings', methods=['POST'])
def save_settings_route():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(status='error', message='Geçersiz ayarlar.'), 400
    try:
        settings = normalize_settings(dict(load_settings(), **data))
        with operation_lock:
            download_manager.check_configuration(settings['concurrency_mode'], settings['concurrent_downloads'], bytes_per_second(settings))
            save_settings_to_file(settings)
            download_manager.configure(settings['concurrency_mode'], settings['concurrent_downloads'], bytes_per_second(settings))
        return jsonify(status='success')
    except ValueError as exc:
        return jsonify(status='error', message=str(exc)), 400
    except OSError:
        return jsonify(status='error', message='Ayarlar kaydedilemedi.'), 500


def queue_action(action):
    ensure_download_state()
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('url'), str):
        return jsonify(status='error', message='Geçersiz kuyruk öğesi.'), 400
    try:
        with operation_lock:
            if action == 'resume' and (app_updater.snapshot()['status'] == 'installing' or component_updater.snapshot()['status'] == 'downloading'):
                raise ValueError('Güncelleme bitene kadar bekleyin.')
            getattr(download_manager, action)(data['url'])
        return jsonify(status='success')
    except ValueError as exc:
        return jsonify(status='error', message=str(exc)), 409


@app.route('/pause', methods=['POST'])
def pause_route():
    return queue_action('pause')


@app.route('/resume', methods=['POST'])
def resume_route():
    return queue_action('resume')


@app.route('/queue/remove', methods=['POST'])
def remove_queue_item():
    return queue_action('remove')

import urllib.parse
@app.route('/open-folder', methods=['POST'])
def open_folder_endpoint():
    data = request.get_json(silent=True) or {}
    path = data.get('path') if isinstance(data, dict) else None
    if not isinstance(path, str) or not path:
        return jsonify(status='error', message='Geçersiz klasör yolu.'), 400
    path = urllib.parse.unquote(path)
    if os.path.exists(path):
        folder = os.path.dirname(path)
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", folder])
    return jsonify({"status": "success"})

@app.route('/set-lang', methods=['POST'])
def set_lang():
    data = request.get_json(silent=True)
    lang = data.get('lang') if isinstance(data, dict) else None
    if not isinstance(lang, str) or lang not in SUPPORTED_LANGUAGES:
        return jsonify(status='error', message='Unsupported language.'), 400
    try:
        with operation_lock:
            if data.get('persist', True):
                settings = load_settings()
                settings['language'] = lang
                save_settings_to_file(settings)
            state['current_lang'] = lang
        return jsonify(status='success')
    except OSError:
        return jsonify(status='error', message='Language preference could not be saved.'), 500


@app.route('/toggle-fullscreen', methods=['POST'])
def toggle_fullscreen():
    if webview.windows:
        webview.windows[0].toggle_fullscreen()
    return jsonify({"status": "success"})

@app.route('/')
def home():
    ensure_download_state()
    return render_template('index.html', default_path=state.get('current_download_path') or "Lütfen Klasör Seçiniz...", current_version=CURRENT_VERSION, system_language=system_language(), saved_language=load_settings().get('language'))

@app.route('/select-folder', methods=['POST'])
def select_folder():
    path = open_folder_dialog()
    if path:
        state["current_download_path"] = path
        return jsonify({"status": "success", "path": path})
    return jsonify({"status": "cancel", "path": state["current_download_path"] if state["current_download_path"] else "Lütfen Klasör Seçiniz..."})

@app.route('/progress')
def get_progress():
    ensure_download_state()
    return jsonify(download_manager.snapshot())

@app.route('/get-info', methods=['POST'])
def get_info():
    data = request.get_json(silent=True)
    url = data.get('url') if isinstance(data, dict) else None
    from urllib.parse import urlsplit
    try:
        if not isinstance(url, str) or len(url) > 8192 or urlsplit(url).scheme not in ('http', 'https') or not urlsplit(url).hostname:
            return jsonify(status='error', message='Geçerli bir video bağlantısı girin.'), 400
    except ValueError:
        return jsonify(status='error', message='Geçerli bir video bağlantısı girin.'), 400
    
    try:
        from yt_dlp import YoutubeDL
        import os
        BIN_DIR = os.path.join(os.environ.get('APPDATA', ''), 'YoutubePro', 'bin')
        ffmpeg_dir = BIN_DIR # Just in case it's needed
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'ffmpeg_location': ffmpeg_dir,
            'socket_timeout': 15,
            'extractor_retries': 2
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            media_catalog.remember(url, info)
            title = info.get('title', 'Bilinmeyen Video')
            thumbnail = info.get('thumbnail', '')
            return jsonify({
                "status": "success",
                "url": url,
                "title": title,
                "thumbnail": thumbnail,
                "total_bytes": media_catalog.lookup(url).get("total_bytes"),
                "duration": info.get("duration"),
                "is_playlist": media_catalog.lookup(url).get('is_playlist', False),
                "video_qualities": media_catalog.lookup(url).get('video_qualities', [])
            })
    except Exception as e:
        print(f"/get-info error: {e}")
        return jsonify({"status": "error"})


@app.route('/previews/<name>')
def media_preview(name):
    import re
    from flask import abort, send_from_directory
    if not re.fullmatch(r'[a-f0-9]{32}\.jpg',name):
        abort(404)
    return send_from_directory(download_store.path.parent/'previews',name,max_age=86400)

@app.route('/download', methods=['POST'])
def download():
    ensure_download_state()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(status='error', message='Geçersiz indirme isteği.'), 400
    urls = data.get('urls')
    if not state['current_download_path']:
        return jsonify(status='error', message=get_i18n('err_folder', state['current_lang'])), 400
    if not isinstance(urls, list) or not urls or len(urls) > 500:
        return jsonify(status='error', message='1–500 bağlantıdan oluşan bir liste gönderin.'), 400
    from urllib.parse import urlsplit
    if any(not isinstance(url, str) or urlsplit(url).scheme not in ('http', 'https') or not urlsplit(url).hostname for url in urls):
        return jsonify(status='error', message='Yalnız geçerli http/https bağlantıları desteklenir.'), 400
    kind, quality = data.get('format'), data.get('quality')
    allowed = ('mp3', 'm4a', 'wav', 'opus') if kind == 'audio' else ('max', '8k', '4k', '1080p', '720p')
    from services.source_quality import parse_source_quality
    source = parse_source_quality(quality) if kind == 'video' else None
    if kind not in ('audio', 'video') or (quality not in allowed and not source):
        return jsonify(status='error', message='Geçersiz format veya kalite.'), 400
    if source:
        choices = media_catalog.lookup(urls[0]).get('video_qualities', [])
        if len(urls) != 1 or data.get('is_playlist') or quality not in [choice['value'] for choice in choices]:
            return jsonify(status='error', message='Bu kalite yalnız incelenen tek video için kullanılabilir. Kalite listesini yenileyin.'), 400
    if not isinstance(data.get('is_playlist', False), bool) or not isinstance(data.get('embed_subs', False), bool):
        return jsonify(status='error', message='Geçersiz indirme seçenekleri.'), 400
    if 'speed_limit' in data:
        return jsonify(status='error', message='Toplam hız sınırını Ayarlar üzerinden kaydedin.'), 400
    options = {'format': kind, 'quality': quality, 'embed_subs': data.get('embed_subs', False)}
    try:
        selected = data.get('playlist_selection')
        if data.get('is_playlist'):
            if not isinstance(selected, dict):
                raise ValueError('Önce listeden indirilecek videoları seçin.')
            entries = media_catalog.selected(selected.get('token'), selected.get('ids'), urls)
            specs = []
            seen = set()
            for entry in entries:
                if entry['url'] in seen:
                    continue
                seen.add(entry['url'])
                group = safe_playlist_name(entry.get('group'))
                specs.append(dict(entry, path=str(os.path.join(state['current_download_path'], group)) if group else state['current_download_path']))
        else:
            target = os.path.join(state['current_download_path'], 'Toplu_Indirmeler') if len(urls) > 1 else state['current_download_path']
            specs = [dict(media_catalog.lookup(url), path=target) for url in urls]
        return prepare_download(specs, options, urls)
    except (ValueError, TypeError) as exc:
        return jsonify(status='error', message=str(exc)), 400


def safe_playlist_name(title):
    import re
    if not title:
        return ''
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title).rstrip('. ')[:120] or 'Playlist'
    if title.upper().split('.')[0] in {'CON','PRN','AUX','NUL', *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))}:
        title = '_' + title
    return title


def start_specs(specs, options, source_urls):
    with operation_lock:
        if app_updater.snapshot()['status'] == 'installing' or component_updater.snapshot()['status'] == 'downloading':
            return jsonify(status='error', message='Güncellemenin bitmesini bekleyin.'), 409
        settings = load_settings()
        download_manager.configure(settings['concurrency_mode'], settings['concurrent_downloads'], bytes_per_second(settings))
        download_manager.submit_specs(specs, options, BIN_DIR, source_urls)
    return jsonify(status='success'), 202


def prepare_download(specs, options, source_urls=()):
    duplicate_rows = []
    for entry in specs:
        matches = download_store.duplicates(entry.get('media_key') or entry['url'], entry['url'], options)
        entry['_duplicate'] = bool(matches)
        if matches:
            duplicate_rows.append({key: matches[0][key] for key in ('id','title','format','quality','path','completed_at')})
    if duplicate_rows:
        token = media_catalog.plan(specs, options, source_urls)
        return jsonify(status='duplicate', confirmation_token=token, duplicates=duplicate_rows,
                       message='Aynı format ve kalitede indirilmiş dosyalar bulundu.'), 409
    return start_specs(specs, options, source_urls)


@app.route('/download/confirm', methods=['POST'])
def confirm_download():
    ensure_download_state()
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    try:
        if data.get('action') not in ('skip', 'again', 'cancel'):
            raise ValueError('Geçersiz onay.')
        plan = media_catalog.consume_plan(data.get('token'))
        specs = plan['specs']
        if data['action'] == 'cancel':
            return jsonify(status='cancelled')
        if data['action'] == 'skip':
            specs = [entry for entry in specs if not entry.get('_duplicate')]
        if not specs:
            drafts = [entry for entry in download_store.load_drafts() if entry['url'] not in plan['source_urls']]
            download_store.save_drafts(drafts)
            return jsonify(status='skipped', message='Tüm seçilen dosyalar zaten mevcut.')
        return start_specs(specs, plan['options'], plan['source_urls'])
    except (ValueError, TypeError) as exc:
        return jsonify(status='error', message=str(exc)), 409


@app.route('/queue/resume-all', methods=['POST'])
def resume_restored_queue():
    ensure_download_state()
    try:
        with operation_lock:
            if app_updater.snapshot()['status'] == 'installing' or component_updater.snapshot()['status'] == 'downloading':
                raise ValueError('Güncellemenin bitmesini bekleyin.')
            download_manager.resume_restored()
        return jsonify(status='success')
    except ValueError as exc:
        return jsonify(status='error', message=str(exc)), 409


@app.route('/queue/drafts', methods=['GET','POST'])
def draft_queue():
    ensure_download_state()
    try:
        if request.method == 'GET':
            entries = download_store.load_drafts()
            managed = {job.url for job in download_manager.jobs}
            return jsonify(items=[entry for entry in entries if entry['url'] not in managed])
        data = request.get_json(silent=True)
        data = data if isinstance(data, dict) else {}
        entries = data.get('items')
        if not isinstance(entries, list) or len(entries) > 500:
            raise ValueError('Geçersiz bağlantı kuyruğu.')
        from urllib.parse import urlsplit
        clean = []
        for entry in entries:
            url = entry.get('url') if isinstance(entry, dict) else None
            if not isinstance(url, str) or urlsplit(url).scheme not in ('http','https') or not urlsplit(url).hostname:
                raise ValueError('Geçersiz bağlantı.')
            clean.append({'url': url, 'title': str(entry.get('title') or 'Video')[:1000],
                          'thumbnail': str(entry.get('thumbnail') or '')[:4000]})
        download_store.save_drafts(clean)
        return jsonify(status='success')
    except Exception as exc:
        return jsonify(status='error', message=str(exc)), 400


@app.route('/playlist/preview', methods=['POST'])
def preview_playlist():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    urls = data.get('urls')
    from urllib.parse import urlsplit
    if not isinstance(urls, list) or not 1 <= len(urls) <= 20 or any(not isinstance(url,str) or urlsplit(url).scheme not in ('http','https') or not urlsplit(url).hostname for url in urls):
        return jsonify(status='error', message='1–20 geçerli liste bağlantısı gönderin.'), 400
    try:
        token = media_catalog.preview(urls)
        return jsonify(status='checking', token=token), 202
    except ValueError as exc:
        return jsonify(status='error', message=str(exc)), 409


@app.route('/playlist/preview/<token>')
def playlist_preview_status(token):
    try:
        return jsonify(media_catalog.preview_status(token))
    except ValueError as exc:
        return jsonify(status='error', message=str(exc)), 404


@app.route('/history')
def history():
    try:
        offset = max(0, int(request.args.get('offset', 0)))
        return jsonify(download_store.history(request.args.get('q','')[:200], offset))
    except Exception as exc:
        return jsonify(status='error', message='Geçmiş okunamadı: ' + str(exc)), 500


@app.route('/history/action', methods=['POST'])
def history_action():
    ensure_download_state()
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    try:
        record = download_store.get_history(data.get('id'))
        if not record:
            raise ValueError('Geçmiş kaydı bulunamadı.')
        action = data.get('action')
        if action == 'repeat':
            options = {key: record[key] for key in ('format','quality','embed_subs')}
            entry = {key: record[key] for key in ('url','title','thumbnail','media_key')}
            entry['path'] = os.path.dirname(record['path'])
            return prepare_download([entry], options)
        path = record['path']
        if not os.path.isfile(path):
            raise ValueError('Dosya taşınmış veya silinmiş. Tekrar indirebilirsiniz.')
        if action not in ('open', 'folder'):
            raise ValueError('Geçersiz geçmiş işlemi.')
        if action == 'open' and os.path.splitext(path)[1].lower() not in ('.mp4','.mp3','.m4a','.wav','.opus','.webm','.mkv'):
            raise ValueError('Bu dosya türü açılamaz.')
        if platform.system() == 'Windows':
            os.startfile(path if action == 'open' else os.path.dirname(path))
        else:
            subprocess.Popen(['open' if platform.system() == 'Darwin' else 'xdg-open', path if action == 'open' else os.path.dirname(path)])
        return jsonify(status='success')
    except Exception as exc:
        return jsonify(status='error', message=str(exc)), 409


@app.route('/check-components')
def get_check_components():
    return jsonify(component_status())


@app.route('/components/status')
def get_component_status():
    return jsonify(component_updater.snapshot())


@app.route('/components/check', methods=['POST'])
def check_component_updates():
    if not update_request_allowed():
        return jsonify(status='error', message='Geçersiz bileşen isteği.'), 403
    try:
        component_updater.start_check()
        return jsonify(status='success'), 202
    except ValueError as exc:
        return jsonify(status='error', message=str(exc)), 409


@app.route('/update-components', methods=['POST'])
def post_update_components():
    if not update_request_allowed():
        return jsonify(status='error', message='Geçersiz bileşen isteği.'), 403
    with operation_lock:
        if media_download_active() or app_updater.snapshot()['status'] == 'installing':
            return jsonify(status='error', message='Önce aktif indirme veya kurulum işleminin bitmesini bekleyin.'), 409
        try:
            component_updater.start_download()
            return jsonify(status='success'), 202
        except ValueError as exc:
            return jsonify(status='error', message=str(exc)), 409


@app.route('/check-app-update')
def check_app_update():
    result = check_app_update_logic(GITHUB_REPO, CURRENT_VERSION)
    return jsonify(result)


@app.route('/app-update/status')
def app_update_status():
    return jsonify(app_updater.snapshot())


@app.route('/app-update/download', methods=['POST'])
def download_app_update():
    if not update_request_allowed():
        return jsonify(status='error', message='Geçersiz güncelleme isteği.'), 403
    try:
        app_updater.start_download()
        return jsonify(status='success'), 202
    except ValueError as exc:
        return jsonify(status='error', message=str(exc)), 409


@app.route('/app-update/install', methods=['POST'])
def install_app_update():
    if not update_request_allowed():
        return jsonify(status='error', message='Geçersiz güncelleme isteği.'), 403
    # Require a real desktop window before executing anything; browser mode is for debugging.
    with operation_lock:
        if media_download_active() or component_updater.snapshot()['status'] == 'downloading':
            return jsonify(status='error', message='Önce aktif video indirmelerinin tamamlanmasını bekleyin.'), 409
        if not webview.windows:
            return jsonify(status='error', message='Kurulum için masaüstü uygulamasını kullanın.'), 409
        try:
            app_updater.launch()
        except (ValueError, OSError) as exc:
            return jsonify(status='error', message=str(exc)), 409
        timer = threading.Timer(1.0, webview.windows[0].destroy)
        timer.daemon = True
        timer.start()
        return jsonify(status='success')


def update_request_allowed():
    # Reject cross-site form posts to endpoints that download or execute installers.
    origin = request.headers.get('Origin')
    return (request.is_json and request.headers.get('Sec-Fetch-Site') != 'cross-site'
            and (not origin or origin == request.host_url.rstrip('/')))

if __name__ == '__main__':
    app.run(debug=True)
