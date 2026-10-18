import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from services.language_service import supported_language, system_language
import app

class LanguageTests(unittest.TestCase):
    def test_regional_codes(self):
        for code, expected in [('tr-TR','tr'),('en_US','en'),('pt-BR','pt'),('zh-TW','zh'),('ja-JP','ja'),('fr_CA','fr')]:
            self.assertEqual(supported_language(code), expected)
    def test_unknown(self):
        for code in [None, '', 'xx-XX', {}, 'constructor']:
            self.assertIsNone(supported_language(code))
    def test_fallback(self):
        with patch('services.language_service.sys.platform','linux'), patch('services.language_service.locale.getlocale',return_value=('xx_XX','UTF-8')):
            self.assertEqual(system_language(),'en')
    def test_system_locale(self):
        with patch('services.language_service.sys.platform','linux'), patch('services.language_service.locale.getlocale',return_value=('de_DE','UTF-8')):
            self.assertEqual(system_language(),'de')
    def test_manual_saved_without_losing_settings(self):
        with patch.object(app,'load_settings',return_value={'speed_limit_mbps':'5'}), patch.object(app,'save_settings_to_file') as save:
            result=app.app.test_client().post('/set-lang',json={'lang':'fr'})
            self.assertEqual(result.status_code,200)
            self.assertEqual(save.call_args.args[0],{'speed_limit_mbps':'5','language':'fr'})
    def test_auto_not_persisted(self):
        with patch.object(app,'save_settings_to_file') as save:
            self.assertEqual(app.app.test_client().post('/set-lang',json={'lang':'en','persist':False}).status_code,200)
            save.assert_not_called()
    def test_invalid_rejected(self):
        with patch.object(app,'save_settings_to_file') as save:
            for payload in [None,{},[],{'lang':'xx'},{'lang':[]}]:
                self.assertEqual(app.app.test_client().post('/set-lang',json=payload).status_code,400)
            save.assert_not_called()
