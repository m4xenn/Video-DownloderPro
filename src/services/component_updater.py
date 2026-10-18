"""Version-aware, asynchronous updates for the actual Python engine and FFmpeg."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import urllib.request
import zipfile

from packaging.version import Version
from services.component_runtime import BIN_DIR, read_manifest, verified_engine, runtime_version

SOURCES = {
    'yt-dlp': ('yt-dlp/yt-dlp', 'yt-dlp', 20 * 1024 * 1024),
    'ffmpeg': ('BtbN/FFmpeg-Builds', 'ffmpeg-master-latest-win64-gpl.zip', 512 * 1024 * 1024),
}


def ffmpeg_version(bin_dir):
    executable = Path(bin_dir) / 'ffmpeg.exe'
    if not executable.is_file():
        return None
    try:
        result = subprocess.run([str(executable), '-version'], capture_output=True, text=True,
                                timeout=5, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode == 0:
            return result.stdout.splitlines()[0].split('version ', 1)[1].split(' Copyright', 1)[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        pass
    return None


def component_status(bin_dir=BIN_DIR):
    engine = runtime_version()
    ffmpeg = ffmpeg_version(bin_dir)
    ready = bool(engine and ffmpeg and (Path(bin_dir) / 'ffprobe.exe').is_file())
    manifest = read_manifest(bin_dir)
    pending = manifest.get('yt-dlp', {}).get('version')
    try:
        restart = bool(pending and Version(pending) > Version(engine or '0') and verified_engine(bin_dir))
    except ValueError:
        restart = False
    return {'ready': ready, 'yt_dlp_version': engine, 'ffmpeg_version': ffmpeg,
            'restart_required': restart, 'pending_version': pending if restart else None}


def remote_release(component):
    repo, name, maximum = SOURCES[component]
    request = urllib.request.Request(f'https://api.github.com/repos/{repo}/releases/latest',
                                     headers={'User-Agent': 'VideoDownloaderPro-Components', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.loads(response.read(2 * 1024 * 1024))
    if data.get('draft') or data.get('prerelease'):
        raise ValueError('Kararlı bileşen sürümü bulunamadı.')
    asset = next((a for a in data.get('assets', []) if a.get('name') == name), None)
    if not asset:
        raise ValueError(f'{component} dağıtım dosyası bulunamadı.')
    digest = asset.get('digest') or ''
    size = asset.get('size')
    if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
        raise ValueError(f'{component} SHA-256 bilgisi bulunamadı.')
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= maximum:
        raise ValueError('Geçersiz bileşen boyutu.')
    # Only use the configured upstream release's exact asset, never a UI-supplied URL.
    from urllib.parse import quote
    url = f'https://github.com/{repo}/releases/download/{quote(data["tag_name"], safe="")}/{name}'
    if asset.get('browser_download_url') != url:
        raise ValueError('Bileşen indirme adresi doğrulanamadı.')
    return {'component': component, 'version': data['tag_name'], 'label': data.get('name') or data['tag_name'],
            'url': url, 'sha256': digest.split(':')[1].lower(), 'size': size}


class ComponentUpdater:
    def __init__(self, bin_dir=BIN_DIR):
        self.bin_dir = Path(bin_dir)
        self.lock = threading.RLock()
        self._state = {'status': 'idle', 'percent': 0, 'components': []}
        self._plan = []

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self._state)

    def _set(self, **values):
        with self.lock:
            self._state.update(values)

    def start_check(self):
        with self.lock:
            if self._state['status'] in ('checking', 'downloading'):
                raise ValueError('Bileşen işlemi zaten sürüyor.')
            self._state = {'status': 'checking', 'percent': 0, 'components': [], 'message': 'Sürümler kontrol ediliyor...'}
            self._plan = []
            threading.Thread(target=self._check, daemon=True).start()

    def _check(self):
        try:
            local = component_status(self.bin_dir)
            manifest = read_manifest(self.bin_dir)
            components, plan = [], []
            for name in SOURCES:
                remote = remote_release(name)
                verification_required = False
                if name == 'yt-dlp':
                    effective = local['pending_version'] or local['yt_dlp_version'] or '0'
                    needs_update = Version(remote['version']) > Version(effective)
                    installed = local['yt_dlp_version']
                else:
                    installed = local['ffmpeg_version']
                    verification_required = bool(installed and (self.bin_dir / 'ffprobe.exe').is_file()
                                                 and not manifest.get(name, {}).get('sha256'))
                    needs_update = (not installed or not (self.bin_dir / 'ffprobe.exe').is_file()
                                    or manifest.get(name, {}).get('sha256') != remote['sha256'])
                components.append({'name': name, 'installed': installed or 'Kurulu değil',
                                   'latest': remote['label'], 'update_available': needs_update and not verification_required,
                                   'verification_required': verification_required,
                                   'pending': name == 'yt-dlp' and local['restart_required'],
                                   'untracked': verification_required})
                if needs_update:
                    plan.append(remote)
            with self.lock:
                self._plan = plan
                self._state = {'status': 'available' if plan else 'up_to_date', 'components': components,
                               'percent': 0, 'restart_required': local['restart_required'],
                               'verification_only': bool(plan) and not any(row['update_available'] for row in components),
                               'message': ('Mevcut kurulumun doğrulama kaydı yok. Daha yeni bir FFmpeg sürümü olduğu doğrulanmadı.'
                                           if plan and not any(row['update_available'] for row in components)
                                           else 'Yeni bileşen dağıtımı mevcut.' if plan else 'Bileşenler güncel.')}
        except Exception as exc:
            self._set(status='error', message=f'Bileşen sürümleri kontrol edilemedi: {exc}')

    def start_download(self):
        with self.lock:
            if self._state['status'] != 'available' or not self._plan:
                raise ValueError('Önce bileşen güncellemelerini kontrol edin.')
            self._set(status='downloading', percent=0, message='İndirme hazırlanıyor...')
            threading.Thread(target=self._download, daemon=True).start()

    def _save_manifest(self, manifest):
        temporary = self.bin_dir / 'components.json.tmp'
        temporary.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        os.replace(temporary, self.bin_dir / 'components.json')

    def _download_asset(self, asset, path):
        request = urllib.request.Request(asset['url'], headers={'User-Agent': 'VideoDownloaderPro-Components'})
        digest, received = hashlib.sha256(), 0
        with urllib.request.urlopen(request, timeout=30) as response, path.open('wb') as output:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                if received > asset['size']:
                    raise ValueError('Beklenmeyen dosya boyutu.')
                digest.update(chunk)
                output.write(chunk)
                self._set(percent=min(99, received * 100 // asset['size']), downloaded=received, total=asset['size'])
        if received != asset['size'] or digest.hexdigest() != asset['sha256']:
            raise ValueError('İndirilen dosyanın SHA-256 doğrulaması başarısız.')

    def _install_ffmpeg(self, archive_path, stage):
        extracted = []
        with zipfile.ZipFile(archive_path) as archive:
            for name in ('ffmpeg.exe', 'ffprobe.exe'):
                matches = [entry for entry in archive.infolist() if entry.filename.rsplit('/', 1)[-1] == name]
                if len(matches) != 1 or matches[0].file_size > 400 * 1024 * 1024:
                    raise ValueError(f'{name} arşivde bulunamadı veya geçersiz.')
                target = stage / name
                with archive.open(matches[0]) as source, target.open('wb') as destination:
                    shutil.copyfileobj(source, destination)
                with target.open('rb') as source:
                    if source.read(2) != b'MZ':
                        raise ValueError('Geçersiz FFmpeg dosyası.')
                extracted.append(name)
        if not ffmpeg_version(stage):
            raise ValueError('Yeni FFmpeg çalıştırılamadı.')
        replaced, backups = [], []
        try:
            for name in extracted:
                target = self.bin_dir / name
                if target.exists():
                    os.replace(target, stage / (name + '.backup'))
                    backups.append(name)
                os.replace(stage / name, target)
                replaced.append(name)
        except Exception:
            for name in reversed(replaced):
                (self.bin_dir / name).unlink(missing_ok=True)
            for name in backups:
                os.replace(stage / (name + '.backup'), self.bin_dir / name)
            raise

    def _download(self):
        try:
            self.bin_dir.mkdir(parents=True, exist_ok=True)
            for index, asset in enumerate(self._plan, 1):
                self._set(component=asset['component'], percent=0, downloaded=0, total=asset['size'],
                          message=f'{asset["component"]} indiriliyor ({index}/{len(self._plan)})...')
                with tempfile.TemporaryDirectory(dir=self.bin_dir) as directory:
                    stage = Path(directory)
                    archive = stage / 'download.zip'
                    self._download_asset(asset, archive)
                    manifest = read_manifest(self.bin_dir)
                    record = {'version': asset['version'], 'sha256': asset['sha256']}
                    if asset['component'] == 'yt-dlp':
                        with zipfile.ZipFile(archive) as package:
                            if not {'yt_dlp/__init__.py', 'yt_dlp/version.py'}.issubset(package.namelist()):
                                raise ValueError('Geçersiz yt-dlp Python dağıtımı.')
                        name = f'yt-dlp-{asset["sha256"]}.zip'
                        os.replace(archive, self.bin_dir / name)
                        record['file'] = name
                    else:
                        self._install_ffmpeg(archive, stage)
                    manifest[asset['component']] = record
                    self._save_manifest(manifest)
            local = component_status(self.bin_dir)
            rows = self.snapshot().get('components', [])
            for row in rows:
                row['update_available'] = False
                row['untracked'] = False
                row['verification_required'] = False
                row['pending'] = row['name'] == 'yt-dlp' and local['restart_required']
                row['installed'] = local['yt_dlp_version'] if row['name'] == 'yt-dlp' else local['ffmpeg_version']
            self._set(status='finished', percent=100, restart_required=local['restart_required'],
                      components=rows,
                      message='Bileşenler doğrulandı ve güncellendi.' + (' Yeni yt-dlp sürümü için uygulamayı kapatıp yeniden açın.' if local['restart_required'] else ''))
        except Exception as exc:
            self._set(status='error', message=f'Bileşen güncellemesi tamamlanamadı: {exc}')
