"""Isolated Chromium extension/native-host acceptance using synthetic media only."""
import pathlib,os,sys,json,time,threading,subprocess,winreg,shutil
from unittest.mock import patch
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from services.extension_bridge import ExtensionBridge
from services.generic_resolver import GenericResolver
from playwright.sync_api import sync_playwright
brave='--brave' in sys.argv
folder=root/('build/extension-brave-acceptance' if brave else 'build/extension-browser-acceptance');folder.mkdir(exist_ok=True)
profile=folder/('profile-'+str(int(time.time())));appdata=folder/'appdata';os.environ['VIDEO_DOWNLOADER_DATA_DIR']=str(appdata/'YoutubePro')
video=folder/'synthetic.webm'
ffmpeg=pathlib.Path(os.environ['APPDATA'])/'YoutubePro/bin/ffmpeg.exe'
if not video.exists():subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=blue:s=320x180:r=10','-t','65','-c:v','libvpx','-b:v','50k','-deadline','realtime',str(video)],check=True)
host_name='com.videodownloaderpro.acceptance'
fixture_extension=folder/'extension';shutil.copytree(root/'browser-extension',fixture_extension,dirs_exist_ok=True)
background=fixture_extension/'background.js';background.write_text(background.read_text(encoding='utf-8').replace('com.videodownloaderpro.bridge',host_name),encoding='utf-8')
b=ExtensionBridge();b.start();regpath=chr(92).join(('Software','Google','Chrome','NativeMessagingHosts',host_name));registered=False
result={}
blob_mode='--blob' in sys.argv
try:
 with sync_playwright() as p:
  context=p.chromium.launch_persistent_context(str(profile),**({'executable_path':r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe'} if brave else {}),headless=False,chromium_sandbox=True,args=[f'--disable-extensions-except={fixture_extension}',f'--load-extension={fixture_extension}'],env=dict(os.environ,APPDATA=str(appdata)))
  try:
   worker=context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker',timeout=15000)
   extension_id=worker.url.split('/')[2]
   try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,regpath):raise RuntimeError('Existing native host registration preserved; test stopped')
   except FileNotFoundError:pass
   manifest=folder/'native-host.json';manifest.write_text(json.dumps({'name':host_name,'description':'Isolated test','path':str(root/'dist/BrowserBridge/VDPBrowserBridge.exe'),'type':'stdio','allowed_origins':[f'chrome-extension://{extension_id}/']}),encoding='utf-8')
   with winreg.CreateKey(winreg.HKEY_CURRENT_USER,regpath) as key:winreg.SetValueEx(key,'',0,winreg.REG_SZ,str(manifest))
   registered=True
   page_url='https://example.com/vdp-bridge-test'
   def route(r):
    print('fixture request',r.request.url,flush=True)
    if r.request.url==page_url:
     html='<title>VDP synthetic acceptance</title><video autoplay muted controls width="400" height="225" src="https://example.com/vdp-synthetic.webm"></video>'
     if blob_mode:html='<title>VDP blob acceptance</title><video autoplay muted controls width="400" height="225"></video><script>fetch("https://example.com/vdp-test-playlist.m3u8");fetch("https://example.com/vdp-synthetic.webm").then(r=>r.blob()).then(b=>{const v=document.querySelector("video");v.src=URL.createObjectURL(b);v.play();});</script>'
     r.fulfill(status=200,content_type='text/html',body=html)
    elif r.request.url=='https://example.com/vdp-test-playlist.m3u8':r.fulfill(status=200,content_type='application/vnd.apple.mpegurl',body='#EXTM3U\n#EXTINF:65,\nvdp-synthetic.webm\n#EXT-X-ENDLIST\n')
    elif r.request.url=='https://example.com/vdp-synthetic.webm':r.fulfill(status=200,content_type='video/webm',body=video.read_bytes())
    else:r.abort()
   context.route('**/*',route)
   deadline=time.monotonic()+30
   while not b.available() and time.monotonic()<deadline:time.sleep(.2)
   if not b.available():raise RuntimeError('Native host did not connect')
   result['native_connection']='passed'
   expected_version=json.loads((root/'browser-extension/manifest.json').read_text())['version']
   assert b.client_connected(extension_id,expected_version)
   result['current_version_status']='passed'
   resolved=[];errors=[]
   def resolve():
    try:
     with patch('services.extension_bridge.extension_bridge',b):resolved.append(GenericResolver().details(page_url))
    except Exception as e:errors.append(type(e).__name__)
   thread=threading.Thread(target=resolve,daemon=True);thread.start()
   fixture_page=context.wait_for_event('page',timeout=15000)
   fixture_page.goto(page_url,wait_until='domcontentloaded')
   deadline=time.monotonic()+30
   while thread.is_alive() and time.monotonic()<deadline:
    # Browser event dispatch continues while the application worker waits.
    context.pages[0].wait_for_timeout(200)
   if not resolved:
    result['browser_state']=worker.evaluate("async()=>({stored:await chrome.storage.session.get('jobs')})")
    result['pages']=[{'url':page.url,'title':page.title(),'body':page.locator('body').inner_text()[:250],'videos':page.evaluate("()=>[...document.querySelectorAll('video')].map(v=>({paused:v.paused,duration:String(v.duration),error:v.error?.code,source:v.currentSrc}))")} for page in context.pages]
    raise RuntimeError('No automatic source handoff: '+','.join(errors))
   assert resolved[0]['stream']==('https://example.com/vdp-test-playlist.m3u8' if blob_mode else 'https://example.com/vdp-synthetic.webm')
   if blob_mode:assert resolved[0]['source_types'][resolved[0]['stream']]=='hls'
   assert resolved[0]['discovery_method']=='extension'
   result.update(status='passed',browser='isolated Brave' if brave else 'isolated Chromium',media='synthetic 65-second WebM',automatic_source_handoff='passed',blob_hls=blob_mode,app_generic_resolver='passed',personal_profile_used=False)
  finally:context.close()
finally:
 if registered:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,regpath)
 b.close()
 (folder/('result-blob.json' if blob_mode else 'result.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
