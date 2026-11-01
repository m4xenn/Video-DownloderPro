"""Render and test guided setup against an isolated Flask client; no OS setup writes."""
import os,json,pathlib,sys
from urllib.parse import urlsplit
root=pathlib.Path(__file__).resolve().parents[1];folder=root/'build/companion-wizard-preview';folder.mkdir(exist_ok=True)
os.environ['VIDEO_DOWNLOADER_DATA_DIR']=str(folder/'profile')
sys.path.insert(0,str(root/'src'))
from services import companion_setup
state={'connected':False,'needs_update':False,'extension_id':companion_setup.extension_id(),'extension_version':json.loads((root/'browser-extension/manifest.json').read_text(encoding='utf-8'))['version'],'prepared':False,'package_ready':True,'folder':r'C:\Users\Example\AppData\Local\VideoDownloaderPro\BrowserExtension','browsers':[{'id':i,'name':n,'installed':True,'registered':False} for i,n in [('brave','Brave'),('chrome','Chrome'),('edge','Edge')]]}
actions=[]
def prepare(browser,consent):
 assert consent is True
 actions.append('prepare');state['prepared']=True
 for b in state['browsers']:b['registered']=b['id']==browser
 return state
companion_setup.status=lambda:state
companion_setup.prepare=prepare
companion_setup.open_browser=lambda browser:actions.append('browser')
companion_setup.open_folder=lambda:actions.append('folder')
import app
from utils import file_helpers
file_helpers.SETTINGS_FILE=str(folder/'settings.json');file_helpers.LEGACY_SETTINGS_FILE=str(folder/'legacy.json')
client=app.app.test_client()
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,chromium_sandbox=True)
 context=browser.new_context(viewport={'width':1360,'height':1000})
 page=context.new_page()
 def route(r):
  u=urlsplit(r.request.url)
  if u.hostname!='127.0.0.1':r.abort();return
  response=client.open(u.path+('?' + u.query if u.query else ''),method=r.request.method,data=r.request.post_data,headers={k:v for k,v in r.request.headers.items() if k.lower() in ('content-type','origin','sec-fetch-site')},base_url='http://127.0.0.1:18080')
  r.fulfill(status=response.status_code,content_type=response.content_type,body=response.data)
 context.route('**/*',route)
 page.add_init_script("localStorage.setItem('ytpro_lang','tr');localStorage.setItem('ytpro_welcome_version','999');")
 page.goto('http://127.0.0.1:18080/')
 # Dismiss the app's first-run welcome only in this isolated UI fixture.
 welcome=page.locator('#welcomeSkip')
 if welcome.is_visible():welcome.click()
 page.locator('[data-workspace="settings"]').click()
 page.locator('#companionPanel summary').click()
 page.get_by_role('button',name='Kurulumu hazırla',exact=True).wait_for()
 assert page.locator('#companionPrepare').is_disabled()
 page.locator('#companionConsent').check()
 page.locator('#companionPrepare').click()
 page.wait_for_function("document.getElementById('companionFolderPath').value.length>0")
 assert actions==['prepare'];assert page.locator('#companionOpen').is_enabled()
 page.locator('#companionOpen').click();page.wait_for_function("!document.getElementById('companionOpen').disabled")
 assert 'browser' in actions
 page.locator('#companionPanel').scroll_into_view_if_needed()
 page.screenshot(path=str(folder/'setup-tr.png'),full_page=True)
 locales=json.loads((root/'src/static/companion-locales.json').read_text(encoding='utf-8'))
 assert set(locales)=={'tr','en','de','fr','es','pt','ru','zh','ja','hi'}
 for lang,copy in locales.items():
  page.evaluate('(lang)=>setLanguage(lang)',lang)
  assert page.locator('[data-companion="title"]').inner_text()==copy['title']
  assert page.locator('[data-companion-step="2"]').inner_text()==copy['steps'][2]
  help_folder=root/'src/static/help'/lang;help_folder.mkdir(parents=True,exist_ok=True)
  page.screenshot(path=str(help_folder/'browser-extension.png'),full_page=True)
 state['connected']=True;page.locator('#companionCheck').click()
 page.wait_for_function("document.getElementById('companionBadge').textContent.includes('ready')||document.getElementById('companionBadge').textContent.length>0")
 page.evaluate("setLanguage('tr')")
 page.wait_for_function("document.getElementById('companionBadge').textContent.includes('Bağlandı')")
 page.screenshot(path=str(folder/'connected-tr.png'),full_page=True)
 browser.close()
print('Wizard: consent gate, setup action, browser page, copied folder, 10 languages and live connection status passed. OS registration mocked.')
