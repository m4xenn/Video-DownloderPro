"""Offline updater contract tests; no installers are executed."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from services import app_update_service as updates
import app

REPO = 'm4xenn/Video-DownloderPro'
PAYLOAD = b'MZ' + b'test installer bytes'


def release(tag='v1.2.0'):
    return {'tag_name': tag, 'draft': False, 'prerelease': False, 'body': '<script>unsafe()</script>',
            'assets': [{'name': updates.INSTALLER_NAME, 'size': len(PAYLOAD),
                        'digest': 'sha256:' + hashlib.sha256(PAYLOAD).hexdigest(),
                        'browser_download_url': f'https://github.com/{REPO}/releases/download/{tag}/{updates.INSTALLER_NAME}'}]}


class UpdateCheckTests(unittest.TestCase):
    def check(self, data, current='v1.1.1'):
        with patch.object(updates.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(data).encode())):
            return updates.check_app_update(REPO, current)

    def test_equal_version_no_notification(self):
        self.assertEqual(self.check(release('v1.1.1'))['status'], 'up_to_date')

    def test_v_prefix_normalized(self):
        self.assertFalse(self.check(release('v1.1.1'), '1.1.1')['update_available'])

    def test_older_release_no_downgrade(self):
        self.assertFalse(self.check(release('v1.0.0'))['update_available'])

    def test_semantic_comparison(self):
        self.assertTrue(self.check(release('v1.10.0'), 'v1.9.0')['update_available'])

    def test_new_version_has_verified_installer(self):
        result = self.check(release())
        self.assertTrue(result['update_available'])
        self.assertEqual(result['size'], len(PAYLOAD))

    def test_draft_and_prerelease_excluded(self):
        for key in ('draft', 'prerelease'):
            data = release()
            data[key] = True
            self.assertFalse(self.check(data)['update_available'])
        self.assertFalse(self.check(release('v2.0.0rc1'))['update_available'])

    def test_missing_asset_is_error(self):
        data = release()
        data['assets'] = []
        self.assertEqual(self.check(data)['status'], 'error')

    def test_missing_digest_is_error(self):
        data = release()
        data['assets'][0].pop('digest')
        self.assertEqual(self.check(data)['status'], 'error')

    def test_wrong_repository_asset_rejected(self):
        data = release()
        data['assets'][0]['browser_download_url'] = 'https://github.com/other/repo/releases/download/v1.2.0/VideoDownloaderPro_Setup.exe'
        self.assertEqual(self.check(data)['status'], 'error')

    def test_invalid_version_is_error(self):
        self.assertEqual(self.check(release('not-a-version'))['status'], 'error')

    def test_offline_is_error_not_up_to_date(self):
        with patch.object(updates.urllib.request, 'urlopen', side_effect=urllib.error.URLError('offline')):
            result = updates.check_app_update(REPO, 'v1.1.1')
        self.assertEqual(result['status'], 'error')
        self.assertFalse(result['update_available'])

    def test_rate_limit_is_error(self):
        with patch.object(updates.urllib.request, 'urlopen', side_effect=urllib.error.HTTPError('', 403, 'limit', {}, None)):
            self.assertEqual(updates.check_app_update(REPO, 'v1.1.1')['status'], 'error')


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.updater = updates.AppUpdater(REPO, 'v1.1.1', self.temp.name)
        asset = release()['assets'][0]
        self.info = {'update_available': True, 'latest_version': 'v1.2.0', 'download_url': asset['browser_download_url'],
                     'size': len(PAYLOAD), 'sha256': hashlib.sha256(PAYLOAD).hexdigest()}

    def download(self, payload=PAYLOAD):
        with patch.object(updates, 'check_app_update', return_value=self.info), \
             patch.object(updates.urllib.request, 'urlopen', return_value=io.BytesIO(payload)):
            self.updater._download()

    def test_verified_download_ready(self):
        self.download()
        self.assertEqual(self.updater.snapshot()['status'], 'ready')
        self.assertEqual(self.updater._installer.read_bytes(), PAYLOAD)

    def test_corrupt_download_removed(self):
        self.download(b'MZ' + b'bad bytes')
        self.assertEqual(self.updater.snapshot()['status'], 'error')
        self.assertFalse(list(Path(self.temp.name).iterdir()))

    def test_oversized_download_rejected(self):
        self.download(PAYLOAD * 2)
        self.assertEqual(self.updater.snapshot()['status'], 'error')

    def test_non_executable_rejected(self):
        payload = b'not an executable'
        self.info.update(size=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        self.download(payload)
        self.assertEqual(self.updater.snapshot()['status'], 'error')

    def test_concurrent_start_rejected(self):
        self.updater._set(status='downloading')
        with self.assertRaises(ValueError):
            self.updater.start_download()

    def test_source_mode_cannot_execute(self):
        self.download()
        with patch.object(updates.os, 'startfile') as process:
            with self.assertRaises(ValueError):
                self.updater.launch()
            process.assert_not_called()

    def test_tampered_ready_file_cannot_execute(self):
        self.download()
        self.updater._installer.write_bytes(b'altered')
        with patch.object(sys, 'frozen', True, create=True), patch.object(updates.os, 'startfile') as process:
            with self.assertRaises(ValueError):
                self.updater.launch()
            process.assert_not_called()

    def test_install_only_once(self):
        self.download()
        with patch.object(sys, 'frozen', True, create=True), patch.object(updates.os, 'startfile') as process:
            self.updater.launch()
            self.assertEqual(self.updater.snapshot()['status'], 'installing')
            with self.assertRaises(ValueError):
                self.updater.launch()
            process.assert_called_once()


class UpdateRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_active_media_blocks_install(self):
        with patch.object(app, 'media_download_active', return_value=True), patch.object(app.app_updater, 'launch') as launch:
            self.assertEqual(self.client.post('/app-update/install', json={}).status_code, 409)
            launch.assert_not_called()

    def test_browser_mode_blocks_install(self):
        with patch.object(app, 'media_download_active', return_value=False), patch.object(app.webview, 'windows', []):
            self.assertEqual(self.client.post('/app-update/install', json={}).status_code, 409)

    def test_cross_site_install_rejected(self):
        self.assertEqual(self.client.post('/app-update/install', json={}, headers={'Origin': 'https://other.example'}).status_code, 403)

    def test_form_post_rejected(self):
        self.assertEqual(self.client.post('/app-update/install', data={}).status_code, 403)

    def test_download_does_not_accept_client_url(self):
        with patch.object(app.app_updater, 'start_download') as start:
            response = self.client.post('/app-update/download', json={'url': 'https://other.example/malware.exe'})
            self.assertEqual(response.status_code, 202)
            start.assert_called_once_with()

    def test_metadata_in_ui(self):
        page = self.client.get('/').get_data(as_text=True)
        self.assertIn(app.CURRENT_VERSION, page)
        self.assertIn("getElementById('appUpdateNotes').textContent", page)


if __name__ == '__main__':
    unittest.main()
