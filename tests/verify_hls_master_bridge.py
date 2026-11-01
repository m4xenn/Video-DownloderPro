"""Actual extension master correlation over a local HTTP fixture, no browser route mocks."""
import contextlib,functools,http.server,json,os,pathlib,shutil,sys,threading,time,winreg
from unittest.mock import patch
from urllib.parse import urlsplit
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from services.extension_bridge import ExtensionBridge
from services.generic_resolver import GenericResolver
from services.media_discovery import public_url
from playwright.sync_api import sync_playwright
base=ROOT/'build/hls-master-bridge';base.mkdir(exist_ok=True)
media=ROOT/'build/extension-brave-acceptance/synthetic.webm';assert media.is_file()
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  origin='http://vdp-fixture.localhost:'+str(self.server.server_port)
  assets={
   '/watch':('text/html',('<title>HLS master acceptance</title><video autoplay muted controls width="400" height="225"></video><script>fetch("'+origin+'/master.m3u8");fetch("'+origin+'/video.m3u8");fetch("'+origin+'/audio.m3u8");fetch("'+origin+'/media.webm").then(r=>r.blob()).then(b=>{const v=document.querySelector("video");v.src=URL.createObjectURL(b);v.play();});</script>').encode()),
   '/master.m3u8':('application/vnd.apple.mpegurl',b'#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",NAME="English",URI="audio.m3u8"\n#EXT-X-STREAM-INF:RESOLUTION=320x180,BANDWIDTH=100000,AUDIO="a"\nvideo.m3u8\n'),
   '/video.m3u8':('application/vnd.apple.mpegurl',b'#EXTM3U\n#EXTINF:65,\nmedia.webm\n#EXT-X-ENDLIST\n'),
   '/audio.m3u8':('application/vnd.apple.mpegurl',b'#EXTM3U\n#EXTINF:65,\nmedia.webm\n#EXT-X-ENDLIST\n'),
   '/media.webm':('video/webm',media.read_bytes())}
  if self.path not in assets:self.send_response(404);self.end_headers();return
  mime,body=assets[self.path];self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
origin='http://vdp-fixture.localhost:'+str(server.server_port)
def allowed(url,resolve=False):
 try:
  u=urlsplit(url)
  if u.hostname=='vdp-fixture.localhost' and u.port==server.server_port and u.scheme=='http':return True
 except ValueError:return False
 return public_url(url,resolve)
appdata=base/'appdata';os.environ['VIDEO_DOWNLOADER_DATA_DIR']=str(appdata/'YoutubePro')
b=ExtensionBridge();b.start();host_name='com.videodownloaderpro.masteracceptance';key=chr(92).join(('Software','Google','Chrome','NativeMessagingHosts',host_name));registered=False
fixture=base/'extension';shutil.copytree(ROOT/'browser-extension',fixture,dirs_exist_ok=True);p=fixture/'background.js';p.write_text(p.read_text(encoding='utf-8').replace('com.videodownloaderpro.bridge',host_name),encoding='utf-8')
report={}
try:
 with contextlib.ExitStack() as stack:
  stack.enter_context(patch('services.extension_bridge.public_url',side_effect=allowed));stack.enter_context(patch('services.generic_resolver.public_url',side_effect=allowed));stack.enter_context(patch('services.extension_bridge.extension_bridge',b))
  with sync_playwright() as p:
   context=p.chromium.launch_persistent_context(str(base/('profile-'+str(int(time.time())))),executable_path=r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe',headless=False,chromium_sandbox=True,args=[f'--disable-extensions-except={fixture}',f'--load-extension={fixture}'],env=dict(os.environ,APPDATA=str(appdata)))
   try:
    worker=context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker',timeout=15000);identity=worker.url.split('/')[2]
    try:
     with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key):raise RuntimeError('Existing test key preserved')
    except FileNotFoundError:pass
    manifest=base/'native-host.json';manifest.write_text(json.dumps({'name':host_name,'description':'Isolated master correlation test','path':str(ROOT/'dist/BrowserBridge/VDPBrowserBridge.exe'),'type':'stdio','allowed_origins':[f'chrome-extension://{identity}/']}))
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,key) as k:winreg.SetValueEx(k,'',0,winreg.REG_SZ,str(manifest))
    registered=True
    deadline=time.monotonic()+20
    while not b.available() and time.monotonic()<deadline:context.pages[0].wait_for_timeout(200)
    assert b.available();resolved=[];errors=[]
    def resolve():
     try:resolved.append(GenericResolver().details(origin+'/watch'))
     except Exception as e:errors.append(type(e).__name__)
    task=threading.Thread(target=resolve,daemon=True);task.start();deadline=time.monotonic()+25
    while task.is_alive() and time.monotonic()<deadline:context.pages[0].wait_for_timeout(200)
    assert resolved,errors
    assert resolved[0]['stream']==origin+'/master.m3u8'
    report={'status':'passed','browser':'isolated Brave','extension_version':json.loads((ROOT/'browser-extension/manifest.json').read_text(encoding='utf-8'))['version'],'observed_lists':3,'automatic_verified_master':'passed','native_bridge_and_generic_resolver':'passed','human_source_selection':False,'scope':'Synthetic blob playback and real HTTP manifest correlation; not a movie download. Local address allowance restricted to this fixture in test process.'}
   finally:context.close()
finally:
 if registered:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,key)
 b.close();server.shutdown();server.server_close();(base/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
