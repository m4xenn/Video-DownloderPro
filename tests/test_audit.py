"""Offline regression checks. Run: python -m unittest discover -s tests -p test_audit.py -v

No internet, browser cookies, or real settings writes.
"""
import copy
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import app as application
from core import queue_manager, downloader
from core.format_resolver import get_ydl_opts
from state.app_state import state


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.saved = copy.deepcopy(state)
        state.update(current_download_path='', current_lang='tr', cancel_flags={},
                     download_status={'status': 'idle', 'error': '', 'items': [], 'total_items': 0})
        self.client = application.app.test_client()

    def tearDown(self):
        state.clear()
        state.update(self.saved)

    def test_home_renders(self):
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_progress_initially_idle(self):
        self.assertEqual(self.client.get('/progress').json['status'], 'idle')

    def test_missing_destination_rejected(self):
        self.assertEqual(self.client.post('/download', json={'urls': ['https://youtube.com/watch?v=test']}).status_code, 400)

    def test_empty_queue_rejected(self):
        state['current_download_path'] = str(ROOT)
        self.assertEqual(self.client.post('/download', json={'urls': []}).status_code, 400)

    def test_missing_url_info_rejected(self):
        self.assertEqual(self.client.post('/get-info', json={}).json['status'], 'error')

    def test_pause_hook(self):
        url = 'https://youtube.com/watch?v=test'
        state['cancel_flags'][url] = True
        state['download_status']['items'] = [{'url': url}]
        with self.assertRaisesRegex(Exception, 'DOWNLOAD_PAUSED'):
            downloader.progress_hook({'status': 'downloading', 'info_dict': {'webpage_url': url}})
        self.assertEqual(state['download_status']['items'][0]['status'], 'paused')

    def test_progress_percentage(self):
        state['download_status']['items'] = [{'url': 'sample'}]
        downloader.progress_hook({'status': 'downloading', 'info_dict': {'webpage_url': 'sample'},
                                  'total_bytes': 200, 'downloaded_bytes': 50})
        self.assertEqual(state['download_status']['items'][0]['percent'], 25)

    def test_audio_formats_and_rate_limit(self):
        for codec in ('mp3', 'm4a', 'wav', 'opus'):
            opts = get_ydl_opts('audio', codec, str(ROOT), 125000, False, lambda _: None, '')
            self.assertEqual(opts['postprocessors'][0]['preferredcodec'], codec)
            self.assertEqual(opts['ratelimit'], 125000)

    def test_subtitle_options(self):
        opts = get_ydl_opts('video', '720p', str(ROOT), 0, True, lambda _: None, '')
        self.assertTrue(opts['writesubtitles'])
        self.assertIn({'key': 'FFmpegEmbedSubtitle'}, opts['postprocessors'])

    def test_settings_round_trip_isolated(self):
        from utils import file_helpers
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with patch.object(file_helpers, 'SETTINGS_FILE', str(Path(directory) / 'settings.json')):
                response = self.client.post('/save-settings', json={'concurrent_downloads': 2})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.client.get('/get-settings').json['concurrent_downloads'], 2)

    def test_failed_download_must_not_report_success(self):
        with patch.object(queue_manager, '_download_single', return_value=False), \
             patch.object(queue_manager, 'show_notification') as notify:
            queue_manager.run_download(['https://youtube.com/watch?v=test'], 'video', '720p', str(ROOT), False)
        self.assertNotEqual(state['download_status']['status'], 'finished_all')
        notify.assert_not_called()

    def test_worker_exception_must_be_reported(self):
        with patch.object(queue_manager, '_download_single', side_effect=RuntimeError('worker failed')), \
             patch.object(queue_manager, 'show_notification'):
            queue_manager.run_download(['https://youtube.com/watch?v=test'], 'video', '720p', str(ROOT), False)
        self.assertEqual(state['download_status']['status'], 'error')

    def test_invalid_folder_payload_must_not_return_500(self):
        self.assertEqual(self.client.post('/open-folder', json={}).status_code, 400)

    def test_urls_must_be_a_list(self):
        state['current_download_path'] = str(ROOT)
        with patch.object(application.threading, 'Thread') as thread:
            response = self.client.post('/download', json={'urls': 'https://example.com/video.mp4'})
        self.assertEqual(response.status_code, 400)
        thread.assert_not_called()

    def test_page_uses_product_name(self):
        title = re.search(r'<title>(.*?)</title>', self.client.get('/').get_data(as_text=True)).group(1)
        self.assertEqual(title, 'Video Downloader Pro')


if __name__ == '__main__':
    unittest.main()
