"""Metadata error boundaries and packaged offline UI resources."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import app
from state.app_state import state

class StudioTests(unittest.TestCase):
    def setUp(self):
        self.client=app.app.test_client()

    def test_invalid_metadata_payload_does_not_call_extractor(self):
        with patch('yt_dlp.YoutubeDL') as ydl:
            for value in [None,[],{}, {'url':34},{'url':'file:///C:/private.mp4'},{'url':'https://['},{'url':'https:///missing-host'}]:
                with self.subTest(value=value):
                    response=self.client.post('/get-info',json=value)
                    self.assertEqual(response.status_code,400)
                    self.assertEqual(response.json['status'],'error')
            ydl.assert_not_called()

    def test_metadata_network_timeout_and_certificate_validation(self):
        with patch('yt_dlp.YoutubeDL') as ydl:
            ydl.return_value.__enter__.return_value.extract_info.return_value={'id':'one','title':'A video'}
            response=self.client.post('/get-info',json={'url':'https://example.com/video'})
            self.assertEqual(response.status_code,200)
            options=ydl.call_args.args[0]
            self.assertEqual(options['socket_timeout'],15)
            self.assertFalse(options.get('nocheckcertificate',False))

    def test_home_reflects_current_destination(self):
        saved=copy.deepcopy(state)
        try:
            state['current_download_path']='C:/Downloads/My chosen folder'
            with patch.object(app,'ensure_download_state'):
                response=self.client.get('/')
            self.assertIn(b'C:/Downloads/My chosen folder',response.data)
        finally:
            state.clear();state.update(saved)

    def test_offline_ui_assets_are_served(self):
        for path in ['studio.css','studio.js','vendor/fontawesome/css/all.min.css',
                     'vendor/fontawesome/webfonts/fa-solid-900.woff2','vendor/flags/flags/4x3/tr.svg']:
            with self.subTest(path=path):
                response=self.client.get('/static/'+path)
                self.assertEqual(response.status_code,200)
                self.assertGreater(len(response.data),100)
                response.close()

if __name__=='__main__': unittest.main()
