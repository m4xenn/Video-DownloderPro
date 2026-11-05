"""Real urllib -> curl transport fallback with generated local HLS and scoped cookies."""
import functools,http.server,json,os,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from services.generic_resolver import GenericResolver
from yt_dlp import YoutubeDL
from yt_dlp.networking import Request

class TransportLocalTests(unittest.TestCase):
 def test_resolved_hls_retry_download_and_cookie_boundaries(self):
  ffmpeg=Path(os.environ['APPDATA'])/'YoutubePro/bin/ffmpeg.exe'
  if not ffmpeg.exists():self.skipTest('Local FFmpeg component required')
  with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='transport-local-') as folder:
   base=Path(folder);media=base/'media';media.mkdir()
   from services.windows_sandbox import protect_workspace
   protect_workspace(base)
   subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=s=320x180:r=10','-f','lavfi','-i','sine=frequency=440','-t','2','-c:v','libx264','-preset','ultrafast','-g','10','-c:a','aac','-hls_time','1','-hls_playlist_type','vod',str(media/'master.m3u8')],check=True,timeout=30)
   seen=[];master_attempts=[0]
   class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
     cookie=self.headers.get('Cookie','');seen.append((self.path,self.headers.get('Host',''),cookie))
     if self.path.endswith('check'):
      self.send_response(200);self.end_headers();self.wfile.write(b'ok');return
     if self.path.startswith('/media/') and cookie!='fixture=1':
      self.send_response(403);self.end_headers();return
     if self.path=='/media/master.m3u8':
      master_attempts[0]+=1
      if master_attempts[0]==1:self.send_response(403);self.end_headers();return
     return super().do_GET()
   server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=base));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   origin=f'http://127.0.0.1:{server.server_port}';source=origin+'/media/master.m3u8'
   resolver=GenericResolver();resolver.details=Mock(return_value={'stream':source,'streams':[source],'headers':{},'source_headers':{source:{'Referer':'https://player.example/','User-Agent':'Browser-UA','Cookie':'fixture=1'}},'title':'Transport fixture','thumbnail':''})
   try:
    with patch('services.media_discovery.public_url',return_value=True),YoutubeDL({'quiet':True,'no_warnings':True,'logger':Mock(),'ffmpeg_location':str(ffmpeg.parent),'outtmpl':str(base/'result.%(ext)s'),'format':'best'}) as ydl:
     info=resolver.extract(ydl,'https://watch.example/episode')
     self.assertIsNotNone(ydl.params.get('impersonate'))
     ydl.process_ie_result(info,download=True)
     with ydl.urlopen(Request(origin+'/outside/check')) as response:self.assertEqual(response.read(),b'ok')
     with ydl.urlopen(Request(origin.replace('127.0.0.1','localhost')+'/media/check')) as response:self.assertEqual(response.read(),b'ok')
    self.assertTrue(list(base.glob('result.*')))
    self.assertGreaterEqual(master_attempts[0],2)
    self.assertTrue(all(not cookie for path,host,cookie in seen if path.endswith('check')))
   finally:server.shutdown();server.server_close();thread.join(timeout=3)
 def test_first_fragment_403_retries_same_media_with_browser_transport(self):
  from services.browser_transport import download_with_browser_retry
  ffmpeg=Path(os.environ['APPDATA'])/'YoutubePro/bin/ffmpeg.exe'
  if not ffmpeg.exists():self.skipTest('Local FFmpeg component required')
  with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='fragment-transport-') as folder:
   base=Path(folder)
   from services.windows_sandbox import protect_workspace
   protect_workspace(base)
   subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=s=320x180:r=10','-f','lavfi','-i','sine=frequency=440','-t','2','-c:v','libx264','-preset','ultrafast','-g','10','-c:a','aac','-hls_time','1','-hls_playlist_type','vod',str(base/'master.m3u8')],check=True,timeout=30)
   attempts=[0]
   class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
     if self.path.endswith('.ts'):
      attempts[0]+=1
      if attempts[0]==1:self.send_response(403);self.end_headers();return
     super().do_GET()
   server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=base));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    source=f'http://127.0.0.1:{server.server_port}/master.m3u8'
    with YoutubeDL({'quiet':True,'logger':Mock(),'no_warnings':True,'ffmpeg_location':str(ffmpeg.parent),'outtmpl':str(base/'download.%(ext)s'),'format':'best','fragment_retries':0,'skip_unavailable_fragments':False}) as ydl:
     info=ydl.extract_info(source,download=False);info['extractor_key']='EmbeddedMedia'
     with patch('services.media_discovery.public_url',return_value=True):
      download_with_browser_retry(ydl,info,lambda:True)
     self.assertIsNotNone(ydl.params.get('impersonate'))
    file=next(base.glob('download.*'))
    details=json.loads(subprocess.check_output([str(ffmpeg.parent/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(file)]))
    self.assertTrue(any(s['codec_type']=='audio' for s in details['streams']))
    self.assertTrue(any(s['codec_type']=='video' and s['height']==180 for s in details['streams']))
    self.assertGreaterEqual(attempts[0],3)
   finally:server.shutdown();server.server_close();thread.join(timeout=3)

if __name__=='__main__':unittest.main()
