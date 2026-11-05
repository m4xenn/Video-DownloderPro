"""Real wall-clock recording endurance. Local synthetic media, bounded disk/logs."""
import argparse,functools,http.server,json,os,subprocess,sys,threading,time,hashlib
from collections import deque
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--minutes',type=int,default=240);parser.add_argument('--label',default='four-hour')
 args=parser.parse_args();assert 1<=args.minutes<=1440 and args.label.replace('-','').isalnum()
 base=ROOT/'build/stability'/args.label;assert not base.exists(),'Preserve previous endurance evidence'
 base.mkdir(parents=True)
 tools=Path(os.environ['APPDATA'])/'YoutubePro/bin'
 os.environ.update(VIDEO_DOWNLOADER_DATA_DIR=str(base/'data'),APPDATA=str(base/'appdata'),LOCALAPPDATA=str(base/'local'))
 sys.path.insert(0,str(ROOT/'src'))
 from services.windows_sandbox import protect_workspace
 from services.live_recording import record_live
 from services.output_validation import validation_session,validate_output
 import psutil
 protect_workspace(base)
 # Generate continuous timestamps: looping a multiplexed MP4 with unequal audio
 # and video durations introduces periodic DTS collisions into the test source.
 producer=subprocess.Popen([str(tools/'ffmpeg.exe'),'-v','error','-re','-f','lavfi','-i','testsrc2=s=426x240:r=24','-re','-f','lavfi','-i','sine=frequency=440',
  '-t',str(args.minutes*60+60),'-c:v','libx264','-preset','veryfast','-b:v','280k','-maxrate','320k','-bufsize','640k','-g','48','-c:a','aac','-b:a','64k','-f','hls','-hls_time','2',
  '-hls_list_size','60','-hls_flags','delete_segments',str(base/'source.m3u8')],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 producer_errors=deque(maxlen=8)
 def drain_producer():
  while chunk:=producer.stderr.read(4096):producer_errors.append(chunk.decode('utf-8','replace'))
 producer_reader=threading.Thread(target=drain_producer,daemon=True);producer_reader.start()
 class Handler(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
  def copyfile(self,*a):
   try:return super().copyfile(*a)
   except (ConnectionResetError,ConnectionAbortedError,BrokenPipeError):pass
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(base)))
 serving=threading.Thread(target=server.serve_forever,daemon=True);serving.start()
 events=deque(maxlen=4);samples=[];done=threading.Event();started=time.monotonic()
 modules=['live_recording','live_completion','live_network','live_catchup','media_process','windows_sandbox','output_validation']
 hashes={n:hashlib.sha256((ROOT/'src/services'/f'{n}.py').read_bytes()).hexdigest() for n in modules}
 report={'status':'running','minutes':args.minutes,'source_hashes':hashes,'samples':samples}
 def save():
  report['wall_seconds']=time.monotonic()-started
  report['latest_recorded_seconds']=next((e['recorded_seconds'] for e in reversed(events) if 'recorded_seconds' in e),report.get('latest_recorded_seconds',0))
  report['producer_returncode']=producer.poll();report['producer_stderr_tail']=list(producer_errors)
  temporary=base/'status.tmp';temporary.write_text(json.dumps(report,indent=2),encoding='utf-8');os.replace(temporary,base/'result.json')
 def monitor():
  parent=psutil.Process()
  while not done.wait(15):
   media=[]
   for child in parent.children(recursive=True):
    if child.pid!=producer.pid:
     try:media.append(child.memory_info().rss)
     except psutil.NoSuchProcess:pass
   samples.append({'seconds':time.monotonic()-started,'rss':parent.memory_info().rss,'media_rss':sum(media),'threads':parent.num_threads(),'handles':parent.num_handles()})
   save()
 watching=threading.Thread(target=monitor,daemon=True);watching.start();save()
 try:
  deadline=time.monotonic()+20
  while not (base/'source.m3u8').exists():
   assert producer.poll() is None and time.monotonic()<deadline,'Fixture playlist unavailable'
   time.sleep(.1)
  info={'url':f'http://127.0.0.1:{server.server_port}/source.m3u8','is_live':True,'vcodec':'h264','acodec':'aac','protocol':'m3u8','ext':'mp4'}
  with patch('services.live_network.require_public_link',lambda value:value),patch('services.live_network.pin_requests_session',lambda value:value),patch('services.secure_transport.pin_requests_session',lambda value:value),patch('services.media_discovery.public_url',lambda *a,**k:True),validation_session():
   report['recorder_result']=record_live(info,base/'recorded.mp4',str(tools),{'format':'video','live_record_minutes':args.minutes},lambda:False,lambda:False,events.append)
   verified=validate_output(base/'recorded.mp4',str(tools),True,expect_audio=True,include_duration=True,reuse_validation=True)
  assert verified['video'] and verified['audio'] and abs(verified['duration']-args.minutes*60)<3,verified
  steady=[s for s in samples if 300<=s['seconds']<=args.minutes*60-15]
  growth=steady[-1]['rss']-steady[0]['rss'] if len(steady)>1 else 0
  assert growth<32*1024**2,('Parent memory growth',growth)
  # Strict full decode, not merely container metadata/tail validation.
  decoded=subprocess.run([str(tools/'ffmpeg.exe'),'-nostdin','-v','error','-xerror','-i',str(base/'recorded.mp4'),'-map','0:v:0','-map','0:a:0','-f','null','-'],capture_output=True,timeout=max(60,args.minutes*20))
  assert decoded.returncode==0 and not decoded.stderr.strip(),decoded.stderr[-2000:]
  assert hashes=={n:hashlib.sha256((ROOT/'src/services'/f'{n}.py').read_bytes()).hexdigest() for n in modules},'Recorder changed during endurance; repeat with final code'
  report.update(status='passed',recorded_seconds=verified['duration'],steady_growth_bytes=growth,full_decode=True,output_bytes=(base/'recorded.mp4').stat().st_size)
 except BaseException as error:
  report.update(status='failed',error=str(error),recorder_diagnostics=getattr(error,'recording_diagnostics',{}));raise
 finally:
  done.set();watching.join(3);save()
  if producer.poll() is None:producer.terminate()
  producer.wait(timeout=10);producer_reader.join(3);producer.stderr.close();server.shutdown();server.server_close();serving.join(3)
 print(json.dumps({k:v for k,v in report.items() if k!='samples'}))

if __name__=='__main__':main()
