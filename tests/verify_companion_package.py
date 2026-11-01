"""Smoke-test the frozen companion setup without writing any native-host registry keys."""
import argparse,os,json,pathlib,time,subprocess,sys,struct,hashlib,psutil
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
root=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--exe',default=str(root/'build/companion-packaging/dist/YoutubePro/YoutubePro.exe'));args=parser.parse_args()
exe=pathlib.Path(args.exe);internal=exe.parent/'_internal';folder=root/'build/companion-package-runtime';folder.mkdir(exist_ok=True)
profile=folder/('profile-'+str(int(time.time())));profile.mkdir()
manifest=json.loads((internal/'browser-extension/manifest.json').read_text(encoding='utf-8'))
assert manifest['key'] and manifest['icons']['128']=='icons/icon-128.png'
for n in (16,32,48,128):assert (internal/f'browser-extension/icons/icon-{n}.png').is_file()
for lang in ('tr','en','de','es','fr','pt','ru','zh','ja','hi'):
 assert (internal/f'static/help/{lang}/browser-extension.png').is_file()
 assert (internal/f'static/help/{lang}/live-recording.png').is_file()
assert (internal/'static/download-tools.js').is_file()
host=internal/'browser-bridge/VDPBrowserBridge.exe';assert host.is_file()
assert hashlib.sha256(host.read_bytes()).digest()==hashlib.sha256((root/'dist/BrowserBridge/VDPBrowserBridge.exe').read_bytes()).digest()
env=dict(os.environ,APPDATA=str(profile),LOCALAPPDATA=str(profile/'local'),VIDEO_DOWNLOADER_DATA_DIR=str(profile/'YoutubePro'))
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
process=subprocess.Popen([str(exe)],env=env,startupinfo=startup)
report={'scope':'Frozen app, isolated user data, no actual registry writes','checks':[]}
def api(base,path,payload):
 try:
  with urlopen(Request(base+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=4) as r:return r.status,json.load(r)
 except HTTPError as e:return e.code,json.load(e)
try:
 deadline=time.monotonic()+45;base=None
 while time.monotonic()<deadline and not base:
  assert process.poll() is None,'Frozen app exited'
  for c in psutil.Process(process.pid).net_connections(kind='tcp'):
   if c.status==psutil.CONN_LISTEN and c.laddr.ip=='127.0.0.1':
    candidate='http://127.0.0.1:'+str(c.laddr.port)
    try:
     code,data=api(candidate,'/browser-companion/status',{})
     if code==200 and data.get('status')=='success':base=candidate;break
    except (OSError,ValueError):pass
  time.sleep(.2)
 assert base,'Frozen setup API unavailable'
 with urlopen(base+'/get-settings',timeout=4) as response:settings=json.load(response)
 assert settings['transfer_mode']=='stable'
 for endpoint in ('/recording/finish','/browser-companion/focus'):
  code,error=api(base,endpoint,{'url':'https://example.com/not-an-active-job'})
  assert code==409,(endpoint,code,error)
 report['checks'].append('Download controls, ten live guide images, stable transfer default and new guarded APIs present in frozen app')
 report['checks'].append('Bundled extension, icons, ten localized help images, native executable and live setup API present')
 assert data['package_ready'] and not data['prepared']
 code,error=api(base,'/browser-companion/action',{'action':'prepare','browser':'brave','consent':False})
 assert code==400 and error['code']=='consent_required'
 assert not (profile/'local/VideoDownloaderPro').exists()
 report['checks'].append('No local registration/files written without consent')
 payload=json.dumps({'type':'poll','extension_id':data['extension_id'],'version':manifest['version']}).encode()
 completed=subprocess.run([str(host)],input=struct.pack('<I',len(payload))+payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,startupinfo=startup,timeout=8)
 length=struct.unpack('<I',completed.stdout[:4])[0];reply=json.loads(completed.stdout[4:4+length]);assert reply['jobs']==[] and reply['language'] in ('tr','en','de','es','fr','pt','ru','zh','ja','hi')
 code,state=api(base,'/browser-companion/status',{});assert state['connected']
 report['checks'].append('Bundled native executable exchanges real stdio frames with frozen bridge; current-version status updates')
 report['status']='passed'
finally:
 try:
  children=psutil.Process(process.pid).children(recursive=True)
  for child in reversed(children):
   try:child.terminate()
   except psutil.Error:pass
  process.terminate();process.wait(timeout=10);psutil.wait_procs(children,timeout=5)
 except (psutil.Error,ProcessLookupError):pass
 (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
