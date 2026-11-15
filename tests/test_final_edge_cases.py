import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import app
from utils import file_helpers

class FinalEdgeCases(unittest.TestCase):
 def test_malformed_mutation_requests_never_return_server_error(self):
  routes=['/save-settings','/download','/queue/drafts','/playlist/preview','/get-info','/history/action','/pause','/resume','/queue/remove','/recordings/recover','/queue/recover','/set-lang']
  bodies=[[],17,'unexpected',{}, {'url':17,'id':[],'urls':{},'action':{},'items':None,'lang':[]}]
  for route in routes:
   for body in bodies:
    with self.subTest(route=route,body=body):
     response=app.app.test_client().post(route,json=body)
     self.assertLess(response.status_code,500)
 def test_settings_merge_occurs_after_acquiring_operation_lock(self):
  current={'language':'en'}
  class ConcurrentLanguageChange:
   def __enter__(self):current['language']='fr'
   def __exit__(self,*args):pass
  with patch('app.operation_lock',ConcurrentLanguageChange()),patch('app.load_settings',side_effect=lambda:dict(current)),patch('app.save_settings_to_file',side_effect=lambda value:current.update(value)),patch.object(app.download_manager,'check_configuration'),patch.object(app.download_manager,'configure'):
   response=app.app.test_client().post('/save-settings',json={'notification_mode':'never'})
  self.assertEqual(response.status_code,200);self.assertEqual(current['language'],'fr')
 def test_broken_playlist_url_is_client_error_not_server_crash(self):
  with patch.object(app.media_catalog,'preview') as preview:
   response=app.app.test_client().post('/playlist/preview',json={'urls':['http://[invalid']})
  self.assertEqual(response.status_code,400);preview.assert_not_called()
 def test_one_invalid_setting_does_not_reset_language_and_other_preferences(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
   path=Path(folder)/'settings.json';data={'language':'fr','welcome_seen':True,'notification_mode':'never','concurrent_downloads':999,'speed_limit_mbps':'12'};path.write_text(json.dumps(data))
   with patch.object(file_helpers,'SETTINGS_FILE',str(path)),patch.object(file_helpers,'LEGACY_SETTINGS_FILE',str(Path(folder)/'missing')):settings=file_helpers.load_settings()
   self.assertEqual(settings['language'],'fr');self.assertTrue(settings['welcome_seen']);self.assertEqual(settings['notification_mode'],'never');self.assertEqual(settings['concurrent_downloads'],3);self.assertEqual(settings['speed_limit_mbps'],'12')
   self.assertEqual(json.loads(path.read_text()),data)

if __name__=='__main__':unittest.main()
