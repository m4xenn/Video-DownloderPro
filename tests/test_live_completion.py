import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.live_completion import confirmed_source_end

class LiveCompletionTests(unittest.TestCase):
 def test_clean_eof_without_endlist_is_not_broadcast_end(self):
  with patch('services.live_catchup.read_window',return_value=SimpleNamespace(ended=False)):
   self.assertFalse(confirmed_source_end([{'url':'https://example.com/live.m3u8'}],[{}]))
 def test_all_selected_hls_renditions_must_end(self):
  formats=[{'url':'https://example.com/v.m3u8'},{'url':'https://example.com/a.m3u8'}]
  with patch('services.live_catchup.read_window',side_effect=[SimpleNamespace(ended=True),SimpleNamespace(ended=False)]):
   self.assertFalse(confirmed_source_end(formats,[{},{}]))
  with patch('services.live_catchup.read_window',return_value=SimpleNamespace(ended=True)):
   self.assertTrue(confirmed_source_end(formats,[{},{}]))
 def test_probe_failure_is_not_a_successful_end(self):
  with patch('services.live_catchup.read_window',side_effect=OSError('timeout')):
   self.assertFalse(confirmed_source_end([{'url':'https://example.com/a.m3u8'}],[{}]))
 def test_confirmed_dvr_end_needs_no_extra_network(self):
  self.assertTrue(confirmed_source_end([],[],SimpleNamespace(ended=True)))
