"""Rendered recovery UX, localization and shutdown state; isolated app data."""
import json,os,sys,time
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'build/recovery-ui';folder.mkdir(exist_ok=True)
profile=folder/('profile-'+str(time.time_ns()));profile.mkdir()
os.environ['VIDEO_DOWNLOADER_DATA_DIR']=str(profile);sys.path.insert(0,str(ROOT/'src'))
import app
from utils import file_helpers
file_helpers.SETTINGS_FILE=str(profile/'settings.json');file_helpers.LEGACY_SETTINGS_FILE=str(profile/'legacy.json')
from playwright.sync_api import sync_playwright
client=app.app.test_client();calls=[];errors=[]
item={'id':'recovered-job','url':'https://example.com/video','title':'Recovered video <img src=x onerror=alert(1)>','percent':64.2,'downloaded_bytes':45000000,'reason':'shutdown','error_code':'','ready':True,'is_live':False}
data={'status':'paused','items':[],'total_items':0,'restored_count':1,'recovery_items':[item],'shutting_down':False}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,chromium_sandbox=True)
 page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
 page.on('pageerror',lambda error:errors.append(str(error)))
 def route(r):
  u=urlsplit(r.request.url)
  if u.hostname!='127.0.0.1':r.abort();return
  if u.path=='/progress':r.fulfill(json=data);return
  if u.path=='/queue/recover':
   calls.append(json.loads(r.request.post_data));data['recovery_items']=[];data['restored_count']=0
   r.fulfill(json={'status':'success'});return
  response=client.open(u.path,method=r.request.method,data=r.request.post_data,headers={k:v for k,v in r.request.headers.items() if k.lower() in ('content-type','origin')},base_url='http://127.0.0.1:18082')
  r.fulfill(status=response.status_code,content_type=response.content_type,body=response.data)
 page.route('**/*',route)
 page.add_init_script("localStorage.setItem('ytpro_lang','tr');document.addEventListener('DOMContentLoaded',()=>document.body.dataset.welcomeSeen='true');")
 page.goto('http://127.0.0.1:18082/')
 page.wait_for_function("typeof updateRecoveryCenter==='function' && !!document.getElementById('recoveryTitle').textContent")
 page.evaluate('updateRecoveryCenter('+json.dumps(data)+')')
 page.locator('#recoveryCenter').wait_for(state='visible')
 assert page.locator('.workspace-content').get_attribute('data-view')=='queue'
 assert page.locator('#recoveryItems img').count()==0
 assert '<img' in page.locator('#recoveryItems strong').inner_text()
 for lang in ['tr','en','de','es','fr','pt','ru','zh','ja','hi']:
  page.evaluate('(lang)=>setLanguage(lang)',lang)
  assert page.locator('#recoveryTitle').inner_text()
  assert page.locator('#recoveryItems button').first.inner_text()
 page.evaluate("setLanguage('tr')")
 item['title']='Örnek video — kaldığın yerden devam et'
 data['items']=[dict(item,status='paused',format='video',quality='720p',speed='',total_bytes=70000000,size_estimated=True,eta=None)]
 data['total_items']=1
 page.evaluate('updateRecoveryCenter('+json.dumps(data)+')')
 page.evaluate('pollDownloadProgress()')
 page.screenshot(path=str(folder/'recovery-tr.png'),full_page=True)
 page.set_viewport_size({'width':900,'height':640})
 page.locator('#recoveryItems button').last.scroll_into_view_if_needed()
 box=page.locator('#recoveryItems button').last.bounding_box();assert box and box['y']>=0 and box['y']+box['height']<=640
 page.screenshot(path=str(folder/'recovery-small.png'),full_page=True)
 page.locator('#recoveryItems button').last.click()
 page.wait_for_function("document.getElementById('recoveryCenter').hidden")
 assert calls==[{'url':item['url'],'action':'refresh'}],calls
 data['recovery_items']=[dict(item,ready=False,reason='paused')]
 page.evaluate('updateRecoveryCenter('+json.dumps(data)+')')
 assert page.locator('#recoveryItems button').first.is_disabled()
 data['recovery_items']=[dict(item,is_live=True,reason='live')]
 page.evaluate('updateRecoveryCenter('+json.dumps(data)+')')
 assert page.locator('#recoveryItems button').count()==1
 assert 'şu andan' in page.locator('#recoveryItems').inner_text()
 page.evaluate('window.setShutdownState(true)')
 assert page.locator('#shutdownOverlay').is_visible()
 assert 'kaydediliyor' in page.locator('#shutdownMessage').inner_text()
 page.evaluate('window.setShutdownState(false,true)')
 assert 'kaydedilemedi' in page.locator('#shutdownMessage').inner_text()
 assert not errors,errors
 (folder/'result.json').write_text(json.dumps({'passed':True,'locales':10,'errors':errors,'refresh_action':calls,'checks':['restored queue auto-opens','safe text rendering','source refresh','small viewport','pending disable','live restart warning','shutdown save/failure']},indent=2))
 browser.close()
app.download_manager.close()
print('Recovery UI passed: ten locales, refresh payload, live/pending states, shutdown and responsive layout')
