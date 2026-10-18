"""Isolated component update tests. No remote downloads or real bin changes."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from services import component_updater as components
from services import component_runtime as runtime
import app


def engine_zip():
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        archive.writestr('yt_dlp/__init__.py', '')
        archive.writestr('yt_dlp/version.py', "__version__ = '2027.01.01'")
    return data.getvalue()


def remote(name, data=b'data'):
    return {'component': name, 'version': '2027.01.01' if name == 'yt-dlp' else 'latest',
            'label': 'New build', 'url': 'https://github.com/test/asset',
            'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)}


class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.updater = components.ComponentUpdater(self.folder)
        self.local = {'ready': True, 'yt_dlp_version': '2026.08.19', 'ffmpeg_version': 'old',
                      'pending_version': None, 'restart_required': False}

    def check(self, ffmpeg_managed=True):
        (self.folder / 'ffprobe.exe').write_bytes(b'MZold')
        manifest = {'ffmpeg': {'version': 'latest', 'sha256': remote('ffmpeg')['sha256']}} if ffmpeg_managed else {}
        with patch.object(components, 'component_status', return_value=self.local), \
             patch.object(components, 'read_manifest', return_value=manifest), \
             patch.object(components, 'remote_release', side_effect=lambda name: remote(name)):
            self.updater._check()
        return self.updater.snapshot()

    def test_only_outdated_engine_planned(self):
        result = self.check()
        self.assertEqual(result['status'], 'available')
        self.assertEqual([a['component'] for a in self.updater._plan], ['yt-dlp'])

    def test_same_versions_no_download(self):
        self.local['yt_dlp_version'] = '2027.01.01'
        self.assertEqual(self.check()['status'], 'up_to_date')

    def test_no_engine_downgrade(self):
        self.local['yt_dlp_version'] = '2028.01.01'
        self.assertEqual(self.check()['status'], 'up_to_date')

    def test_pending_engine_not_downloaded_twice(self):
        self.local.update(pending_version='2027.01.01', restart_required=True)
        result = self.check()
        self.assertEqual(result['status'], 'up_to_date')
        self.assertTrue(result['restart_required'])

    def test_untracked_ffmpeg_explained(self):
        result = self.check(False)
        self.assertTrue(result['components'][1]['untracked'])
        self.assertFalse(result['components'][1]['update_available'])
        self.assertTrue(result['components'][1]['verification_required'])

    def test_verification_only_does_not_claim_new_version(self):
        self.local['yt_dlp_version'] = '9999.1'
        result = self.check(False)
        self.assertTrue(result['verification_only'])
        self.assertFalse(any(row['update_available'] for row in result['components']))
        self.assertIn('Daha yeni bir FFmpeg sürümü olduğu doğrulanmadı', result['message'])
        self.assertEqual([item['component'] for item in self.updater._plan], ['ffmpeg'])

    def test_offline_error(self):
        with patch.object(components, 'component_status', return_value=self.local), \
             patch.object(components, 'remote_release', side_effect=OSError('offline')):
            self.updater._check()
        self.assertEqual(self.updater.snapshot()['status'], 'error')

    def test_download_requires_check(self):
        with self.assertRaises(ValueError):
            self.updater.start_download()

    def test_duplicate_check_blocked(self):
        self.updater._set(status='checking')
        with self.assertRaises(ValueError):
            self.updater.start_check()

    def test_corrupt_download_rejected(self):
        asset = remote('yt-dlp', b'good')
        with patch.object(components.urllib.request, 'urlopen', return_value=io.BytesIO(b'evil')):
            with self.assertRaises(ValueError):
                self.updater._download_asset(asset, self.folder / 'bad.zip')

    def test_verified_download_progress(self):
        payload = engine_zip()
        asset = remote('yt-dlp', payload)
        with patch.object(components.urllib.request, 'urlopen', return_value=io.BytesIO(payload)):
            self.updater._download_asset(asset, self.folder / 'engine.zip')
        self.assertEqual(self.updater.snapshot()['downloaded'], len(payload))

    def test_engine_staged_and_verified(self):
        payload = engine_zip()
        self.updater._plan = [remote('yt-dlp', payload)]
        local = dict(self.local, restart_required=True, pending_version='2027.01.01')
        with patch.object(components.urllib.request, 'urlopen', return_value=io.BytesIO(payload)), \
             patch.object(components, 'component_status', return_value=local):
            self.updater._download()
        self.assertEqual(self.updater.snapshot()['status'], 'finished')
        self.assertTrue(self.updater.snapshot()['restart_required'])
        self.assertIsNotNone(runtime.verified_engine(self.folder))

    def test_tampered_engine_not_loaded(self):
        payload = engine_zip()
        file = self.folder / 'yt-dlp-test.zip'
        file.write_bytes(payload)
        (self.folder / 'components.json').write_text(json.dumps({'yt-dlp': {
            'version': '2027.01.01', 'file': file.name, 'sha256': '0' * 64}}))
        self.assertIsNone(runtime.verified_engine(self.folder))

    def test_invalid_manifest_falls_back(self):
        (self.folder / 'components.json').write_text('{')
        self.assertEqual(runtime.read_manifest(self.folder), {})

    def test_startup_selects_newer_verified_python_engine(self):
        old_paths = sys.path[:]
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), old_paths))
        with patch.object(runtime, 'verified_engine', return_value=self.folder / 'engine.zip'), \
             patch.object(runtime, 'read_manifest', return_value={'yt-dlp': {'version': '2027.01.01'}}), \
             patch.object(runtime.importlib.metadata, 'version', return_value='2026.08.19'):
            runtime.activate_engine()
        self.assertEqual(sys.path[0], str(self.folder / 'engine.zip'))

    def test_new_app_bundled_engine_not_downgraded(self):
        previous = sys.path[:]
        with patch.object(runtime, 'verified_engine', return_value=self.folder / 'engine.zip'), \
             patch.object(runtime, 'read_manifest', return_value={'yt-dlp': {'version': '2025.01.01'}}), \
             patch.object(runtime.importlib.metadata, 'version', return_value='2026.08.19'):
            runtime.activate_engine()
        self.assertEqual(sys.path, previous)

    def test_ffmpeg_archive_requires_both_executables(self):
        package = self.folder / 'bad.zip'
        with zipfile.ZipFile(package, 'w') as archive:
            archive.writestr('bin/ffmpeg.exe', b'MZnew')
        with self.assertRaises(ValueError):
            self.updater._install_ffmpeg(package, self.folder)

    def test_ffmpeg_rollback_on_replace_failure(self):
        stage = self.folder / 'stage'
        stage.mkdir()
        package = stage / 'ffmpeg.zip'
        with zipfile.ZipFile(package, 'w') as archive:
            for name in ('ffmpeg.exe', 'ffprobe.exe'):
                archive.writestr('bin/' + name, b'MZnew')
                (self.folder / name).write_bytes(b'MZold')
        real_replace = components.os.replace
        def replace(source, target):
            if Path(source) == stage / 'ffprobe.exe' and Path(target) == self.folder / 'ffprobe.exe':
                raise PermissionError('busy')
            return real_replace(source, target)
        with patch.object(components, 'ffmpeg_version', return_value='new'), \
             patch.object(components.os, 'replace', side_effect=replace):
            with self.assertRaises(PermissionError):
                self.updater._install_ffmpeg(package, stage)
        for name in ('ffmpeg.exe', 'ffprobe.exe'):
            self.assertEqual((self.folder / name).read_bytes(), b'MZold')


class ComponentRouteTests(unittest.TestCase):
    def test_update_blocked_during_media(self):
        with patch.object(app, 'media_download_active', return_value=True), patch.object(app.component_updater, 'start_download') as start:
            self.assertEqual(app.app.test_client().post('/update-components', json={}).status_code, 409)
            start.assert_not_called()

    def test_check_cross_site_blocked(self):
        response = app.app.test_client().post('/components/check', json={}, headers={'Origin': 'https://other.example'})
        self.assertEqual(response.status_code, 403)

    def test_check_only_never_downloads(self):
        with patch.object(app.component_updater, 'start_check') as check, \
             patch.object(app.component_updater, 'start_download') as download:
            self.assertEqual(app.app.test_client().post('/components/check', json={}).status_code, 202)
            check.assert_called_once()
            download.assert_not_called()


if __name__ == '__main__':
    unittest.main()
