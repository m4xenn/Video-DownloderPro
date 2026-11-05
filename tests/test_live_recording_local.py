"""Real live HLS capture, graceful finish and wall-clock stop using synthetic media."""
import functools,http.server,json,os
from pathlib import Path
import subprocess,sys,tempfile,threading,time,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from services.live_recording import record_live,LiveRecordingGapError
from core.bandwidth import DownloadPaused

class LiveLocalTests(unittest.TestCase):
 def setUp(self):
  # Only these generated fixtures may use their owned loopback server.
  for target in ('services.live_network.require_public_link','services.secure_transport.pin_requests_session'):
   fixture=patch(target,side_effect=(lambda value:value))
   fixture.start();self.addCleanup(fixture.stop)
  fixture=patch('services.live_network.pin_requests_session',side_effect=lambda value:value)
  fixture.start();self.addCleanup(fixture.stop)
 @classmethod
 def setUpClass(cls):
  cls.bin=Path(os.environ['APPDATA'])/'YoutubePro/bin'
  if not (cls.bin/'ffmpeg.exe').is_file():raise unittest.SkipTest('FFmpeg required')
  cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='live-record-test-');cls.base=Path(cls.temp.name)
  from services.windows_sandbox import protect_workspace
  protect_workspace(cls.base)
  subprocess.run([str(cls.bin/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=s=320x180:r=10','-f','lavfi','-i','sine=frequency=440','-t','8','-c:v','libx264','-preset','ultrafast','-g','10','-c:a','aac','-hls_time','1','-hls_list_size','0',str(cls.base/'live.m3u8')],check=True,timeout=30)
  p=cls.base/'live.m3u8';p.write_text(p.read_text().replace('#EXT-X-ENDLIST',''))
  class Handler(http.server.SimpleHTTPRequestHandler):
   retry_once=False;fail_forever=False;failed_segment=None;seen={}
   def log_message(self,*args):pass
   def do_GET(self):
    cls_handler=type(self);cls_handler.seen[self.path]=cls_handler.seen.get(self.path,0)+1
    if (cls_handler.retry_once and self.path.endswith('.ts')) or (cls_handler.fail_forever and self.path==cls_handler.failed_segment):
     cls_handler.retry_once=False;cls_handler.failed_segment=self.path
     self.send_response(503);self.send_header('Content-Length','0');self.end_headers();return
    return super().do_GET()
  cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(cls.base)))
  cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.worker.start()
  cls.url=f'http://127.0.0.1:{cls.server.server_port}/live.m3u8'
  split=cls.base/'split';split.mkdir()
  subprocess.run([str(cls.bin/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=s=320x180:r=10',
      '-f','lavfi','-i','sine=frequency=440','-map','0:v','-t','8','-c:v','libx264','-preset','ultrafast','-g','10','-an',
      '-hls_time','1','-hls_list_size','0',str(split/'video.m3u8'),'-map','1:a','-t','8','-c:a','aac','-vn',
      '-hls_time','1','-hls_list_size','0',str(split/'audio.m3u8')],check=True,timeout=30)
  for name in ('video.m3u8','audio.m3u8'):
   manifest=split/name;manifest.write_text(manifest.read_text().replace('#EXT-X-ENDLIST',''))

 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.worker.join(3);cls.temp.cleanup()
 def verify(self,name,until=None):
  target=self.base/(name+'.mp4');start=time.monotonic();events=[]
  info=dict(url=self.url,is_live=True,vcodec='h264',acodec='aac',protocol='m3u8',ext='mp4')
  with patch('services.media_discovery.public_url',return_value=True):
   result=record_live(info,target,str(self.bin),dict(format='video',live_record_minutes=1,live_record_until=until),lambda:False,lambda:until is None and time.monotonic()-start>2,events.append)
  self.assertTrue(target.is_file());self.assertFalse(target.with_suffix('.live.mkv').exists())
  streams=json.loads(subprocess.check_output([str(self.bin/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(target)]))['streams']
  self.assertTrue(any(s['codec_type']=='video' for s in streams));self.assertTrue(any(s['codec_type']=='audio' for s in streams))
  self.assertLess(time.monotonic()-start,23);return result

 def test_queue_can_reuse_only_the_locked_finalized_live_file(self):
  from services.output_validation import validation_session,validate_output,_validate_output
  with validation_session(),patch('services.output_validation._validate_output',wraps=_validate_output) as full:
   self.verify('validation-reuse')
   checked=validate_output(self.base/'validation-reuse.mp4',str(self.bin),True,expect_audio=True,include_duration=True,reuse_validation=True)
   self.assertTrue(checked['video'] and checked['audio'])
   self.assertEqual(full.call_count,1)
 def test_graceful_finish_publishes_playable_audio_video(self):self.verify('manual')
 def test_dynamic_dash_preserves_selected_video_and_audio(self):
  from services.dash_metadata import extract_dash
  from yt_dlp import YoutubeDL
  folder=self.base/'dynamic-dash';folder.mkdir();target=self.base/'dash-live.mp4'
  producer=subprocess.Popen([str(self.bin/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-re','-f','lavfi','-i','testsrc2=s=320x180:r=10',
      '-re','-f','lavfi','-i','sine=frequency=440','-t','15','-c:v','libx264','-preset','ultrafast','-g','10','-c:a','aac',
      '-seg_duration','1','-window_size','5','-f','dash','manifest.mpd'],cwd=folder,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
      creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  try:
   deadline=time.monotonic()+8
   while not (folder/'manifest.mpd').exists() and time.monotonic()<deadline:time.sleep(.1)
   self.assertTrue((folder/'manifest.mpd').exists())
   url=self.url.rsplit('/',1)[0]+'/dynamic-dash/manifest.mpd'
   with patch('services.media_discovery.public_url',return_value=True),YoutubeDL({'quiet':True,'no_warnings':True,'format':'bestvideo+bestaudio/best','ffmpeg_location':str(self.bin)}) as ydl:
    info=ydl.process_ie_result(extract_dash(ydl,url,'live-dash','Live DASH'),download=False)
    self.assertTrue(info['is_live']);start=time.monotonic()
    record_live(info,target,str(self.bin),dict(format='video',live_record_minutes=1),lambda:False,lambda:time.monotonic()-start>3)
   streams=json.loads(subprocess.check_output([str(self.bin/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(target)]))['streams']
   self.assertTrue(any(s['codec_type']=='video' for s in streams));self.assertTrue(any(s['codec_type']=='audio' for s in streams))
  finally:
   if producer.poll() is None:producer.terminate()
   producer.wait(timeout=5);producer.stderr.close()
 def split_info(self,audio_name='audio.m3u8'):
  prefix=self.url.rsplit('/',1)[0]+'/split/'
  return {'is_live':True,'requested_formats':[
    {'url':prefix+'video.m3u8','vcodec':'h264','acodec':'none','protocol':'m3u8_native'},
    {'url':prefix+audio_name,'vcodec':'none','acodec':None,'protocol':'m3u8_native'}]}
 def test_split_hls_unknown_audio_codec_is_recorded_and_audible(self):
  target=self.base/'unknown-audio.mp4';start=time.monotonic();events=[]
  with patch('services.media_discovery.public_url',return_value=True):
   record_live(self.split_info(),target,str(self.bin),dict(format='video',live_record_minutes=1),lambda:False,lambda:time.monotonic()-start>2,events.append)
  streams=json.loads(subprocess.check_output([str(self.bin/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(target)]))['streams']
  self.assertEqual({s['codec_type'] for s in streams},{'video','audio'})
  measured=subprocess.run([str(self.bin/'ffmpeg.exe'),'-hide_banner','-i',str(target),'-vn','-af','volumedetect','-f','null','-'],capture_output=True,text=True,check=True,timeout=15)
  import re
  mean=re.search(r'mean_volume: (-?[0-9.]+) dB',measured.stderr)
  self.assertIsNotNone(mean);self.assertGreater(float(mean[1]),-60)
  self.assertTrue(any('recording_speed_bps' in e for e in events if e['status']=='downloading'))
 def test_declared_audio_without_audio_stream_does_not_publish_silent_file(self):
  target=self.base/'missing-audio.mp4'
  with patch('services.media_discovery.public_url',return_value=True),self.assertRaises(ValueError):
   record_live(self.split_info('video.m3u8'),target,str(self.bin),dict(format='video',live_record_minutes=1),lambda:False,lambda:False)
  self.assertFalse(target.exists())
 def test_exhausted_segment_retries_do_not_publish_a_successful_recording(self):
  handler=self.server.RequestHandlerClass.func;handler.seen={};handler.retry_once=True;handler.fail_forever=True;handler.failed_segment=None
  target=self.base/'missing-segment.mp4'
  info=dict(url=self.url,is_live=True,vcodec='h264',acodec='aac',protocol='m3u8',ext='mp4')
  try:
   with patch('services.media_discovery.public_url',return_value=True),self.assertRaises(LiveRecordingGapError):
    record_live(info,target,str(self.bin),dict(format='video',live_record_minutes=1,live_record_until=time.time()+10),lambda:False,lambda:False)
   self.assertFalse(target.exists());self.assertGreaterEqual(handler.seen[handler.failed_segment],4)
  finally:handler.fail_forever=False;handler.retry_once=False
 def test_transient_503_reconnects_to_same_segment(self):
  handler=self.server.RequestHandlerClass.func;handler.seen={};handler.retry_once=True;handler.failed_segment=None
  self.verify('reconnect')
  self.assertIsNotNone(handler.failed_segment);self.assertGreaterEqual(handler.seen[handler.failed_segment],2)
 def test_pause_preserves_recoverable_mkv_without_claiming_completion(self):
  target=self.base/'paused.mp4';start=time.monotonic()
  info=dict(url=self.url,is_live=True,vcodec='h264',acodec='aac',protocol='m3u8',ext='mp4')
  with patch('services.media_discovery.public_url',return_value=True),self.assertRaises(DownloadPaused):
   record_live(info,target,str(self.bin),dict(format='video',live_record_minutes=1),lambda:time.monotonic()-start>2,lambda:False)
  self.assertTrue(target.with_suffix('.live.mkv').is_file());self.assertFalse(target.exists())
 def test_scheduled_wall_clock_finish(self):self.verify('scheduled',time.time()+6)
 def test_unexpected_clean_ffmpeg_exit_preserves_partial_and_reports_gap(self):
  from services import media_process
  original=media_process.Popen
  def quick_reload(args,*a,**k):
   if '-progress' in args:
    # Force a real successful FFmpeg exit at two seconds while the recorder
    # still expects sixty. No fake media or fabricated process return code.
    args=list(args);args[args.index('-t')+1]='2'
   return original(args,*a,**k)
  target=self.base/'stalled-clean-eof.mp4'
  info=dict(url=self.url,is_live=True,vcodec='h264',acodec='aac',protocol='m3u8',ext='mp4')
  with patch('services.media_discovery.public_url',lambda *a,**k:True),patch('services.media_process.Popen',side_effect=quick_reload),self.assertRaises(LiveRecordingGapError) as caught:
   record_live(info,target,str(self.bin),dict(format='video',live_record_minutes=1),lambda:False,lambda:False)
  self.assertTrue(target.with_suffix('.live.mkv').is_file());self.assertFalse(target.exists())
  self.assertEqual(caught.exception.recording_diagnostics['stop_reason'],'unconfirmed_eof')

if __name__=='__main__':unittest.main()
