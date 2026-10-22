"""Welcome preference lives in app settings, independent of WebView storage."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import app
from utils import file_helpers

class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(dir=ROOT/'tmp/ui-redesign')
        self.addCleanup(self.folder.cleanup)
        for name,file in [('SETTINGS_FILE','settings.json'),('LEGACY_SETTINGS_FILE','legacy.json')]:
            item=patch.object(file_helpers,name,str(Path(self.folder.name)/file))
            item.start();self.addCleanup(item.stop)
        self.client=app.app.test_client()

    def test_preference_survives_restart_and_preserves_other_settings(self):
        file_helpers.save_settings_to_file({'language':'tr','speed_limit_mbps':'8'})
        self.assertEqual(self.client.post('/onboarding/complete',json={}).status_code,200)
        stored=file_helpers.load_settings()
        self.assertIs(stored['welcome_seen'],True)
        self.assertEqual(stored['language'],'tr')
        self.assertEqual(stored['speed_limit_mbps'],'8')
        # A fresh client represents a new WebView origin/session.
        with patch.object(app,'ensure_download_state'):
            html=app.app.test_client().get('/').data
        self.assertIn(b'data-welcome-seen="true"',html)

    def test_first_run_defaults_to_unseen(self):
        with patch.object(app,'ensure_download_state'):
            self.assertIn(b'data-welcome-seen="false"',self.client.get('/').data)

    def test_repeated_completion_is_idempotent(self):
        for _ in range(2):
            self.assertEqual(self.client.post('/onboarding/complete',json={}).status_code,200)
        self.assertIs(file_helpers.load_settings()['welcome_seen'],True)

    def test_cross_site_and_non_json_requests_do_not_write(self):
        with patch.object(app,'save_settings_to_file') as save:
            self.assertEqual(self.client.post('/onboarding/complete',json={},headers={'Origin':'https://other.example'}).status_code,403)
            self.assertEqual(self.client.post('/onboarding/complete',json={},headers={'Sec-Fetch-Site':'cross-site'}).status_code,403)
            self.assertEqual(self.client.post('/onboarding/complete',data='ignored').status_code,403)
            save.assert_not_called()

    def test_write_failure_is_reported(self):
        with patch.object(app,'save_settings_to_file',side_effect=OSError('read only')):
            self.assertEqual(self.client.post('/onboarding/complete',json={}).status_code,500)

if __name__=='__main__': unittest.main()
