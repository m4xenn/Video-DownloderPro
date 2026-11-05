"""Real HLS backlog -> live transition, retaining one continuous AV recording."""
import functools,http.server,json,os,re,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from services.live_recording import record_live
class CatchupLocalTests(unittest.TestCase):
 def setUp(self):
  for target in ('services.live_network.require_public_link','services.live_network.pin_requests_session','services.secure_transport.pin_requests_session'):
   fixture=patch(target,side_effect=lambda value:value)
   fixture.start();self.addCleanup(fixture.stop)
 def run_case(self,split=False,origin=False):
  tools=Path(os.environ['APPDATA'])/'YoutubePro/bin'
  if not (tools/'ffmpeg.exe').is_file():self.skipTest('FFmpeg required')
  with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='catchup-local-') as folder:
   base=Path(folder);source=base/'source';source.mkdir()
   from services.windows_sandbox import protect_workspace
   protect_workspace(base)
   subprocess.run([str(tools/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=s=320x180:r=10','-f','lavfi','-i','sine=frequency=440','-t','32','-c:v','libx264','-preset','ultrafast','-g','10','-c:a','aac','-hls_time','1','-hls_list_size','0',str(source/'stream.m3u8')],check=True,timeout=30)
   text=(source/'stream.m3u8').read_text();segments=[];duration=None
   for line in text.splitlines():
    if line.startswith('#EXTINF:'):duration=line
    elif line and not line.startswith('#') and duration:segments.append((duration,line));duration=None
   self.assertGreaterEqual(len(segments),31)
   started=time.monotonic();requests=[];events=[]
   class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
     if origin and self.headers.get('Origin')!='https://source.example':self.send_error(403);return
     if self.path in ('/history.m3u8','/history-audio.m3u8'):
      count=min(len(segments),20+int(time.monotonic()-started))
      rows=['#EXTM3U','#EXT-X-VERSION:3','#EXT-X-TARGETDURATION:1','#EXT-X-MEDIA-SEQUENCE:0','#EXT-X-PROGRAM-DATE-TIME:2026-11-02T12:00:00Z']
      for entry in segments[:count]:rows.extend(entry)
      body=('\n'.join(rows)+'\n').encode();self.send_response(200);self.send_header('Content-Type','application/vnd.apple.mpegurl');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
     if self.path.endswith('.ts'):
      match=re.search(r'(\d+)\.ts$',self.path)
      if match:requests.append((time.monotonic()-started,int(match[1])))
     return super().do_GET()
   server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(source)))
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   target=base/'recorded.mp4';url=f'http://127.0.0.1:{server.server_port}/history.m3u8'
   info=dict(url=url,is_live=True,vcodec='h264',acodec='aac',protocol='m3u8_native')
   if origin:info['http_headers']={'Origin':'https://source.example'}
   if split:info['requested_formats']=[dict(url=url,vcodec='h264',acodec='none',protocol='m3u8_native'),dict(url=url.replace('history.m3u8','history-audio.m3u8'),vcodec='none',acodec=None,protocol='m3u8_native')]
   def progress(event):
    if event['status']=='downloading':events.append((time.monotonic()-started,event['recorded_seconds'],event['recording_phase']))
   try:
    with patch('services.media_discovery.public_url',return_value=True):
     result=record_live(info,target,str(tools),dict(format='video',live_record_minutes=1),lambda:False,lambda:time.monotonic()-started>6,progress)
    self.assertTrue(any(wall<3 and recorded>=18 for wall,recorded,phase in events),events)
    self.assertIn('catchup',[e[2] for e in events]);self.assertIn('live',[e[2] for e in events])
    self.assertTrue(any(index>=22 for _,index in requests),requests)
    self.assertEqual(min(index for _,index in requests),0)
    self.assertGreater(result['recorded_seconds'],22)
    streams=json.loads(subprocess.check_output([str(tools/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(target)]))['streams']
    self.assertEqual({s['codec_type'] for s in streams},{'video','audio'})
    self.assertLess(abs(float(streams[0]['duration'])-float(streams[1]['duration'])),.4)
    decoded=subprocess.run([str(tools/'ffmpeg.exe'),'-v','error','-xerror','-i',str(target),'-f','null','-'],capture_output=True,check=True,timeout=20)
    self.assertFalse(decoded.stderr)
    print('Caught 20 seconds of history in <3 seconds, then appended new live AV segments without restarting.')
   finally:server.shutdown();server.server_close();thread.join(3)
 def test_fast_history_then_new_live_segments_in_same_audio_video_file(self):self.run_case()
 def test_separate_inputs_with_unknown_audio_follow_common_timeline(self):self.run_case(True)
 def test_origin_header_reaches_source_through_native_manifest_proxy(self):self.run_case(origin=True)
if __name__=='__main__':unittest.main()
