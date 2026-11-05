"""Repeatable local pipeline/startup measurements using isolated app profiles.

Network guards are bypassed ONLY inside this developer fixture's owned-loopback
pipeline. Frozen startup keeps production guards; no personal data is opened.
"""
import argparse, functools, http.server, json, os, statistics, subprocess, sys, threading, time
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def activate_archive(executable):
 """Load the five changed modules from a trusted local benchmark EXE.

 This lets both variants run under the same source harness without reverting
 working files. The archive must use this interpreter's Python bytecode version.
 """
 import importlib.abc,importlib.util
 from PyInstaller.archive.readers import CArchiveReader
 archive=CArchiveReader(str(Path(executable).resolve())).open_embedded_archive('PYZ.pyz')
 names={'app','core.queue_manager','core.downloader','services.output_validation','services.live_recording'}
 class Loader(importlib.abc.Loader):
  def create_module(self,spec):return None
  def exec_module(self,module):
   module.__file__=str(ROOT/'src'/Path(*module.__name__.split('.')).with_suffix('.py'))
   exec(archive.extract(module.__name__),module.__dict__)
 class Finder(importlib.abc.MetaPathFinder):
  def find_spec(self,fullname,path=None,target=None):
   if fullname in names:return importlib.util.spec_from_loader(fullname,Loader(),origin=str(ROOT/'src'/Path(*fullname.split('.')).with_suffix('.py')))
 sys.meta_path.insert(0,Finder())


