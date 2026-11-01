"""User-initiated companion setup using bundled assets; no Python/PowerShell required."""
import base64,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
from services.extension_bridge import HOST_NAME,extension_bridge

BROWSERS={
 'brave':('Brave','brave','BraveSoftware/Brave-Browser/Application/brave.exe',r'Software\Google\Chrome\NativeMessagingHosts'),
 'chrome':('Chrome','chrome','Google/Chrome/Application/chrome.exe',r'Software\Google\Chrome\NativeMessagingHosts'),
 'edge':('Edge','edge','Microsoft/Edge/Application/msedge.exe',r'Software\Microsoft\Edge\NativeMessagingHosts'),
}
def resource_root():
 return Path(sys._MEIPASS) if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[2]
def install_root():
 return Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'VideoDownloaderPro'
def extension_source():return resource_root()/'browser-extension'
def host_source():
 return resource_root()/('browser-bridge/VDPBrowserBridge.exe' if getattr(sys,'frozen',False) else 'dist/BrowserBridge/VDPBrowserBridge.exe')
def extension_id():
 manifest=json.loads((extension_source()/'manifest.json').read_text(encoding='utf-8'))
 key=base64.b64decode(manifest['key'],validate=True)
 return ''.join(chr(ord('a')+int(c,16)) for c in hashlib.sha256(key).hexdigest()[:32])
def browser_exe(browser):
 if browser not in BROWSERS:raise ValueError('invalid_browser')
 suffix=BROWSERS[browser][2]
 for env in ('ProgramFiles','ProgramFiles(x86)','LOCALAPPDATA'):
  base=os.environ.get(env)
  if base:
   p=Path(base)/suffix
   if p.is_file():return p
 return None
def manifest_path():return install_root()/'BrowserBridge'/f'{HOST_NAME}.json'
def registry_path(browser):
 if browser not in BROWSERS:raise ValueError('invalid_browser')
 return BROWSERS[browser][3]+chr(92)+HOST_NAME

def registered(browser):
 try:
  import winreg
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry_path(browser)) as key:value=winreg.QueryValueEx(key,'')[0]
  p=manifest_path()
  if Path(value).resolve()!=p.resolve():return False
  data=json.loads(p.read_text(encoding='utf-8'))
  return ('chrome-extension://'+extension_id()+'/' in data.get('allowed_origins',[]) and Path(data.get('path','')).resolve()==(p.parent/'VDPBrowserBridge.exe').resolve() and (p.parent/'VDPBrowserBridge.exe').is_file())
 except (ImportError,OSError,ValueError,KeyError):return False

def status():
 folder=install_root()/'BrowserExtension'
 version=json.loads((extension_source()/'manifest.json').read_text(encoding='utf-8'))['version']
 connected=extension_bridge.client_connected(extension_id(),version)
 return {'connected':connected,'needs_update':extension_bridge.available() and not connected,'extension_id':extension_id(),
  'extension_version':version,
  'folder':str(folder),'prepared':(folder/'manifest.json').is_file(),
  'package_ready':host_source().is_file(),
  'browsers':[{'id':b,'name':v[0],'installed':browser_exe(b) is not None,'registered':registered(b)} for b,v in BROWSERS.items()]}

def prepare(browser,consent):
 if browser not in BROWSERS:raise ValueError('invalid_browser')
 if consent is not True:raise ValueError('consent_required')
 if browser_exe(browser) is None:raise ValueError('browser_missing')
 exe=host_source()
 if not exe.is_file():raise ValueError('package_incomplete')
 source=extension_source();identity=extension_id()
 folder=install_root()/'BrowserExtension';host=manifest_path();host.parent.mkdir(parents=True,exist_ok=True)
 shutil.copytree(source,folder,dirs_exist_ok=True)
 target=host.parent/'VDPBrowserBridge.exe'
 if not target.is_file() or hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256(exe.read_bytes()).digest():
  temporary=target.with_suffix('.new')
  try:shutil.copy2(exe,temporary);os.replace(temporary,target)
  finally:
   if temporary.exists():temporary.unlink()
 origins={'chrome-extension://'+identity+'/'}
 if host.exists():
  previous=json.loads(host.read_text(encoding='utf-8'))
  if previous.get('name')!=HOST_NAME:raise ValueError('manifest_conflict')
  origins.update(o for o in previous.get('allowed_origins',[]) if isinstance(o,str) and re.fullmatch(r'chrome-extension://[a-p]{32}/',o))
 data={'name':HOST_NAME,'description':'Video Downloader Pro companion','path':str(target),'type':'stdio','allowed_origins':sorted(origins)}
 temporary=host.with_suffix('.new');temporary.write_text(json.dumps(data,indent=2),encoding='utf-8');os.replace(temporary,host)
 import winreg
 with winreg.CreateKey(winreg.HKEY_CURRENT_USER,registry_path(browser)) as key:winreg.SetValueEx(key,'',0,winreg.REG_SZ,str(host))
 return status()

def open_browser(browser):
 if browser not in BROWSERS:raise ValueError('invalid_browser')
 executable=browser_exe(browser)
 if executable is None:raise ValueError('browser_missing')
 subprocess.Popen([str(executable),'--new-window',BROWSERS[browser][1]+'://extensions/'])
def open_folder():
 folder=install_root()/'BrowserExtension'
 if not (folder/'manifest.json').is_file():raise ValueError('prepare_first')
 os.startfile(str(folder))
