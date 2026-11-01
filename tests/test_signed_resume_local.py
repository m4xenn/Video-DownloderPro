"""A real HTTP Range resume across a changed signed query, guarded by a strong ETag."""
import functools,http.server,os
from pathlib import Path
import subprocess,sys,tempfile,threading,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];os.environ.setdefault('VIDEO_DOWNLOADER_DATA_DIR',str(ROOT/'build/signed-resume-profile'));sys.path.insert(0,str(ROOT/'src'))
from yt_dlp import YoutubeDL
from services.media_preflight import preflight_media
from services.source_recovery import source_checkpoint
from core.downloader import _download_single

class SignedResumeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='signed-resume-');cls.base=Path(cls.temp.name)
  cls.bin=Path(os.environ['APPDATA'])/'YoutubePro/bin';cls.source=cls.base/'source.mp4'
  subprocess.run([str(cls.bin/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=s=320x180:r=10','-f','lavfi','-i','sine=frequency=440','-t','4','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(cls.source)],check=True,timeout=30)
  cls.body=cls.source.read_bytes();cls.requests=[]
  class Handler(http.server.BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):
    cls.requests.append(self.headers.get('Range',''))
    tag='"changed"' if 'changed' in self.path else '"same-representation"'
    raw=self.headers.get('Range','');start=0;end=len(cls.body)-1
    if raw:
     a,b=raw.removeprefix('bytes=').split('-');start=int(a);end=min(int(b) if b else end,end)
    if start>end:self.send_error(416);return
    self.send_response(206 if raw else 200);self.send_header('Content-Type','video/mp4');self.send_header('ETag',tag)
    self.send_header('Content-Length',str(end-start+1))
    if raw:self.send_header('Content-Range',f'bytes {start}-{end}/{len(cls.body)}')
    self.end_headers();self.wfile.write(cls.body[start:end+1])
  cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.worker.start()
  cls.origin=f'http://127.0.0.1:{cls.server.server_port}/source.mp4'
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.worker.join(3);cls.temp.cleanup()
 def inspected(self,token):
  info=dict(id='fixture',title='Fixture',url=self.origin+'?token='+token,duration=4,vcodec='h264',acodec='aac',ext='mp4',protocol='http',extractor_key='EmbeddedMedia')
  with patch('services.media_preflight.public_url',return_value=True),YoutubeDL({'quiet':True}) as ydl:preflight_media(ydl,info)
  self.assertEqual(info['source_status'],'container_checked');return info
 def run_case(self,name,token,expected):
  folder=self.base/name;folder.mkdir();output=folder/'output.mp4';partial=folder/'output.mp4.part'
  middle=len(self.body)//2;partial.write_bytes(self.body[:middle]);before=self.inspected('old');after=self.inspected(token)
  errors=[];completed=[];first=len(self.requests)
  with patch('services.site_resolver.extract_media_info',return_value=after):
   success=_download_single('https://watch.example/signed-'+name,dict(quiet=True,format='best',outtmpl=str(output),ffmpeg_location=str(self.bin),ignoreerrors=False),str(folder),dict(format='video',_resume_target=True,_source_signature=source_checkpoint(before),_error=errors.append,_completed=completed.append))
  self.assertEqual(success,expected,errors)
  if expected:
   self.assertEqual(output.read_bytes(),self.body);self.assertTrue(any(r.startswith(f'bytes={middle}-') for r in self.requests[first:]));self.assertEqual(completed,[str(output)])
  else:
   self.assertFalse(output.exists());self.assertEqual(partial.read_bytes(),self.body[:middle]);self.assertFalse(completed);self.assertEqual(self.requests[first:],[])
 def test_same_strong_etag_resumes_exact_bytes_with_new_query(self):self.run_case('same','new',True)
 def test_changed_representation_preserves_partial_without_transfer(self):self.run_case('changed','changed',False)

if __name__=='__main__':unittest.main()
