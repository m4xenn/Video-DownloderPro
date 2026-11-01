from pathlib import Path
import sys,time,unittest
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from core.fragment_policy import FragmentPolicy
from services.live_recording import live_options,LiveRecordingGapError
from services.dash_metadata import inspect_dash
from services.hls_metadata import ProtectedMediaError
from utils.download_settings import normalize_settings

class EnhancementTests(unittest.TestCase):
 def test_live_gap_error_survives_queue_serialization(self):
  from services.diagnostics import error_code
  self.assertEqual(error_code(str(LiveRecordingGapError())),'recording_gap')
 def test_api_live_submission_and_cross_origin_actions(self):
  import app
  from services.media_catalog import MediaCatalog
  from state.app_state import state
  catalog=MediaCatalog();url='https://example.com/live';catalog.remember(url,dict(is_live=True,title='Fixture'))
  with patch.dict(state,current_download_path=str(ROOT)),patch.object(app,'ensure_download_state'),patch.object(app,'media_catalog',catalog),patch.object(app,'prepare_download',return_value=({'status':'success'},202)) as submit:
   client=app.app.test_client();data=dict(urls=[url],format='video',quality='max',live_record_minutes=15)
   self.assertEqual(client.post('/download',json=data).status_code,202);self.assertEqual(submit.call_args.args[1]['live_record_minutes'],15)
   for changes in [dict(live_record_minutes=0),dict(live_record_until=time.time()-60),dict(embed_subs=True),dict(urls=[url,'https://example.com/other'])]:
    self.assertEqual(client.post('/download',json=dict(data,**changes)).status_code,400)
   for endpoint in ['/recording/finish','/browser-companion/focus']:
    self.assertEqual(client.post(endpoint,json={'url':url},headers={'Origin':'https://evil.example'}).status_code,403)
    self.assertEqual(client.post(endpoint,data='url=ignored').status_code,403)
 def test_live_duration_and_schedule_bounds(self):
  self.assertEqual(live_options({},now=100)['live_record_minutes'],60)
  for data in [dict(live_record_minutes=True),dict(live_record_minutes=0),dict(live_record_minutes=1441),dict(live_record_until=100),dict(live_record_until=float('nan'))]:
   with self.assertRaises(ValueError):live_options(data,now=100)
  self.assertEqual(live_options(dict(live_record_until=200),now=100)['live_record_until'],200)
 def test_transfer_mode_is_validated_and_defaults_to_stable(self):
  self.assertEqual(normalize_settings({})['transfer_mode'],'stable')
  with self.assertRaises(ValueError):normalize_settings(dict(transfer_mode='unbounded'))
 def test_fragment_probe_improvement_and_error_rollback(self):
  now=[0];p=FragmentPolicy(lambda:now[0]);info=dict(extractor_key='EmbeddedMedia',url='https://cdn.example/v.m3u8',protocol='m3u8_native')
  ticket,limit=p.begin(info,'auto');self.assertEqual(limit,1);now[0]+=20;p.finish(ticket,2_000_000,True)
  ticket,limit=p.begin(info,'auto');self.assertEqual(limit,2);now[0]+=20;p.finish(ticket,3_000_000,True)
  ticket,limit=p.begin(info,'auto');self.assertEqual(limit,3);now[0]+=20;p.finish(ticket,0,False)
  self.assertEqual(p.begin(info,'auto')[1],1)
 def test_no_gain_rolls_back_and_capped_or_live_transfers_do_not_probe(self):
  now=[0];p=FragmentPolicy(lambda:now[0]);info=dict(extractor_key='EmbeddedMedia',url='https://cdn.example/v.m3u8',protocol='m3u8_native')
  ticket,_=p.begin(info,'auto');now[0]+=20;p.finish(ticket,2_000_000,True)
  ticket,_=p.begin(info,'auto');now[0]+=20;p.finish(ticket,2_000_000,True)
  self.assertEqual(p.begin(info,'auto')[1],1)
  self.assertIsNone(p.begin(info,'auto',100_000)[0]);self.assertIsNone(p.begin(dict(info,is_live=True),'auto')[0])
 def test_overlapping_jobs_cannot_claim_a_speed_gain(self):
  now=[0];p=FragmentPolicy(lambda:now[0]);info=dict(extractor_key='EmbeddedMedia',url='https://cdn.example/v.m3u8',protocol='m3u8_native')
  a,_=p.begin(info,'auto');b,_=p.begin(info,'auto');now[0]=20;p.finish(a,4_000_000,True);p.finish(b,4_000_000,True)
  self.assertEqual(p.begin(info,'auto')[1],1)
 def test_dash_protection_dynamic_and_entity_rejection(self):
  _,e=inspect_dash(b'<MPD type="dynamic"/>');self.assertTrue(e['is_live']);self.assertEqual(e['protection'],'clear')
  _,e=inspect_dash(b'<MPD><ContentProtection schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"/></MPD>');self.assertEqual(e['systems'],['Widevine'])
  _,e=inspect_dash(b'<MPD><ContentProtection schemeIdUri="urn:mpeg:dash:mp4protection:2011"/></MPD>');self.assertEqual(e['protection'],'unknown')
  with self.assertRaises(ValueError):inspect_dash(b'<!DOCTYPE MPD><MPD/>')

if __name__=='__main__':unittest.main()