def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--label',required=True)
 parser.add_argument('--runs',type=int,default=3)
 parser.add_argument('--exe')
 parser.add_argument('--source',help='Reuse identical synthetic media from the baseline')
 parser.add_argument('--engine-exe',help='Use the changed modules from this trusted local EXE for a controlled before/after comparison')
 args=parser.parse_args()
 assert args.label.replace('-','').isalnum() and 1<=args.runs<=10
 base=ROOT/'build/performance'/args.label;base.mkdir(parents=True,exist_ok=True)
 assert not (base/'result.json').exists(),'Preserve previous measurements; choose another label'
 profile=base/'profile';tools=profile/'appdata/YoutubePro/bin';tools.mkdir(parents=True,exist_ok=True)
 original=Path(os.environ['APPDATA'])/'YoutubePro/bin'
 for name in ('ffmpeg.exe','ffprobe.exe'):
  target=tools/name
  if not target.exists():os.link(original/name,target)
 env=dict(os.environ,APPDATA=str(profile/'appdata'),LOCALAPPDATA=str(profile/'local'),VIDEO_DOWNLOADER_DATA_DIR=str(profile/'data'))
 os.environ.update({key:env[key] for key in ('APPDATA','LOCALAPPDATA','VIDEO_DOWNLOADER_DATA_DIR')})
 sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
 from utils import file_helpers
 file_helpers.SETTINGS_FILE=str(profile/'settings.json');file_helpers.LEGACY_SETTINGS_FILE=str(profile/'legacy.json')
 file_helpers.save_settings_to_file({'notification_mode':'never','language':'en'})
 prefix=''
 if args.engine_exe:
  activate_archive(args.engine_exe)
  prefix="import sys;sys.path.insert(0,"+repr(str(ROOT/'scripts'))+");from benchmark_performance import activate_archive;activate_archive("+repr(str(Path(args.engine_exe).resolve()))+");"
 code=prefix+"import time,json,sys;start=time.perf_counter();import app;print(json.dumps({'app_import_seconds':time.perf_counter()-start}))"
 imports=[]
 for i in range(args.runs):
  with (base/f'import-{i}.log').open('w',encoding='utf-8') as log:
   started=time.perf_counter();run=subprocess.run([sys.executable,'-X','importtime','-c',code],env=env,capture_output=False,stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=40)
  imports.append(dict(json.loads(run.stdout.strip().splitlines()[-1]),process_seconds=time.perf_counter()-started))
 report={'label':args.label,'runs':args.runs,'python':sys.version,'engine_exe':args.engine_exe,'imports':imports,'pipeline':[],'startup':[]}
 def save():
  (base/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 save()
 if args.exe:
  import types,psutil
  assert not any((p.info['name'] or '').lower()=='youtubepro.exe' for p in psutil.process_iter(['name'])),'Do not interrupt an existing app'
  helper=types.ModuleType('startup_benchmark');helper.__file__=str(ROOT/'scripts/check_installed_runtime.py')
  exec(compile(Path(helper.__file__).read_text(encoding='utf-8'),helper.__file__,'exec'),helper.__dict__)
  helper.EXE=Path(args.exe).resolve();helper.PROFILE=profile/'native'
  for i in range(args.runs):
   started=time.perf_counter();process,url=helper.launch()
   try:
    from urllib.request import urlopen
    response=json.load(urlopen(url+'/get-settings',timeout=5))
    report['startup'].append({'api_ready_seconds':time.perf_counter()-started})
   finally:helper.stop(process)
   save()
 from core.queue_manager import DownloadManager,Job
 from services.download_store import DownloadStore
 import services.site_resolver as resolver
 import services.output_validation as validation
 import services.preview_service as previews
 import services.malware_scan as scanner
 from services.diagnostics import Diagnostics
 import services.media_process as media_process
 import psutil
 media=base/'source.mp4'
 if args.source and not media.exists():os.link(Path(args.source).resolve(),media)
 if not media.exists():
  subprocess.run([str(tools/'ffmpeg.exe'),'-v','error','-f','lavfi','-i','testsrc2=s=1280x720:r=24','-f','lavfi','-i','sine=frequency=440','-t','30','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(media)],check=True,timeout=90)
 class Handler(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
  def copyfile(self,*args):
   try:return super().copyfile(*args)
   except (ConnectionResetError,ConnectionAbortedError,BrokenPipeError):pass  # Media probes may close after a prefix.
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(base)))
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 active={};phase_times=[]
 def measured(name,original):
  def call(*a,**kw):
   started=time.perf_counter()
   try:return original(*a,**kw)
   finally:active.setdefault(name,[]).append(time.perf_counter()-started)
  return call
 try:
  with patch('services.secure_transport.attach_network_guard',lambda ydl:None),patch('core.queue_manager.show_notification'),patch('services.diagnostics.diagnostics',Diagnostics(base/'diagnostics.sqlite3')):
   for kind,quality in [('video','max'),('audio','mp3')]:
    for i in range(args.runs):
     active={};starts=[];finished=[];native_calls=[]
     manager=DownloadManager(store=DownloadStore(base/f'{kind}-{i}.sqlite3'))
     url=f'http://127.0.0.1:{server.server_port}/source.mp4'
     job=Job(url,{'format':kind,'quality':quality},str(base/'output'),str(tools));manager.jobs=[job]
     def process_started(self,*a,**kw):
      native_calls.append(Path(a[0][0]).name.lower())
      return original_execute(self,*a,**kw)
     original_execute=media_process.MediaPopen._execute_child
     before=psutil.Process().memory_info().rss
     started=time.perf_counter()
     try:
      with patch.object(resolver,'extract_media_info',measured('metadata',resolver.extract_media_info)),patch.object(validation,'validate_output',measured('validation',validation.validate_output)),patch.object(previews,'create_preview',measured('preview',previews.create_preview)),patch.object(scanner,'scan_file',measured('scan',scanner.scan_file)),patch.object(media_process.MediaPopen,'_execute_child',process_started):
       assert manager._execute(job),job.error
      manager._finished(job);manager._persist(required=True)
      report['pipeline'].append({'format':kind,'total_seconds':time.perf_counter()-started,'stages':{k:{'calls':len(v),'seconds':sum(v)} for k,v in active.items()},'native_calls':native_calls,'bytes':Path(job.output_path).stat().st_size,'rss_delta_bytes':psutil.Process().memory_info().rss-before,'security_status':job.security_status})
      print(json.dumps(report['pipeline'][-1]),flush=True);save()
     finally:manager.jobs=[];manager.close()
 finally:server.shutdown();server.server_close();thread.join(3)
 report['medians']={'app_import_seconds':statistics.median(v['app_import_seconds'] for v in imports)}
 for kind in ('video','audio'):
  rows=[r for r in report['pipeline'] if r['format']==kind]
  report['medians'][kind+'_seconds']=statistics.median(r['total_seconds'] for r in rows)
 if report['startup']:report['medians']['api_ready_seconds']=statistics.median(v['api_ready_seconds'] for v in report['startup'])
 save();print(json.dumps(report['medians']))


if __name__=='__main__':main()
