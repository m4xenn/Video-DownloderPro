"""Exercise the real installed EXE with an isolated profile and local media.

No personal history/settings are opened. Only generated media is downloaded.
Runs actual HTTP routes, download workers, FFmpeg and SQLite in the frozen app.
"""
import argparse
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'version.json').read_text(encoding='utf-8'))['version']
BASE = ROOT / ('build/real-upgrade-' + VERSION) / 'runtime'
EXE = Path(os.environ['ProgramFiles(x86)']) / 'Studio Downloader/YoutubePro.exe'
SOURCE_BIN = Path(os.environ['APPDATA']) / 'YoutubePro/bin'
PROFILE = BASE / 'profile'
OUTPUT = BASE / 'output'
REPORT = {'status': 'running', 'scope': 'Actual installed EXE; isolated profile; synthetic localhost media', 'checks': []}


def passed(message):
    REPORT['checks'].append(message)
    (BASE / 'result.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
    print(message, flush=True)


def api(base, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(base + path, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def launch():
    env = dict(os.environ, APPDATA=str(PROFILE), LOCALAPPDATA=str(PROFILE / 'local'),
               VIDEO_DOWNLOADER_DATA_DIR=str(PROFILE / 'YoutubePro'))
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen([str(EXE)], env=env, startupinfo=startup)
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        assert process.poll() is None, 'Installed executable exited during startup'
        for connection in psutil.Process(process.pid).net_connections(kind='tcp'):
            if connection.status == psutil.CONN_LISTEN and connection.laddr.ip == '127.0.0.1':
                base = 'http://127.0.0.1:' + str(connection.laddr.port)
                try:
                    with urllib.request.urlopen(base, timeout=2) as response:
                        assert VERSION in response.read().decode('utf-8')
                    return process, base
                except OSError:
                    pass
        time.sleep(.25)
    stop(process)
    raise RuntimeError('Installed executable startup timed out')


def stop(process):
    if process.poll() is not None:
        return
    children = psutil.Process(process.pid).children(recursive=True)
    for child in reversed(children):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    process.terminate()
    process.wait(timeout=10)
    psutil.wait_procs(children, timeout=5)


def wait_job(base, url, terminal=('finished', 'error'), timeout=50):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        _, progress = api(base, '/progress')
        items = [item for item in progress['items'] if item['url'] == url]
        if items:
            last = items[-1]
            if last['status'] in terminal:
                return last
        time.sleep(.15)
    raise RuntimeError('Job timed out; last state: ' + repr(last))


def main():
    assert json.loads((EXE.parent / '_internal/version.json').read_text())['version'] == VERSION
    assert not BASE.exists(), 'Preserve previous runtime results; inspect before repeating.'
    OUTPUT.mkdir(parents=True)
    source = BASE / 'media'
    source.mkdir()
    component_bin = PROFILE / 'YoutubePro/bin'
    component_bin.mkdir(parents=True)
    for path in SOURCE_BIN.iterdir():
        if path.is_file() and (path.suffix in ('.exe', '.zip') or path.name == 'components.json'):
            target = component_bin / path.name
            if path.suffix == '.exe':
                # Same-volume hard links save space; tests never update components.
                os.link(path, target)
            else:
                shutil.copy2(path, target)
    subprocess.run([str(component_bin / 'ffmpeg.exe'), '-hide_banner', '-loglevel', 'error',
                    '-f', 'lavfi', '-i', 'testsrc2=s=640x360:r=24', '-f', 'lavfi', '-i', 'sine=frequency=440',
                    '-t', '4', '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', str(source / 'sample.mp4')], check=True, timeout=30)
    shutil.copy2(source / 'sample.mp4', source / 'pause.mp4')
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(source)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    media = 'http://127.0.0.1:' + str(server.server_port) + '/sample.mp4'
    pause_url = media.replace('sample.mp4', 'pause.mp4')
    missing = media.replace('sample.mp4', 'missing.mp4')
    sys.path.insert(0, str(ROOT / 'src'))
    from services.download_store import DownloadStore, media_key
    store = DownloadStore(PROFILE / 'YoutubePro/downloads.sqlite3')
    cases = [('mp4', 'video', 'max', media), ('mp3', 'audio', 'mp3', media),
             ('m4a', 'audio', 'm4a', media), ('wav', 'audio', 'wav', media),
             ('opus', 'audio', 'opus', media), ('pause', 'video', 'max', pause_url),
             ('missing', 'video', 'max', missing)]
    records = [{'id': 'fixture-' + label, 'media_key': media_key(url), 'url': url,
                'title': 'Runtime test ' + label, 'thumbnail': '', 'format': kind, 'quality': quality,
                'embed_subs': False, 'path': str(OUTPUT / ('missing-fixture-' + label + '.mp4')),
                'size': 0, 'completed_at': '2026-10-18T00:00:00+00:00'}
               for label, kind, quality, url in cases]
    store.commit_queue([], records)
    process = None
    try:
        process, base = launch()
        passed('Installed frozen EXE opened with isolated profile and real media components')
        with urllib.request.urlopen(base, timeout=5) as response:
            html = response.read().decode('utf-8')
        assets = set(re.findall(r'(?:src|href)="(/static/[^\"]+)"', html))
        assert assets, 'No bundled static assets referenced'
        for asset in assets:
            with urllib.request.urlopen(base + asset, timeout=5) as response:
                assert response.status == 200 and response.read(), asset
        passed('All ' + str(len(assets)) + ' referenced bundled CSS/JS/image/font entry assets served')
        code, result = api(base, '/get-info', {'url': media})
        assert code == 200 and result['status'] == 'success', result
        assert result.get('title') and 'duration' in result and isinstance(result.get('video_qualities'), list), result
        # A plain MP4 HTTP endpoint does not advertise duration/quality metadata;
        # its actual output is checked with FFprobe after the download below.
        passed('Actual /get-info resolves direct MP4, including supported unknown duration/quality state')
        code, _ = api(base, '/download', {'urls': [media], 'format': 'video', 'quality': 'max'})
        assert code == 400
        passed('Download rejected before destination selection')
        for label, kind, quality, url in cases[:5]:
            code, result = api(base, '/history/action', {'id': 'fixture-' + label, 'action': 'repeat'})
            assert code == 202, (label, result)
            job = wait_job(base, url)
            assert job['status'] == 'finished', job
            entries = api(base, '/history')[1]['items']
            entry = next(item for item in entries if not item['id'].startswith('fixture-')
                         and item['format'] == kind and item['quality'] == quality)
            path = Path(entry['path'])
            assert path.suffix == '.' + label and path.is_file(), str(path)
            data = json.loads(subprocess.check_output([str(component_bin / 'ffprobe.exe'), '-v', 'error',
                         '-show_streams', '-show_format', '-of', 'json', str(path)]))
            assert float(data['format']['duration']) >= 3
            assert any(item['codec_type'] == 'audio' for item in data['streams'])
            if kind == 'video':
                assert any(item['codec_type'] == 'video' and item['height'] == 360 for item in data['streams'])
            passed('Real ' + label.upper() + ' download/conversion verified by FFprobe')
        history = api(base, '/history')[1]
        existing = next(item for item in history['items'] if item['format'] == 'video' and not item['id'].startswith('fixture-'))
        original = hashlib.sha256(Path(existing['path']).read_bytes()).hexdigest()
        code, result = api(base, '/history/action', {'id': 'fixture-mp4', 'action': 'repeat'})
        assert code == 409 and result['status'] == 'duplicate', result
        code, skipped = api(base, '/download/confirm', {'token': result['confirmation_token'], 'action': 'skip'})
        assert skipped['status'] == 'skipped' and api(base, '/history')[1]['total'] == history['total']
        code, result = api(base, '/history/action', {'id': 'fixture-mp4', 'action': 'repeat'})
        code, result = api(base, '/download/confirm', {'token': result['confirmation_token'], 'action': 'again'})
        assert code == 202, result
        assert wait_job(base, media)['status'] == 'finished'
        assert api(base, '/history')[1]['total'] == history['total'] + 1
        assert hashlib.sha256(Path(existing['path']).read_bytes()).hexdigest() == original
        passed('Duplicate skip and re-download preserve original file and create a separate output')
        settings = {'concurrency_mode': 'manual', 'concurrent_downloads': 2, 'speed_limit_mbps': '0.4', 'auto_compress': False}
        assert api(base, '/save-settings', settings)[0] == 200
        assert api(base, '/history/action', {'id': 'fixture-pause', 'action': 'repeat'})[0] == 202
        active = wait_job(base, pause_url, ('downloading',))
        assert api(base, '/pause', {'url': pause_url})[0] == 200
        assert wait_job(base, pause_url, ('paused',))['status'] == 'paused'
        stop(process)
        process, base = launch()
        restored = wait_job(base, pause_url, ('paused',))
        assert restored['status'] == 'paused'
        saved = api(base, '/get-settings')[1]
        assert all(saved[k] == v for k, v in settings.items())
        assert api(base, '/resume', {'url': pause_url})[0] == 200
        assert wait_job(base, pause_url)['status'] == 'finished'
        passed('Real pause -> process restart -> queue/settings restore -> resume completes')
        assert api(base, '/save-settings', dict(settings, speed_limit_mbps='0'))[0] == 200
        assert api(base, '/history/action', {'id': 'fixture-missing', 'action': 'repeat'})[0] == 202
        failed = wait_job(base, missing)
        assert failed['status'] == 'error' and failed.get('error'), failed
        assert api(base, '/progress')[1]['status'] != 'finished_all'
        passed('Actual HTTP 404 stays failed instead of reporting all downloads successful')
        code, diagnostic = api(base, '/diagnostics', {'url': missing})
        assert code == 200 and diagnostic['count'] > 0
        assert missing not in diagnostic['text'] and str(BASE) not in diagnostic['text']
        assert 'Cookie:' not in diagnostic['text'] and 'Authorization:' not in diagnostic['text']
        passed('Installed error report is available and excludes raw URL, local path and session headers')
        REPORT['status'] = 'passed'
        passed('All installed-runtime acceptance checks completed')
    except BaseException as error:
        REPORT['status'] = 'failed'
        REPORT['error'] = str(error)
        (BASE / 'result.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
        raise
    finally:
        if process is not None:
            stop(process)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, help='Explicit packaged executable; default is installed production app')
    parser.add_argument('--result-dir', type=Path, help='New isolated result directory')
    args = parser.parse_args()
    if args.exe:
        EXE = args.exe.resolve()
        REPORT['scope'] = 'Explicit frozen EXE; isolated profile; synthetic localhost media'
    if args.result_dir:
        BASE = args.result_dir.resolve()
        PROFILE, OUTPUT = BASE / 'profile', BASE / 'output'
    REPORT['executable'] = str(EXE)
    main()
