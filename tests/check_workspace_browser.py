"""Isolated browser acceptance check; requires Playwright and installed Edge.
Run: python tests/check_workspace_browser.py --output tmp/ui-redesign
No installed profile, external media or download engine is used.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit, parse_qs
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--capture-help',action='store_true',help='Refresh bundled screenshots using synthetic fixtures')
 parser.add_argument('--output',default=str(ROOT/'tmp/ui-redesign'))
 args=parser.parse_args()
 if args.capture_help: parser.error('Use python tests/capture_localized_help.py to regenerate the complete language matrix.')
 output=Path(args.output); output.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='workspace-browser-') as temporary:
  os.environ['VIDEO_DOWNLOADER_DATA_DIR']=temporary
  sys.path.insert(0,str(ROOT/'src'))
  import app
  from utils import file_helpers
  file_helpers.SETTINGS_FILE=str(Path(temporary)/'settings.json')
  file_helpers.LEGACY_SETTINGS_FILE=str(Path(temporary)/'legacy.json')
  app.state['current_download_path']='C:/Downloads/Video Downloader Pro'
  client=app.app.test_client()
  errors=[]
  jobs=[]
  submissions=[]
  history_empty=[False]
  def capture_help(name,locator):
   if args.capture_help: locator.screenshot(path=str(ROOT/'src/static/help/tr'/f'{name}.png'),animations='disabled')
  # Serve through Flask's client so no test server, user data or external network is needed.
  def serve(route):
   request=route.request
   url=urlsplit(request.url)
   if url.path=='/check-app-update':
    route.fulfill(json={'status':'up_to_date','update_available':False,'current_version':app.CURRENT_VERSION}); return
   if url.path=='/history':
    if history_empty[0] or parse_qs(url.query).get('q',[''])[0]=='no-match':
     route.fulfill(json={'total':0,'items':[]}); return
    route.fulfill(json={'total':1,'items':[{'id':'sample','title':'Örnek eğitim videosu','url':'https://example.com/lesson','format':'video','quality':'max','embed_subs':False,'size':10485760,'completed_at':'2026-10-22T09:00:00+03:00','path':'C:/Downloads/Örnek eğitim videosu.mp4','file_exists':True}]}); return
   if url.path=='/download':
    payload=json.loads(request.post_data); submissions.append(payload)
    jobs.extend({'url':link,'title':'Browser fixture video','thumbnail':'','format':payload['format'],'quality':payload['quality'],'percent':42,'status':'downloading','speed':'2 MB/s','total_bytes':10485760,'eta':3} for link in payload['urls'])
    route.fulfill(json={'status':'success'}); return
   if url.path in ['/pause','/resume','/queue/remove']:
    link=json.loads(request.post_data)['url']
    if url.path=='/queue/remove': jobs[:]=[job for job in jobs if job['url']!=link]
    else:
     for job in jobs:
      if job['url']==link: job['status']='paused' if url.path=='/pause' else 'downloading'
    route.fulfill(json={'status':'success'}); return
   if url.path=='/progress':
    route.fulfill(json={'status':'downloading' if any(job['status']=='downloading' for job in jobs) else 'idle','items':jobs,'total_items':len(jobs),'concurrency_mode':'auto','concurrency_limit':2,'active_count':sum(job['status']=='downloading' for job in jobs),'total_speed_bps':3200000 if any(job['status']=='downloading' for job in jobs) else 0}); return
   if url.path=='/get-info':
    route.fulfill(json={'status':'success','url':json.loads(request.post_data)['url'],'title':'Browser fixture video','thumbnail':'','video_qualities':[{'value':'source:720:30','label':'720p · 30 FPS'}]}); return
   with patch.object(app,'ensure_download_state'):
    response=client.open(url.path+('?' + url.query if url.query else ''),method=request.method,
      data=request.post_data,content_type=request.headers.get('content-type'))
   route.fulfill(status=response.status_code,body=response.data,content_type=response.content_type)
  with sync_playwright() as playwright:
   browser=playwright.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
   page=browser.new_page(viewport={'width':1120,'height':850},device_scale_factor=1)
   page.on('pageerror',lambda error:errors.append(str(error)))
   page.route('**/*',serve)
   page.goto('http://workspace.test/',wait_until='domcontentloaded')
   page.wait_for_function('typeof updateWorkspaceTexts === "function"')
   page.evaluate('setLanguage("tr"); toggleTheme(true)')
   expect(page.locator('#welcomeModal')).to_be_visible()
   expect(page.locator('#welcomeTabs [role=tab]')).to_have_count(7)
   expect(page.locator('main')).to_have_js_property('inert',True)
   page.screenshot(path=str(output/'welcome.png'),full_page=True,animations='disabled')
   page.locator('#welcomeNext').click()
   expect(page.locator('#welcomePosition')).to_contain_text('2 / 7')
   expect(page.locator('#welcome-tab-formats')).to_have_attribute('aria-selected','true')
   # Native horizontal scroll changes the selected page without using Next.
   page.locator('#welcomeTrack').evaluate('(node)=>node.scrollTo({left:node.clientWidth,behavior:"instant"})')
   page.locator('#welcomeTrack').hover()
   page.mouse.wheel(700,0)
   expect(page.locator('#welcomePosition')).not_to_contain_text('2 / 7')
   page.locator('#welcomeTabs [aria-selected=true]').focus()
   page.keyboard.press('End')
   expect(page.locator('#welcomePosition')).to_contain_text('7 / 7')
   page.locator('#welcomeNext').click()
   expect(page.locator('#welcomeModal')).not_to_be_visible()
   expect(page.locator('main')).to_have_js_property('inert',False)
   page.wait_for_function('document.body.dataset.welcomeSeen==="true"')
   page.evaluate('localStorage.clear()')  # App settings must survive an ephemeral WebView profile.
   page.reload(wait_until='domcontentloaded')
   page.wait_for_timeout(450)  # The delayed first-run check must not reopen a completed tour.
   expect(page.locator('#welcomeModal')).not_to_be_visible()
   page.evaluate('setLanguage("tr");toggleTheme(true)')
   capture_help('start',page.locator('.download-studio'))
   page.locator('[data-workspace=guide]').click()
   expect(page.locator('.guide-section')).to_be_visible()
   expect(page.locator('[data-workspace=guide]')).to_have_attribute('aria-current','page')
   for topic in ['start','formats','playlist','queue','history','settings','troubleshooting']:
    page.locator('#guide-tab-'+topic).click()
    expect(page.locator('#guideArticle .guide-steps li')).to_have_count(3)
    page.wait_for_function('document.querySelector(".guide-screenshot img").naturalWidth>0')
   page.locator('.guide-screenshot').click()
   expect(page.locator('#guideImageModal')).to_be_visible()
   page.keyboard.press('Escape')
   expect(page.locator('.guide-screenshot')).to_be_focused()
   page.locator('#replayWelcome').click()
   expect(page.locator('#welcomePosition')).to_contain_text('1 / 7')
   page.locator('#welcome-tab-queue').click()
   expect(page.locator('#welcomePosition')).to_contain_text('4 / 7')
   page.locator('#welcomeGuide').click()
   expect(page.locator('#guide-tab-queue')).to_have_attribute('aria-selected','true')
   page.locator('#replayWelcome').click()
   page.keyboard.press('Escape')
   expect(page.locator('#replayWelcome')).to_be_focused()
   page.screenshot(path=str(output/'guide.png'),full_page=True,animations='disabled')
   page.locator('[data-workspace=new]').click()
   expect(page.locator('#workspaceQueueStatus')).to_have_text('Bağlantı ekleyerek başla')
   page.screenshot(path=str(output/'dark.png'),full_page=True,animations="disabled")
   page.locator('[data-workspace=new]').click()
   expect(page.locator('#urlInput')).to_be_focused()
   page.locator('#urlInput').fill('https://example.com/browser-fixture')
   page.locator('#addBtn').click()
   expect(page.locator('#queueCount')).to_have_text('1')
   expect(page.locator('#addLabel')).to_have_text('Ekle')
   page.locator('.queue-remove').click()
   expect(page.locator('#queueCount')).to_have_text('0')
   page.locator('[data-workspace=queue]').click()
   expect(page.locator('.queue-panel')).to_be_focused()
   expect(page.locator('.download-studio')).not_to_be_visible()
   expect(page.locator('[data-workspace=queue]')).to_have_attribute('aria-current','page')
   expect(page.locator('[data-workspace=new]')).not_to_have_attribute('aria-current','page')
   expect(page.locator('.queue-tools')).to_be_visible()
   page.screenshot(path=str(output/'queue-empty.png'),full_page=True,animations="disabled")
   page.locator('#queueEmptyAction').click()
   expect(page.locator('#urlInput')).to_be_focused()
   page.locator('#urlInput').fill('https://example.com/unsaved')
   page.locator('[data-workspace=queue]').click()
   page.locator('#queueNewDownload').click()
   expect(page.locator('#urlInput')).to_have_value('https://example.com/unsaved')
   page.locator('#urlInput').fill('')
   page.locator('#formatSelectDiv .custom-select__trigger').focus()
   page.keyboard.press('ArrowDown')
   page.keyboard.press('ArrowDown')
   page.keyboard.press('Enter')
   expect(page.locator('#formatValue')).to_have_value('audio')
   page.locator('#qualitySelectDiv .custom-select__trigger').click()
   capture_help('formats',page.locator('.download-studio'))
   page.keyboard.press('Escape')
   if args.capture_help:
    page.evaluate('''() => {
     playlistPreview={token:'sample',status:'ready',entries:[
      {id:'one',title:'01 · Başlangıç ve kurulum',group:'Örnek eğitim serisi',available:true,duration:180,total_bytes:10485760},
      {id:'two',title:'02 · Temel kullanım',group:'Örnek eğitim serisi',available:true,duration:240,total_bytes:20971520},
      {id:'three',title:'03 · İleri seviye ayarlar',group:'Örnek eğitim serisi',available:true,duration:300,total_bytes:31457280}]};
     playlistChosen.clear();playlistChosen.add('one');playlistChosen.add('two');
     document.getElementById('playlistStatus').textContent='İndirmek istediğin videoları seç.';
     openFeature('playlistModal');renderPlaylistSelection();
    }''')
    capture_help('playlist',page.locator('#playlistModal .feature-card'))
    page.keyboard.press('Escape')
   page.evaluate('setLanguage("en")')
   expect(page.locator('[data-workspace=settings]')).to_have_attribute('aria-label','Settings')
   page.locator('[data-workspace=settings]').click()
   expect(page.locator('#settingsView')).to_be_visible()
   page.evaluate('setLanguage("tr")')
   capture_help('settings',page.locator('#settingsView'))
   if args.capture_help:
    page.locator('#diagnosticsPanel > summary').click()
    capture_help('troubleshooting',page.locator('#diagnosticsPanel'))
    page.locator('#diagnosticsPanel > summary').click()
   page.screenshot(path=str(output/'settings.png'),full_page=True,animations="disabled")
   page.keyboard.press('Escape')
   expect(page.locator('#settingsView')).to_be_visible()
   assert page.locator('#settingsView').get_attribute('role')!='dialog'
   expect(page.locator('[data-workspace=settings]')).to_have_attribute('aria-current','page')
   page.locator('[data-workspace=history]').click()
   expect(page.locator('#historyView')).to_be_visible()
   expect(page.locator('.workspace-content')).to_have_attribute('data-view','history')
   expect(page.locator('[data-workspace=history]')).to_have_attribute('aria-current','page')
   assert page.locator('#historyView').get_attribute('role')!='dialog'
   assert page.evaluate("getComputedStyle(document.querySelector('.workspace-content')).filter")== 'none'
   assert page.evaluate("[...document.querySelectorAll('.feature-overlay')].every(node=>getComputedStyle(node).display==='none')")
   expect(page.locator('#historyEntries .feature-row')).to_have_count(1)
   page.set_viewport_size({'width':1920,'height':1080})
   page.evaluate("setWorkspaceView('new')")
   area=page.locator('.studio-layout').bounding_box()
   composer=page.locator('.download-studio').bounding_box()
   assert area['height']-composer['height']<50, (area,composer)
   page.screenshot(path=str(output/'new-maximized.png'),animations='disabled')
   for width,height in [(1120,850),(900,750),(600,500),(390,844)]:
    page.set_viewport_size({'width':width,'height':height})
    sizes=[]
    for view in ['new','queue','history','settings','guide']:
     page.evaluate('(view)=>setWorkspaceView(view)',view)
     sizes.append(page.locator('.glass-card').bounding_box())
     assert page.evaluate('document.documentElement.scrollHeight<=innerHeight'), (width,view)
    assert all(abs(box['height']-sizes[0]['height'])<1 and abs(box['width']-sizes[0]['width'])<1 for box in sizes),sizes
   page.set_viewport_size({'width':1120,'height':850})
   page.evaluate("setWorkspaceView('settings');document.querySelector('.studio-layout').scrollTop=100")
   settings_scroll=page.evaluate("document.querySelector('.studio-layout').scrollTop")
   page.evaluate("setWorkspaceView('new');setWorkspaceView('settings')")
   assert page.evaluate("document.querySelector('.studio-layout').scrollTop")==settings_scroll
   page.evaluate("setWorkspaceView('history')")
   preview=page.locator('.history-preview-toggle')
   expect(preview).to_be_visible()
   preview.click()
   expect(preview).to_have_attribute('aria-expanded','true')
   expect(page.locator('.history-player video')).to_be_visible()
   assert page.locator('.history-player video').evaluate('(v)=>!v.autoplay')
   preview.click()
   expect(page.locator('.history-player')).to_have_count(0)
   preview.click()
   page.evaluate("setWorkspaceView('new')")
   expect(page.locator('.history-player')).to_have_count(0)
   page.evaluate("setWorkspaceView('history')")
   page.evaluate("()=>{const list=document.querySelector('#historyEntries');for(let i=0;i<30;i++)list.append(list.firstElementChild.cloneNode(true));}")
   settings=page.locator('[data-workspace=settings]').bounding_box()
   assert settings['y']>=0 and settings['y']+settings['height']<=850, settings
   page.evaluate("document.querySelector('.studio-layout').scrollTop=1500")
   settings=page.locator('[data-workspace=settings]').bounding_box()
   assert settings['y']>=0 and settings['y']+settings['height']<=850, settings
   page.evaluate('loadHistory()')
   expect(page.locator('#historyEntries .feature-row')).to_have_count(1)
   page.evaluate('window.scrollTo(0,0)')
   page.screenshot(path=str(output/'history-inline.png'),full_page=True,animations='disabled')
   page.keyboard.press('Escape')
   expect(page.locator('.workspace-content')).to_have_attribute('data-view','history')
   assert page.evaluate('''()=>{window.historyPending=loadHistory();return document.querySelectorAll('#historyEntries .feature-row').length;}''')==1
   page.evaluate('window.historyPending')
   page.locator('#historySearch').fill('no-match')
   expect(page.locator('#historyEmpty')).to_be_visible()
   expect(page.locator('#historyEntries .feature-row')).to_have_count(0)
   page.locator('#historyNewDownload').click()
   expect(page.locator('#historyEntries .feature-row')).to_have_count(1)
   expect(page.locator('#historySearch')).to_have_value('')
   history_empty[0]=True
   page.locator('[data-workspace=history]').click()
   expect(page.locator('#historyEmpty')).to_be_visible()
   page.locator('#historyNewDownload').click()
   expect(page.locator('.workspace-content')).to_have_attribute('data-view','new')
   history_empty[0]=False
   page.locator('[data-workspace=new]').click()
   page.evaluate('setLanguage("tr"); toggleTheme(false)')
   page.screenshot(path=str(output/'light.png'),full_page=True,animations="disabled")
   # Theme updates keep text nodes, contrast colors and geometry stable at every paint.
   theme_report=page.evaluate('''async()=>{
    const heading=document.querySelector('.app-brand h1'), textNode=heading.firstChild;
    const reports=[];
    for(const dark of [true,false,true,false]) {
     toggleTheme(dark);
     const expectedColor=getComputedStyle(heading).color, frames=[];
     for(let i=0;i<10;i++) {
      await new Promise(requestAnimationFrame);
      const style=getComputedStyle(heading), rect=heading.getBoundingClientRect();
      frames.push({color:style.color,opacity:style.opacity,y:rect.y,textSame:heading.firstChild===textNode});
     }
     reports.push({expectedColor,frames});
    }
    return reports;
   }''')
   for report in theme_report:
    assert all(frame['color']==report['expectedColor'] and frame['opacity']=='1' and frame['textSame'] for frame in report['frames']),report
    assert len({frame['y'] for frame in report['frames']})==1,report
   header_positions=page.evaluate('''()=>['new','queue','guide','history','new'].map(view=>{setWorkspaceView(view);return document.querySelector('.app-header').getBoundingClientRect().y;})''')
   assert max(header_positions)-min(header_positions)<1,header_positions
   # Rapid view changes cancel old entrances and settle on the last requested view.
   page.evaluate("setWorkspaceView('queue');setWorkspaceView('guide');setWorkspaceView('history');setWorkspaceView('new')")
   expect(page.locator('#urlInput')).to_be_focused()
   expect(page.locator('.workspace-content')).to_have_attribute('data-view','new')
   page.evaluate("setWorkspaceView('queue')")
   assert page.evaluate("document.querySelector('.studio-layout').getAnimations().length")>0
   page.evaluate("Promise.all(document.querySelector('.studio-layout').getAnimations().map(a=>a.finished))")
   page.locator('[data-workspace=new]').click()
   # An accepted submission moves to the queue; pause and resume use the existing actions.
   page.locator('#urlInput').fill('https://example.com/submitted')
   page.locator('#dlBtn').click()
   expect(page.locator('.workspace-content')).to_have_attribute('data-view','queue')
   expect(page.locator('#queueContainer > .queue-item')).to_have_attribute('data-status','downloading')
   assert submissions[-1]['format']=='audio'
   page.locator('.queue-pause').click()
   expect(page.locator('#queueContainer > .queue-item')).to_have_attribute('data-status','paused')
   page.locator('.queue-resume').click()
   expect(page.locator('#queueContainer > .queue-item')).to_have_attribute('data-status','downloading')
   page.locator('.queue-pause').click()
   page.locator('.queue-remove').click()
   expect(page.locator('#queueCount')).to_have_text('0')
   jobs.clear()
   page.locator('#queueNewDownload').click()
   # Exercise every queue state without a media download.
   page.evaluate('clearInterval(progressInterval)')
   for index,status in reversed(list(enumerate(['downloading','paused','finished','error','queued']))):
    jobs.append({'url':f'https://example.com/video-{index}','title':['Tasarımın ritmi · Bölüm 01','Şehirden uzaklaş · Yol notları','Ses koleksiyonu','Bağlantı yeniden kontrol edilmeli','Yeni bir başlangıç'][index],
     'thumbnail':'','format':'video','quality':'max','percent':100 if status=='finished' else 0 if status=='queued' else 42,'status':status,'speed':'3.2 MB/s','total_bytes':10485760,'eta':5,
     'error_code':'network_error' if status=='error' else ''})
   page.evaluate('pollDownloadProgress()')
   expect(page.locator('#workspaceQueueStatus')).to_have_text('1 indiriliyor · 1 duraklatıldı · 1 tamamlandı · 1 bekliyor · 1 hata')
   expect(page.locator('#queueCount')).to_have_text('5')
   expect(page.locator('#queueEmpty')).not_to_be_visible()
   page.evaluate('toggleTheme(true)')
   page.screenshot(path=str(output/'queue.png'),full_page=True,animations="disabled")
   page.locator('#queueExpand').click()
   expect(page.locator('.download-studio')).not_to_be_visible()
   capture_help('queue',page.locator('.queue-panel'))
   page.screenshot(path=str(output/'queue-focused.png'),full_page=True,animations="disabled")
   page.locator('#queueFilter').select_option('error')
   expect(page.locator('#queueContainer > .queue-item:visible')).to_have_count(1)
   expect(page.locator('#queueContainer > .queue-item:visible')).to_have_attribute('data-status','error')
   # Filtered results track live status changes, without losing the search.
   page.evaluate("document.querySelector('[data-status=error]').dataset.status='paused'")
   expect(page.locator('#queueNoResults')).to_be_visible()
   page.locator('#queueResetFilters').click()
   expect(page.locator('#queueContainer > .queue-item:visible')).to_have_count(5)
   page.locator('#queueSearch').fill('https://example.com/video-2')
   expect(page.locator('#queueContainer > .queue-item:visible')).to_have_count(1)
   page.locator('#queueSearch').fill('no matching download')
   expect(page.locator('#queueNoResults')).to_be_visible()
   page.locator('[data-workspace=new]').click()
   expect(page.locator('#queueContainer > .queue-item:visible')).to_have_count(5)
   page.locator('[data-workspace=queue]').click()
   expect(page.locator('#queueNoResults')).to_be_visible()
   page.locator('#queueResetFilters').click()
   for width,height in [(900,750),(600,500),(390,844)]:
    page.set_viewport_size({'width':width,'height':height})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Horizontal overflow at {width}'
    page.screenshot(path=str(output/f'queue-focused-{width}.png'),full_page=True,animations="disabled")
    page.locator('#queueNewDownload').click()
    if width==900:
     assert page.locator('#dlBtn').bounding_box()['y']+page.locator('#dlBtn').bounding_box()['height'] <= height, 'Primary action below native viewport'
    page.screenshot(path=str(output/f'workspace-{width}.png'),full_page=True,animations="disabled")
    page.locator('[data-workspace=queue]').click()
   for language in ['tr','en','de','es','fr','pt','ru','zh','ja','hi']:
    page.evaluate('(lang)=>setLanguage(lang)',language)
    assert page.locator('[data-workspace=new]').get_attribute('aria-label')
    assert page.locator('#workspaceQueueStatus').inner_text()
    for topic in ['start','formats','playlist','queue','history','settings','troubleshooting']:
     page.locator('[data-workspace=guide]').click()
     page.locator('#guide-tab-'+topic).click()
     expect(page.locator('.guide-screenshot img')).to_have_attribute('src','/static/help/'+language+'/'+topic+'.png')
     page.wait_for_function('document.querySelector(".guide-screenshot img").naturalWidth>0')
    page.locator('[data-workspace=queue]').click()
   page.evaluate('setLanguage("tr")')
   page.locator('[data-workspace=guide]').click()
   for width,height in [(900,750),(600,500),(390,844)]:
    page.set_viewport_size({'width':width,'height':height})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Guide overflow at {width}'
    page.screenshot(path=str(output/f'guide-{width}.png'),full_page=True,animations='disabled')
    page.locator('[data-workspace=history]').click()
    expect(page.locator('#historyView')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'History overflow at {width}'
    page.screenshot(path=str(output/f'history-{width}.png'),full_page=True,animations='disabled')
    page.locator('[data-workspace=guide]').click()
   page.locator('#replayWelcome').click()
   for width,height in [(900,750),(600,500),(390,844)]:
    page.set_viewport_size({'width':width,'height':height})
    box=page.locator('.welcome-card').bounding_box()
    assert box['y']>=0 and box['y']+box['height']<=height, f'Welcome controls outside viewport at {width}x{height}'
    page.screenshot(path=str(output/f'welcome-{width}.png'),full_page=False,animations='disabled')
   page.screenshot(path=str(output/'welcome-small.png'),full_page=False,animations='disabled')
   # Reduced motion and explicit Skip are supported too.
   page.emulate_media(reduced_motion='reduce')
   page.locator('#welcomeNext').click()
   expect(page.locator('#welcomePosition')).to_contain_text('2 / 7')
   page.locator('#welcomeSkip').click()
   expect(page.locator('#welcomeModal')).not_to_be_visible()
   page.evaluate("setWorkspaceView('history')")
   assert page.evaluate("document.querySelector('.studio-layout').getAnimations().length")==0
   assert not errors,errors
   browser.close()
  app.download_manager.close()
  (output/'result.json').write_text(json.dumps({'result':'passed','languages':10,'viewports':4,'page_errors':errors},indent=2),encoding='utf-8')
  print('Workspace browser checks passed: first-run persistence, swipe/keyboard tour, replay/skip/Escape, illustrated guide/zoom, distinct queue view, draft preservation, submission/pause/resume, live filters/search, dialog focus, frame-stable themes, inline history, rapid navigation, 10 languages, responsive layouts; no page errors.')
if __name__=='__main__': main()
