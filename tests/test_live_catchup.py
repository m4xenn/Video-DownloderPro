import sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from services.live_catchup import parse_window,plan_catchup,MAX_BYTES

def playlist(start=0,count=4,timed=True):
 rows=['#EXTM3U','#EXT-X-TARGETDURATION:1','#EXT-X-MEDIA-SEQUENCE:'+str(start),'#EXT-X-DISCONTINUITY-SEQUENCE:0']
 if timed:rows+=['#EXT-X-PROGRAM-DATE-TIME:2026-11-02T12:00:'+str(start).zfill(2)+'Z']
 for index in range(count):rows+=['#EXTINF:1,','s'+str(index+start)+'.ts']
 return ('\n'.join(rows)+'\n').encode()
class CatchupTests(unittest.TestCase):
 def test_parse_live_duration_and_utc_boundaries(self):
  w=parse_window(playlist());self.assertEqual(sum(w.durations),4);self.assertEqual(w.times[1]-w.times[0],1)
 def test_single_stream_starts_earliest_without_timing_metadata(self):
  with patch('services.live_catchup.read_window',return_value=parse_window(playlist(timed=False))):
   p=plan_catchup([{'url':'https://example.com/live.m3u8'}],[{}])
  self.assertEqual(p.indices,(0,));self.assertEqual(p.seconds,4)
 def test_split_streams_align_on_common_program_time(self):
  formats=[{'url':'https://example.com/v.m3u8'},{'url':'https://example.com/a.m3u8'}]
  with patch('services.live_catchup.read_window',side_effect=[parse_window(playlist(0,6)),parse_window(playlist(2,4))]):
   p=plan_catchup(formats,[{},{}])
  self.assertEqual(p.indices,(2,0));self.assertEqual(p.seconds,4)
 def test_unknown_split_alignment_falls_back_without_guessing(self):
  formats=[{'url':'https://example.com/v.m3u8'},{'url':'https://example.com/a.m3u8'}]
  with patch('services.live_catchup.read_window',return_value=parse_window(playlist(timed=False))):p=plan_catchup(formats,[{},{}])
  self.assertEqual(p.indices,(-3,-3));self.assertEqual(p.seconds,0)
 def test_probe_failure_preserves_normal_live_path(self):
  with patch('services.live_catchup.read_window',side_effect=ValueError('bad manifest')):
   self.assertEqual(plan_catchup([{'url':'https://example.com/live.m3u8'}],[{}]).indices,(-3,))
 def test_ended_or_non_hls_does_not_claim_live_catchup(self):
  with patch('services.live_catchup.read_window') as read:
   self.assertEqual(plan_catchup([{'url':'https://example.com/live.mpd'}],[{}]).seconds,0);read.assert_not_called()
  with patch('services.live_catchup.read_window',return_value=parse_window(playlist()+b'#EXT-X-ENDLIST')):
   self.assertEqual(plan_catchup([{'url':'https://example.com/live.m3u8'}],[{}]).seconds,0)
 def test_malformed_discontinuous_or_oversized_manifests_rejected(self):
  for body in (b'bad',b'x'*(MAX_BYTES+1),playlist()+b'#EXT-X-DISCONTINUITY',b'#EXTM3U\n#EXTINF:nan,\na.ts'):
   with self.assertRaises(ValueError):parse_window(body)
 def test_cancel_skips_probe(self):
  with patch('services.live_catchup.read_window') as read:
   plan_catchup([{'url':'https://example.com/live.m3u8'}],[{}],lambda:True);read.assert_not_called()

 def test_initial_manifest_is_pinned_then_refreshes_without_source_url_leak(self):
  import urllib.request,urllib.error
  from dataclasses import replace
  from services.live_catchup import CatchupPlan,HLSHistoryProxy
  base='https://cdn.example/video/list.m3u8?signature=PRIVATE'
  original=replace(parse_window(playlist()),url=base)
  refreshed=replace(parse_window(playlist(1,4)),url=base)
  plan=CatchupPlan((0,),4,2,0,(original,))
  self.assertNotIn('PRIVATE',repr(plan))
  router=HLSHistoryProxy(plan,[{'url':base}],[{}])
  with patch('services.media_discovery.public_url',return_value=True),patch('services.live_catchup.read_window',return_value=refreshed) as refresh:
   try:
    url=router.start()[0]
    with urllib.request.urlopen(url,timeout=2) as response:first=response.read().decode()
    self.assertIn('https://cdn.example/video/s0.ts',first);refresh.assert_not_called()
    with urllib.request.urlopen(url,timeout=2) as response:second=response.read().decode()
    self.assertIn('https://cdn.example/video/s1.ts',second)
    refresh.assert_called_once_with(base,{},allow_discontinuity=True)
    request=urllib.request.Request(url,headers={'Origin':'https://evil.example'})
    with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(request,timeout=2)
   finally:router.close()
 def test_reload_can_pass_discontinuity_to_native_demuxer(self):
  self.assertTrue(parse_window(playlist()+b'#EXT-X-DISCONTINUITY',allow_discontinuity=True).durations)

 def test_telemetry_measures_media_pace_independent_of_small_bitrate(self):
  from services.live_recording import LiveTelemetry
  telemetry=LiveTelemetry(0)
  speed,pace=telemetry.sample(2,180000,24)
  self.assertEqual(speed,90000);self.assertEqual(pace,12)

 def test_telemetry_ages_out_rate_during_network_wait(self):
  from services.live_recording import LiveTelemetry
  telemetry=LiveTelemetry(0)
  telemetry.sample(1,500000,10)
  for now in range(2,9):speed,pace=telemetry.sample(now,500000,10)
  self.assertEqual(speed,0);self.assertEqual(pace,0)

if __name__=='__main__':unittest.main()
