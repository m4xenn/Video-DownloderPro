"""Real isolated multi-file queue, filename collision and history acceptance."""
import functools,http.server,os,json,sys,threading,subprocess,time,hashlib
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'build/field-acceptance-2026-11-15/queue';assert not base.exists(),'Preserve evidence'
base.mkdir(parents=True);tools=Path(os.environ['APPDATA'])/'YoutubePro/bin'
os.environ.update(APPDATA=str(base/'profile/appdata'),LOCALAPPDATA=str(base/'profile/local'),VIDEO_DOWNLOADER_DATA_DIR=str(base/'profile/data'))
sys.path.insert(0,str(ROOT/'src'))
subprocess.run([str(tools/'ffmpeg.exe'),'-v','error','-f','lavfi','-i','testsrc2=s=160x90:r=24','-f','lavfi','-i','sine=frequency=440','-t','2','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(base/'sample.mp4')],check=True,timeout=30)
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(base)))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
from core.queue_manager import DownloadManager
from services.download_store import DownloadStore
from services.output_validation import validate_output
store=DownloadStore(base/'queue.sqlite');manager=DownloadManager(store=store)
started=time.monotonic();result={'status':'running','jobs':50};(base/'result.json').write_text(json.dumps(result))
try:
 with patch('services.secure_transport.attach_network_guard',lambda _:None),patch('core.queue_manager.show_notification',lambda *a:None):
  manager.configure('manual',3)
  manager.submit([f'http://127.0.0.1:{server.server_port}/sample.mp4?batch={n}' for n in range(50)],{'format':'video','quality':'max','embed_subs':False},str(base/'outputs'),str(tools))
  outcome=manager.wait(600);assert outcome['status']=='finished_all',[(j.error_code,j.error) for j in manager.jobs if j.status=='error']
  entries=store.history(limit=100)['items'];assert len(entries)==50
  paths=[Path(e['path']) for e in entries];assert len(set(paths))==50
  for path in paths:
   checked=validate_output(path,str(tools),True,expect_audio=True,include_duration=True)
   assert checked['video'] and checked['audio'] and 1.5<checked['duration']<2.5
  manager.close()
  restored=DownloadManager(store=store)
  try:restored.restore();assert restored.store.history()['total']==50
  finally:restored.close()
  result.update(status='passed',seconds=time.monotonic()-started,unique_outputs=50,validated_audio_video=50,history_after_restart=50)
except BaseException as error:result.update(status='failed',error=str(error));raise
finally:
 manager.close();server.shutdown();server.server_close();thread.join(3)
 (base/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
