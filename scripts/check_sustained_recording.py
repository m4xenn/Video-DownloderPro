"""One-minute real-time HLS recording with isolated data and resource sampling."""
import functools,http.server,json,os,subprocess,sys,threading,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'build/performance/sustained';base.mkdir(parents=True,exist_ok=True)
assert not (base/'result.json').exists(),'Preserve the previous sustained recording report'
tools=Path(os.environ['APPDATA'])/'YoutubePro/bin'
os.environ.update(VIDEO_DOWNLOADER_DATA_DIR=str(base/'data'),LOCALAPPDATA=str(base/'local'))
sys.path.insert(0,str(ROOT/'src'))
from services.windows_sandbox import protect_workspace
from services.live_recording import record_live
from services.output_validation import validation_session,validate_output,_validate_output
import psutil
protect_workspace(base)
source=ROOT/'build/performance/baseline/source.mp4'
producer=subprocess.Popen([str(tools/'ffmpeg.exe'),'-v','error','-re','-stream_loop','-1','-i',str(source),'-c','copy','-f','hls','-hls_time','2','-hls_list_size','30',str(base/'source.m3u8')],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def copyfile(self,*args):
  try:return super().copyfile(*args)
  except (ConnectionResetError,ConnectionAbortedError,BrokenPipeError):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(base)))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
samples=[];events=[];done=threading.Event()
def sample():
 parent=psutil.Process()
 while not done.wait(1):
  children=[]
  for child in parent.children(recursive=True):
   if child.pid!=producer.pid:
    try:children.append(child.memory_info().rss)
    except psutil.NoSuchProcess:pass
  samples.append({'seconds':time.monotonic()-started,'parent_rss':parent.memory_info().rss,'media_rss':sum(children),'threads':parent.num_threads(),'handles':parent.num_handles()})
started=time.monotonic();monitor=threading.Thread(target=sample,daemon=True);monitor.start()
try:
 deadline=time.monotonic()+15
 while not (base/'source.m3u8').exists():
  assert producer.poll() is None,'Fixture producer exited'
  assert time.monotonic()<deadline,'Fixture playlist timeout'
  time.sleep(.1)
 info={'url':f'http://127.0.0.1:{server.server_port}/source.m3u8','is_live':True,'vcodec':'h264','acodec':'aac','protocol':'m3u8','ext':'mp4'}
 with patch('services.live_network.require_public_link',lambda value:value),patch('services.live_network.pin_requests_session',lambda value:value),patch('services.secure_transport.pin_requests_session',lambda value:value),patch('services.media_discovery.public_url',return_value=True),validation_session(),patch('services.output_validation._validate_output',wraps=_validate_output) as full:
  result=record_live(info,base/'recorded.mp4',str(tools),{'format':'video','live_record_minutes':1},lambda:False,lambda:False,events.append)
  checked=validate_output(base/'recorded.mp4',str(tools),True,expect_audio=True,include_duration=True,reuse_validation=True)
  assert full.call_count==1,full.call_count
  assert checked['audio'] and checked['video'] and 55<=checked['duration']<=62,checked
 assert len(samples)>=50,len(samples)
 stable=[s for s in samples if 15<=s['seconds']<=55]
 growth=stable[-1]['parent_rss']-stable[0]['parent_rss']
 assert growth<24*1024**2,('Parent memory growth exceeds 24 MiB',growth)
 report={'status':'passed','wall_seconds':time.monotonic()-started,'recorded_seconds':checked['duration'],'audio':checked['audio'],'video':checked['video'],'full_validations':1,'samples':samples,'steady_parent_growth_bytes':growth,'peak_media_rss':max(s['media_rss'] for s in samples),'output_bytes':(base/'recorded.mp4').stat().st_size}
 (base/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='samples'}))
finally:
 done.set();monitor.join(3)
 producer.terminate();producer.wait(timeout=5)
 producer.stderr.close()
 server.shutdown();server.server_close();thread.join(3)
