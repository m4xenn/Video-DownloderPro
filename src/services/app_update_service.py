"""GitHub Releases application updates. Never accept executable URLs from the UI."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

from packaging.version import Version, InvalidVersion

INSTALLER_NAME = 'VideoDownloaderPro_Setup.exe'
MAX_INSTALLER_BYTES = 512 * 1024 * 1024


def _request(url):
    return urllib.request.Request(url, headers={
        'User-Agent': 'VideoDownloaderPro-Updater',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    })


def _asset_url(url, repo, tag):
    parsed = urllib.parse.urlsplit(url)
    prefix = f'/{repo}/releases/download/{urllib.parse.quote(tag, safe="")}/'
    return (parsed.scheme == 'https' and parsed.netloc == 'github.com'
            and parsed.path.startswith(prefix) and not parsed.query and not parsed.fragment
            and parsed.path.rsplit('/', 1)[-1] == INSTALLER_NAME)


def check_app_update(repo, current_version):
    base = {'current_version': current_version, 'update_available': False}
    try:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise ValueError('Geçersiz yayın deposu.')
        current = Version(current_version)
        with urllib.request.urlopen(_request(f'https://api.github.com/repos/{repo}/releases/latest'), timeout=10) as response:
            release = json.loads(response.read(2 * 1024 * 1024))
        tag = release.get('tag_name', '')
        latest = Version(tag)
        if release.get('draft') or release.get('prerelease') or latest.is_prerelease or latest.is_devrelease:
            return dict(base, status='up_to_date')
        if latest <= current:
            return dict(base, status='up_to_date', latest_version=tag)
        asset = next((a for a in release.get('assets', []) if a.get('name') == INSTALLER_NAME), None)
        if not asset or not _asset_url(asset.get('browser_download_url', ''), repo, tag):
            raise ValueError('Yeni sürümün kurulum dosyası henüz hazır değil.')
        digest = asset.get('digest') or ''
        if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}', digest):
            raise ValueError('Kurulum dosyasının SHA-256 doğrulama bilgisi eksik.')
        size = asset.get('size')
        if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_INSTALLER_BYTES:
            raise ValueError('Geçersiz kurulum dosyası boyutu.')
        return dict(base, status='available', update_available=True, latest_version=tag,
                    release_notes=release.get('body') or '', download_url=asset['browser_download_url'],
                    sha256=digest.split(':', 1)[1].lower(), size=size)
    except urllib.error.HTTPError as exc:
        message = 'Yayımlanmış sürüm bulunamadı veya depoya erişilemiyor.' if exc.code == 404 else 'Güncelleme sunucusuna erişilemiyor. Daha sonra tekrar deneyin.'
    except (InvalidVersion, ValueError, TypeError, KeyError) as exc:
        message = f'Güncelleme bilgisi doğrulanamadı: {exc}'
    except Exception:
        message = 'Güncelleme kontrol edilemedi. İnternet bağlantınızı kontrol edin.'
    return dict(base, status='error', message=message)


class AppUpdater:
    def __init__(self, repo, current_version, cache_dir=None):
        self.repo = repo
        self.current_version = current_version
        self.cache_dir = Path(cache_dir) if cache_dir else Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'VideoDownloaderPro' / 'updates'
        self.lock = threading.RLock()
        self._state = {'status': 'idle', 'percent': 0}
        self._release = None
        self._installer = None

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self._state)

    def _set(self, **values):
        with self.lock:
            self._state.update(values)

    def start_download(self):
        with self.lock:
            if self._state['status'] in ('checking', 'downloading', 'installing'):
                raise ValueError('Güncelleme işlemi zaten sürüyor.')
            self._installer = None
            self._release = None
            self._state = {'status': 'checking', 'percent': 0}
            threading.Thread(target=self._download, daemon=True).start()

    def _download(self):
        part = None
        try:
            release = check_app_update(self.repo, self.current_version)
            if not release['update_available']:
                self._set(status='error', message=release.get('message', 'Yeni bir sürüm bulunmuyor.'))
                return
            # Isolate releases by digest while keeping the UAC-visible filename readable.
            release_dir = self.cache_dir / release["sha256"]
            release_dir.mkdir(parents=True, exist_ok=True)
            destination = release_dir / INSTALLER_NAME
            part = destination.with_suffix('.part')
            self._set(status='downloading', percent=0)
            digest = hashlib.sha256()
            downloaded = 0
            with urllib.request.urlopen(_request(release['download_url']), timeout=30) as response, part.open('wb') as output:
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > release['size']:
                        raise ValueError('Kurulum dosyasının boyutu beklenenden farklı.')
                    digest.update(chunk)
                    output.write(chunk)
                    self._set(percent=min(99, int(downloaded * 100 / release['size'])))
            if downloaded != release['size'] or digest.hexdigest() != release['sha256']:
                raise ValueError('Kurulum dosyası doğrulanamadı; tekrar indirin.')
            with part.open('rb') as executable:
                header = executable.read(2)
            if header != b'MZ':
                raise ValueError('Geçerli bir Windows kurulum dosyası değil.')
            os.replace(part, destination)
            with self.lock:
                self._release = release
                self._installer = destination
                self._state = {'status': 'ready', 'percent': 100, 'latest_version': release['latest_version']}
        except Exception as exc:
            self._set(status='error', message=f'Güncelleme indirilemedi: {exc}')
        finally:
            if part and part.exists():
                part.unlink(missing_ok=True)

    def launch(self):
        with self.lock:
            if not getattr(sys, 'frozen', False) or sys.platform != 'win32':
                raise ValueError('Kurulum yalnız paketlenmiş Windows uygulamasında başlatılabilir.')
            if self._state['status'] != 'ready' or not self._installer or not self._release:
                raise ValueError('Önce güncellemeyi indirin.')
            # Recheck bytes immediately before execution, including after a long pause.
            if hashlib.sha256(self._installer.read_bytes()).hexdigest() != self._release['sha256']:
                self._set(status='error', message='Kurulum dosyası değişmiş; tekrar indirin.')
                raise ValueError(self._state['message'])
            # ShellExecute handles the installer's UAC elevation prompt. CreateProcess
            # (subprocess.Popen) would fail with WinError 740 for an admin installer.
            os.startfile(str(self._installer), 'open', '/SP- /NORESTART', str(self._installer.parent))
            self._set(status='installing')
