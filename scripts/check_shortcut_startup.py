"""Check real installed shortcuts and first launch; keep private state in build/."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import time
import urllib.error
import urllib.request

import psutil
import win32com.client

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'build/real-upgrade-1.2.14'
INSTALL = Path(os.environ['ProgramFiles(x86)']) / 'Studio Downloader'
PROFILE = Path(os.environ['APPDATA']) / 'YoutubePro'


def data_snapshot():
    with sqlite3.connect((PROFILE / 'downloads.sqlite3').resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        history = [dict(row) for row in db.execute('SELECT * FROM history ORDER BY id')]
        states = {row['name']: json.loads(row['payload']) for row in db.execute('SELECT * FROM state')}
    return {'settings': json.loads((PROFILE / 'settings.json').read_text(encoding='utf-8')),
            'history': history, 'states': states}


def get(base, route):
    with urllib.request.urlopen(base + route, timeout=20) as response:
        return json.load(response)


def launch():
    assert not any((p.info['name'] or '').lower() == 'youtubepro.exe'
                   for p in psutil.process_iter(['name']))
    assert json.loads((INSTALL / '_internal/version.json').read_text())['version'] == '1.2.14'
    BASE.mkdir(parents=True, exist_ok=True)
    shell = win32com.client.Dispatch('WScript.Shell')
    roots = [(name, Path(shell.SpecialFolders.Item(name)))
             for name in ('Desktop', 'AllUsersDesktop', 'Programs', 'AllUsersPrograms')]
    links = []
    for kind, folder in roots:
        for path in folder.rglob('*Video Downloader Pro*.lnk'):
            shortcut = shell.CreateShortcut(str(path))
            target = Path(shortcut.TargetPath)
            if target.name.lower() == 'youtubepro.exe':
                assert target.resolve() == (INSTALL / 'YoutubePro.exe').resolve()
                assert target.is_file()
                links.append({'kind': kind, 'path': str(path), 'target': str(target)})
    assert any(row['kind'] in ('Programs', 'AllUsersPrograms') for row in links), 'Start-menu shortcut missing'
    desktop = next((row for row in links if row['kind'] in ('Desktop', 'AllUsersDesktop')), None)
    assert desktop, 'Desktop shortcut missing'
    (BASE / 'personal-before-startup.json').write_text(json.dumps(data_snapshot()), encoding='utf-8')
    os.startfile(desktop['path'])
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        for process in psutil.process_iter(['name', 'exe']):
            if (process.info['name'] or '').lower() != 'youtubepro.exe':
                continue
            if Path(process.info['exe']).resolve() != (INSTALL / 'YoutubePro.exe').resolve():
                continue
            for connection in process.net_connections(kind='tcp'):
                if connection.status == psutil.CONN_LISTEN and connection.laddr.ip == '127.0.0.1':
                    url = 'http://127.0.0.1:' + str(connection.laddr.port)
                    with urllib.request.urlopen(url, timeout=5) as response:
                        assert '1.2.14' in response.read().decode('utf-8')
                    progress = get(url, '/progress')
                    assert not any(row['status'] in ('starting', 'downloading', 'converting', 'retry_wait')
                                   for row in progress['items']), 'Restored work started unexpectedly'
                    result = {'status': 'passed', 'installed_version': '1.2.14', 'pid': process.pid,
                              'url': url, 'shortcut_count': len(links), 'desktop_link_opened': True,
                              'start_menu_verified': True, 'no_unexpected_downloads': True}
                    (BASE / 'shortcut-startup.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
                    print(json.dumps({k: v for k, v in result.items() if k != 'url'}, indent=2))
                    return
        time.sleep(.3)
    raise RuntimeError('Desktop shortcut did not open the expected application')


def verify_data():
    before = json.loads((BASE / 'personal-before-startup.json').read_text(encoding='utf-8'))
    after = data_snapshot()
    assert before['history'] == after['history'], 'History changed unexpectedly during startup'
    assert all(after['settings'].get(key) == value for key, value in before['settings'].items()), 'Saved preferences changed'
    old_drafts = {row['url'] for row in before['states'].get('drafts', [])}
    new_drafts = {row['url'] for row in after['states'].get('drafts', [])}
    assert old_drafts <= new_drafts, 'Draft queue lost an entry'
    new_jobs = {row['id']: row for row in after['states'].get('queue', [])}
    old_jobs = [row for row in before['states'].get('queue', []) if row['status'] not in ('finished', 'expanded')]
    for row in old_jobs:
        recovered = new_jobs[row['id']]
        for field in ('url', 'path', 'options'):
            assert row[field] == recovered[field], 'Restored queue data changed'
    result = {'status': 'passed', 'settings_preserved': True, 'history_preserved': True,
              'drafts_preserved': True, 'paused_queue_preserved': True, 'sqlite_integrity': 'ok',
              'application_closed': not any((p.info['name'] or '').lower() == 'youtubepro.exe'
                                            for p in psutil.process_iter(['name']))}
    (BASE / 'personal-startup-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('launch', 'verify-data'))
    args = parser.parse_args()
    {'launch': launch, 'verify-data': verify_data}[args.action]()
