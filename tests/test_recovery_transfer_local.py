"""Real process restart/kill and HTTP Range recovery with generated AV media."""
import hashlib,http.server,json,os,re,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from services.download_store import DownloadStore

CHILD = r"""
import json,sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from core.queue_manager import DownloadManager
from core.downloader import _download_single
from services.download_store import DownloadStore
import core.queue_manager as queue
# This subprocess owns the synthetic loopback fixture; no production bypass.
import services.secure_transport
services.secure_transport.attach_network_guard=lambda _:None
queue.show_notification=lambda *_:None
base=Path(sys.argv[2]);url=sys.argv[3];mode=sys.argv[4];tools=sys.argv[5]
def worker(url,opts,path,request,folder):
    opts.update(postprocessors=[],quiet=True,noprogress=True)
    request['_preview_dir']=None
    return _download_single(url,opts,path,request,folder)
m=DownloadManager(worker,store=DownloadStore(base/'queue.sqlite3'))
try:
    if mode=='start':
        m.configure('manual',1,100000)
        m.submit([url],{'format':'video','quality':'720p','embed_subs':False},str(base/'out'),tools)
        while m.busy() and not (base/'stop').exists():time.sleep(.02)
    else:
        m.restore();identity=m.jobs[0].id
        assert m.jobs[0].status=='paused'
        m.configure('manual',1,0);m.resume_restored()
        result=m.wait(45)
        assert result['status']=='finished_all',result
        (base/'result.json').write_text(json.dumps({'id':m.jobs[0].id,'restored_id':identity,'output':m.jobs[0].output_path,'history':m.store.history()['total']}))
finally:
    print('CHILD FINAL',m.snapshot(),flush=True)
    m.close()
"""
class RecoveryTransferTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tools=Path(os.environ['APPDATA'])/'YoutubePro/bin'
  if not (cls.tools/'ffmpeg.exe').is_file():raise unittest.SkipTest('FFmpeg missing')
  cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='recovery-transfer-');cls.base=Path(cls.temp.name)
  cls.media=cls.base/'source.mp4'
  subprocess.run([str(cls.tools/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=s=480x270:r=20','-f','lavfi','-i','sine=frequency=440','-t','12','-c:v','libx264','-preset','ultrafast','-b:v','1200k','-c:a','aac','-movflags','+faststart',str(cls.media)],check=True,timeout=30)
  cls.body=cls.media.read_bytes();cls.ranges=[]
  class Handler(http.server.BaseHTTPRequestHandler):
   def log_message(self,*_):pass
   def do_HEAD(self):self.send_media(False)
   def do_GET(self):self.send_media(True)
   def send_media(self,body):
    raw=self.headers.get('Range','');start=0;end=len(cls.body)-1
    if raw:
     match=re.fullmatch(r'bytes=(\d+)-(\d*)',raw)
     if not match:self.send_error(416);return
     start=int(match[1]);end=min(int(match[2]) if match[2] else end,end)
    if body:cls.ranges.append(start)
    if start>end:self.send_error(416);return
    self.send_response(206 if raw else 200);self.send_header('Content-Type','video/mp4')
    self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes');self.send_header('ETag','"synthetic-stable"')
    if raw:self.send_header('Content-Range',f'bytes {start}-{end}/{len(cls.body)}')
    self.end_headers()
    if body:
     try:
      for offset in range(start,end+1,16384):self.wfile.write(cls.body[offset:min(offset+16384,end+1)]);self.wfile.flush();time.sleep(.005)
     except (OSError,ConnectionError):pass
  cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.url=f'http://127.0.0.1:{cls.server.server_port}/source.mp4'
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown();cls.server.server_close();cls.thread.join(3);cls.temp.cleanup()
 def run_case(self,name,kill):
  base=self.base/name;base.mkdir();log=(base/'child.log').open('w',encoding='utf-8')
  env=dict(os.environ,VIDEO_DOWNLOADER_DATA_DIR=str(base/'profile'),PYTHONIOENCODING='utf-8')
  child=subprocess.Popen([sys.executable,'-u','-c',CHILD,str(ROOT/'src'),str(base),self.url,'start',str(self.tools)],stdout=log,stderr=subprocess.STDOUT,env=env)
  try:
   deadline=time.monotonic()+20
   while True:
    parts=list((base/'out').glob('*.part'))
    if parts and parts[0].stat().st_size>=65536:break
    log.flush();self.assertIsNone(child.poll(),(base/'child.log').read_text(encoding='utf-8',errors='replace'))
    self.assertLess(time.monotonic(),deadline);time.sleep(.02)
   store=DownloadStore(base/'queue.sqlite3');record=store.load_queue()[0]
   self.assertTrue(record['output_template']);self.assertTrue(record['source_signature'])
   if kill:child.kill()
   else:(base/'stop').touch()
   child.wait(20);self.assertTrue(parts[0].exists());offset=parts[0].stat().st_size
   self.assertGreater(offset,0);self.assertLess(offset,len(self.body))
   before=len(self.ranges)
   resumed=subprocess.run([sys.executable,'-u','-c',CHILD,str(ROOT/'src'),str(base),self.url,'resume',str(self.tools)],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=55)
   log.flush();self.assertEqual(resumed.returncode,0,(base/'child.log').read_text(encoding='utf-8',errors='replace'))
   result=json.loads((base/'result.json').read_text());self.assertEqual(result['id'],record['id']);self.assertEqual(result['history'],1)
   output=Path(result['output']);self.assertEqual(hashlib.sha256(output.read_bytes()).digest(),hashlib.sha256(self.body).digest())
   self.assertTrue(any(start>=offset for start in self.ranges[before:]),self.ranges[before:])
   self.assertEqual(len(list((base/'out').glob('*.mp4'))),1)
   probe=subprocess.run([str(self.tools/'ffprobe.exe'),'-v','error','-show_entries','stream=codec_type:format=duration','-of','json',str(output)],capture_output=True,text=True,check=True,timeout=15)
   details=json.loads(probe.stdout);self.assertEqual({s['codec_type'] for s in details['streams']},{'video','audio'})
   self.assertGreater(float(details['format']['duration']),11)
   print(name,'resumed from',offset,'of',len(self.body),'bytes; identical complete AV output')
  finally:
   if child.poll() is None:child.kill();child.wait(10)
   log.close()
 def test_graceful_close_then_new_process_resumes_bytes(self):self.run_case('graceful',False)
 def test_abrupt_kill_then_new_process_resumes_bytes(self):self.run_case('crash',True)

if __name__=='__main__':unittest.main()
