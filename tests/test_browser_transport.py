import sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.browser_transport import enable_browser_transport
URL='https://cdn.example/media/master.m3u8'
class TransportTests(unittest.TestCase):
 def ydl(self):
  ydl=Mock();ydl.params={'http_headers':{'Referer':'https://player.example/'}};ydl.cookiejar=object();return ydl
 def test_only_403_on_public_media_is_retried(self):
  for message in ['HTTP Error 404','timeout','DRM 403','Login required 403','Sign in 403','Private video 403','Copyright 403']:
   ydl=self.ydl()
   with patch('services.media_discovery.public_url',return_value=True):self.assertFalse(enable_browser_transport(ydl,URL,message))
   self.assertNotIn('impersonate',ydl.params)
 def test_transport_changes_once_and_preserves_jar_and_headers(self):
  ydl=self.ydl();jar=ydl.cookiejar;director=Mock();ydl.__dict__['_request_director']=director
  with patch('services.media_discovery.public_url',return_value=True):
   self.assertTrue(enable_browser_transport(ydl,URL,'HTTP Error 403'))
   self.assertFalse(enable_browser_transport(ydl,URL,'HTTP Error 403'))
  director.close.assert_called_once();self.assertIs(ydl.cookiejar,jar)
  self.assertEqual(ydl.params['http_headers'],{'Referer':'https://player.example/'})
 def test_missing_backend_keeps_original_transport(self):
  ydl=self.ydl();ydl._impersonate_target_available.return_value=False
  with patch('services.media_discovery.public_url',return_value=True):self.assertFalse(enable_browser_transport(ydl,URL,'403'))
  self.assertNotIn('impersonate',ydl.params)
 def test_private_source_not_retried(self):
  ydl=self.ydl()
  with patch('services.media_discovery.public_url',return_value=False):self.assertFalse(enable_browser_transport(ydl,URL,'403'))
 def test_explicit_transport_preference_is_preserved(self):
  ydl=self.ydl();ydl.params['impersonate']='chosen'
  with patch('services.media_discovery.public_url',return_value=True):self.assertFalse(enable_browser_transport(ydl,URL,'403'))
  self.assertEqual(ydl.params['impersonate'],'chosen')
class DownloadTransportTests(unittest.TestCase):
 def test_retry_keeps_exact_same_info_and_runs_callback_once(self):
  from services.browser_transport import download_with_browser_retry
  info={'extractor_key':'EmbeddedMedia','url':URL};ydl=Mock();ydl.process_ie_result.side_effect=[ValueError('403'),'done'];prepare=Mock()
  with patch('services.browser_transport.enable_browser_transport',return_value=True):
   self.assertEqual(download_with_browser_retry(ydl,info,lambda:True,prepare),'done')
  self.assertEqual(ydl.process_ie_result.call_count,2);prepare.assert_called_once()
  self.assertTrue(all(call.args[0] is info for call in ydl.process_ie_result.call_args_list))
 def test_partial_data_stops_retry(self):
  from services.browser_transport import download_with_browser_retry
  ydl=Mock();ydl.process_ie_result.side_effect=ValueError('403')
  with patch('services.browser_transport.enable_browser_transport') as enable:
   with self.assertRaises(ValueError):download_with_browser_retry(ydl,{'extractor_key':'EmbeddedMedia','url':URL},lambda:False)
   enable.assert_not_called()
 def test_native_extractors_do_not_change_transport(self):
  from services.browser_transport import download_with_browser_retry
  ydl=Mock();ydl.process_ie_result.side_effect=ValueError('403')
  with patch('services.browser_transport.enable_browser_transport') as enable:
   with self.assertRaises(ValueError):download_with_browser_retry(ydl,{'extractor_key':'Youtube','url':URL},lambda:True)
   enable.assert_not_called()
 def test_retry_failure_is_not_looped(self):
  from services.browser_transport import download_with_browser_retry
  ydl=Mock();ydl.process_ie_result.side_effect=ValueError('403')
  with patch('services.browser_transport.enable_browser_transport',return_value=True):
   with self.assertRaises(ValueError):download_with_browser_retry(ydl,{'extractor_key':'EmbeddedMedia','url':URL},lambda:True)
  self.assertEqual(ydl.process_ie_result.call_count,2)

if __name__=='__main__':unittest.main()
