"""Explicit production-upgrade preparation and verification; never publishes.

Backup manifests and private user state stay under ignored build/. Run backup
before launch-installer, then verify after the user approves Windows elevation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import winreg

import psutil

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'version.json').read_text(encoding='utf-8'))['version']
BASE = ROOT / 'build' / 'real-upgrade-1.2.13'
INSTALL = Path(os.environ['ProgramFiles(x86)']) / 'Studio Downloader'
PROFILE = Path(os.environ['APPDATA']) / 'YoutubePro'
KEY = r'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Studio Downloader_is1'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def registration():
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, KEY) as key:
        return {name: winreg.QueryValueEx(key, name)[0]
                for name in ('DisplayVersion', 'InstallLocation', 'UninstallString')}


def profile_files():
    return [p for p in PROFILE.rglob('*') if p.is_file()
            and p.relative_to(PROFILE).parts[0] not in ('bin', 'previews')]


def no_running_app():
    for process in psutil.process_iter(['name', 'exe']):
        if (process.info['name'] or '').lower() == 'youtubepro.exe':
            raise RuntimeError('Close Video Downloader Pro before preparing or verifying the upgrade.')


def installer():
    release = ROOT / 'releases' / ('v' + VERSION)
    info = json.loads((release / 'release-info.json').read_text(encoding='utf-8'))
    exe = release / info['installer']
    assert digest(exe) == info['sha256'], 'Installer SHA-256 mismatch'
    assert exe.stat().st_size == info['size'], 'Installer size mismatch'
    return exe


def backup():
    no_running_app()
    manifest = BASE / 'backup-manifest.json'
    assert not manifest.exists(), 'Existing backup is preserved; inspect before repeating.'
    BASE.mkdir(parents=True, exist_ok=True)
    before = registration()
    assert before['DisplayVersion'] == '1.2.8', before['DisplayVersion']
    entries = []
    for source in profile_files():
        relative = source.relative_to(PROFILE)
        target = BASE / 'backup' / 'profile' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        value = digest(source)
        assert digest(target) == value
        entries.append({'path': str(relative), 'sha256': value, 'size': source.stat().st_size})
    for name in ('settings.json', 'history.json', 'folders.json'):
        source = INSTALL / name
        if source.exists():
            target = BASE / 'backup' / 'legacy' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    data = {'created_at': datetime.now(timezone.utc).isoformat(), 'registration': before,
            'profile': entries, 'excluded': ['bin (unchanged by application setup)', 'previews (cache)'],
            'old_installer_available': (ROOT / 'releases/v1.2.8/VideoDownloaderPro_Setup.exe').is_file(),
            'installer_sha256': digest(installer())}
    manifest.write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(json.dumps({'backup': str(BASE / 'backup'), 'profile_files': len(entries),
                      'backup_bytes': sum(p['size'] for p in entries),
                      'current_version': before['DisplayVersion'], 'installer_verified': True}))


def launch_installer():
    no_running_app()
    assert (BASE / 'backup-manifest.json').is_file(), 'Verified backup required'
    for item in json.loads((BASE / 'backup-manifest.json').read_text(encoding='utf-8'))['profile']:
        assert digest(BASE / 'backup/profile' / item['path']) == item['sha256']
    # ShellExecute opens the normal Windows UAC prompt; the user approves it.
    os.startfile(str(installer()), 'open', '/SP- /NORESTART /VERYSILENT /SUPPRESSMSGBOXES /TASKS="desktopicon" /LOG="' + str(BASE / ('production-install-' + VERSION + '.log')) + '"')
    print('Production installer launched. Windows elevation must be approved by the user.')


def verify():
    no_running_app()
    before = json.loads((BASE / 'backup-manifest.json').read_text(encoding='utf-8'))
    after = registration()
    assert after['DisplayVersion'] == VERSION, after['DisplayVersion']
    assert Path(after['InstallLocation']).resolve() == INSTALL.resolve()
    files = [p for p in (ROOT / 'dist/YoutubePro').rglob('*') if p.is_file()]
    for source in files:
        target = INSTALL / source.relative_to(ROOT / 'dist/YoutubePro')
        assert target.is_file() and digest(target) == digest(source), str(target)
    preserved = []
    for item in before['profile']:
        source = PROFILE / item['path']
        assert source.is_file() and digest(source) == item['sha256'], 'User state changed during setup: ' + item['path']
        preserved.append(item['path'])
    result = {'status': 'passed', 'previous_version': before['registration']['DisplayVersion'],
              'installed_version': after['DisplayVersion'], 'installed_files_verified': len(files),
              'profile_files_preserved': len(preserved), 'installer_sha256': digest(installer()),
              'scope': 'Actual production installer and existing Windows install; before first app launch.'}
    (BASE / 'production-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('backup', 'launch-installer', 'verify'))
    args = parser.parse_args()
    {'backup': backup, 'launch-installer': launch_installer, 'verify': verify}[args.action]()
