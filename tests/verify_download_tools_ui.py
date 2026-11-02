"""Own-app UI acceptance and ten localized guide captures; no real downloads or OS writes."""
import json,os,time
from pathlib import Path
import sys
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'build/download-tools-ui';folder.mkdir(exist_ok=True)
profile=folder/'profiles'/str(time.time_ns());profile.mkdir(parents=True)
os.environ['VIDEO_DOWNLOADER_DATA_DIR']=str(profile)
sys.path.insert(0,str(ROOT/'src'))
import app
from utils import file_helpers
from state.app_state import state
file_helpers.SETTINGS_FILE=str(profile/'settings.json');file_helpers.LEGACY_SETTINGS_FILE=str(profile/'legacy.json')
state['current_download_path']=r'C:\Videos'
client=app.app.test_client();submissions=[];focused=[];finished=[];pending=[]
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,chromium_sandbox=True)
 context=browser.new_context(viewport={'width':1440,'height':1080},device_scale_factor=1)
 page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
 def route(r):
  u=urlsplit(r.request.url)
  if u.hostname!='127.0.0.1':r.abort();return
  if u.path=='/source-progress':r.fulfill(json={'phase':'browser_extension' if pending else ''});return
  if u.path=='/get-info':
   data=json.loads(r.request.post_data)
   if data['url'].endswith('/await-play'):pending.append(r);return
   live='live' in data['url'];partial='partial' in data['url']
   r.fulfill(json=dict(status='success',url=data['url'],title='Synthetic live stream' if live else 'Synthetic source',thumbnail='',video_qualities=[],audio_languages=['en','tr'],subtitle_languages=['en','tr'],is_live=live,source_status='partial' if partial else 'unknown',is_playlist=False));return
  if u.path=='/download':submissions.append(json.loads(r.request.post_data));r.fulfill(json={'status':'success'});return
  if u.path=='/recording/finish':finished.append(json.loads(r.request.post_data));r.fulfill(json={'status':'success'});return
  if u.path=='/browser-companion/focus':focused.append(json.loads(r.request.post_data));r.fulfill(json={'status':'success'});return
  response=client.open(u.path+('?' + u.query if u.query else ''),method=r.request.method,data=r.request.post_data,
       headers={k:v for k,v in r.request.headers.items() if k.lower() in ('content-type','origin','sec-fetch-site')},base_url='http://127.0.0.1:18081')
  r.fulfill(status=response.status_code,content_type=response.content_type,body=response.data)
 context.route('**/*',route)
 page.add_init_script("localStorage.setItem('ytpro_lang','tr');document.addEventListener('DOMContentLoaded',()=>document.body.dataset.welcomeSeen='true');")
 page.goto('http://127.0.0.1:18081/')
 page.locator('#urlInput').fill('https://example.com/live')
 page.locator('#liveRecordingOptions').wait_for(state='visible')
 assert page.locator('#companionContinue').is_hidden()
 page.locator('#liveRecordMinutes').fill('15')
 assert page.locator('#subCheck').is_disabled()
 page.locator('#audioLanguage').select_option('tr')
 page.screenshot(path=str(folder/'live-tr.png'),full_page=True)
 # Capture each locale from real rendered controls, retaining the same illustrative source.
 for lang in ['tr','en','de','es','fr','pt','ru','zh','ja','hi']:
  page.evaluate('(lang)=>setLanguage(lang)',lang)
  assert page.locator('#liveRecordingTitle').inner_text()
  assert page.locator('#audioLanguage').input_value()=='tr'
  destination=ROOT/'src/static/help'/lang/'live-recording.png';destination.parent.mkdir(parents=True,exist_ok=True)
  page.screenshot(path=str(destination),full_page=True)
 page.evaluate("setLanguage('en');document.documentElement.classList.remove('light-mode')")
 page.screenshot(path=str(folder/'live-en-dark.png'),full_page=True)
 page.set_viewport_size({'width':1280,'height':720});page.locator('#dlBtn').scroll_into_view_if_needed()
 bounds=page.locator('#dlBtn').bounding_box();assert bounds['y']>=0 and bounds['y']+bounds['height']<=720
 shell=page.locator('.glass-card').bounding_box();page.evaluate("setWorkspaceView('settings')")
 assert abs(page.locator('.glass-card').bounding_box()['height']-shell['height'])<1
 page.evaluate("setWorkspaceView('new')");page.set_viewport_size({'width':1440,'height':1080})
 page.locator('#dlBtn').click();page.wait_for_timeout(400)
 assert submissions and submissions[-1]['live_record_minutes']==15,submissions
 assert submissions[-1]['audio_language']=='tr' and submissions[-1]['subtitle_language']=='all',submissions
 page.evaluate("setWorkspaceView('settings')")
 page.locator('#settingTransfer').select_option('auto');page.locator('.settings-save').click()
 page.wait_for_timeout(200);assert client.get('/get-settings').json['transfer_mode']=='auto'
 page.screenshot(path=str(folder/'settings-en.png'),full_page=True)
 page.evaluate("openGuideTopic('live')")
 assert page.locator('#guideArticle img').get_attribute('src').endswith('/en/live-recording.png')
 # A source explicitly identified as partial must not produce a submission.
 page.evaluate("setWorkspaceView('new');downloadQueue=[];draftItems.clear();document.getElementById('queueContainer').replaceChildren()")
 page.locator('#urlInput').fill('https://example.com/partial');page.wait_for_timeout(1200)
 before=len(submissions);page.locator('#dlBtn').click();page.wait_for_timeout(300)
 assert len(submissions)==before
 assert 'Partial' in page.locator('#linkPreviewMeta').inner_text()
 page.evaluate("downloadQueue=[];draftItems.clear();document.getElementById('queueContainer').replaceChildren()")
 page.locator('#urlInput').fill('https://example.com/await-play');page.locator('#companionContinue').wait_for(state='visible')
 page.locator('#companionContinue').click();page.wait_for_timeout(200);assert focused and focused[-1]['url']=='https://example.com/await-play'
 for held in pending:held.fulfill(json={'status':'success','url':'https://example.com/await-play','title':'Browser source','video_qualities':[]})
 pending.clear();page.locator('#companionContinue').wait_for(state='hidden')

 page.evaluate("setWorkspaceView('queue');renderQueueItem('https://example.com/active-recording','Live recording','');decorateLiveQueue(document.getElementById('queue-'+btoa(encodeURIComponent('https://example.com/active-recording')).replace(/=/g,'')),{url:'https://example.com/active-recording',is_live:true,status:'downloading',recorded_seconds:42,recording_limit:900})")
 page.evaluate("localizeProgress({items:[{url:'https://example.com/active-recording',is_live:true,status:'downloading',recorded_seconds:42,recording_limit:900,recording_speed_bps:60000,downloaded_bytes:2500000,percent:5}],concurrency_limit:2,active_count:1,total_speed_bps:60000})")
 assert '00:00:42 / 00:15:00' in page.locator('#queueContainer .q-estimate').last.inner_text()
 assert 'Real time' in page.locator('#queueContainer .q-speed').last.inner_text()
 button=page.locator('.queue-finish-recording');assert button.is_visible();assert button.bounding_box()['width']>200
 page.screenshot(path=str(folder/'recording-queue-en.png'),full_page=True)
 button.click();page.wait_for_timeout(200);assert finished and finished[0]['url']=='https://example.com/active-recording'
 assert not errors,errors
 browser.close()
print(json.dumps({'status':'passed','locales':10,'live_payload':'passed','language_choices':'preserved','transfer_setting':'saved','partial_submission':'blocked','page_errors':errors}))
