"""Render the live UI into 10 × 7 bundled help screenshots. No real downloads.
Run from repository root: python tests/capture_localized_help.py
"""
import json
import os
from pathlib import Path
import sys
import struct
import tempfile
from unittest.mock import patch
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
LANGUAGES=['tr','en','de','es','fr','pt','ru','zh','ja','hi']
TOPICS=['start','formats','playlist','queue','history','settings','troubleshooting']
DEMO={
 'tr':['Örnek eğitim videosu','Örnek eğitim serisi','Başlangıç ve kurulum','Temel kullanım','İleri seviye ayarlar','Şehirden uzaklaş','Yeni bir başlangıç'],
 'en':['Sample tutorial video','Sample tutorial series','Getting started and setup','Basic usage','Advanced settings','Away from the city','A new beginning'],
 'de':['Beispiel-Lernvideo','Beispiel-Lernreihe','Erste Schritte und Einrichtung','Grundlagen','Erweiterte Einstellungen','Raus aus der Stadt','Ein neuer Anfang'],
 'es':['Vídeo de ejemplo','Serie de tutoriales','Primeros pasos e instalación','Uso básico','Ajustes avanzados','Lejos de la ciudad','Un nuevo comienzo'],
 'fr':['Tutoriel d’exemple','Série de tutoriels','Premiers pas et installation','Utilisation de base','Réglages avancés','Loin de la ville','Un nouveau départ'],
 'pt':['Vídeo de exemplo','Série de tutoriais','Primeiros passos e instalação','Uso básico','Configurações avançadas','Longe da cidade','Um novo começo'],
 'ru':['Пример обучающего видео','Учебная серия','Начало работы и установка','Основы использования','Расширенные настройки','Вдали от города','Новое начало'],
 'zh':['示例教学视频','示例教程系列','入门与安装','基本用法','高级设置','远离城市','全新开始'],
 'ja':['サンプル解説動画','サンプル講座','はじめに・インストール','基本的な使い方','詳細設定','街を離れて','新しい始まり'],
 'hi':['उदाहरण शिक्षण वीडियो','उदाहरण शिक्षण शृंखला','शुरुआत और स्थापना','बुनियादी उपयोग','उन्नत सेटिंग्स','शहर से दूर','एक नई शुरुआत']}

def main():
 target=ROOT/'src/static/help'
 manifest={'languages':LANGUAGES,'topics':TOPICS,'screenshots':[]}
 for lang in LANGUAGES:(target/lang).mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='help-capture-') as temporary:
  os.environ['VIDEO_DOWNLOADER_DATA_DIR']=temporary
  sys.path.insert(0,str(ROOT/'src'))
  import app
  from utils import file_helpers
  file_helpers.SETTINGS_FILE=str(Path(temporary)/'settings.json')
  file_helpers.LEGACY_SETTINGS_FILE=str(Path(temporary)/'legacy.json')
  file_helpers.save_settings_to_file({'welcome_seen':True})
  app.state['current_download_path']='C:/Downloads/Video Downloader Pro'
  client=app.app.test_client(); current=['tr']; jobs=[]; errors=[]
  def serve(route):
   req=route.request; parsed=urlsplit(req.url); lang=current[0]; demo=DEMO[lang]
   if parsed.path=='/check-app-update':route.fulfill(json={'status':'success','update_available':False,'current_version':app.CURRENT_VERSION});return
   if parsed.path=='/progress':route.fulfill(json={'status':'downloading' if jobs else 'idle','items':jobs,'total_items':len(jobs),'concurrency_mode':'auto','concurrency_limit':2,'active_count':1 if jobs else 0,'total_speed_bps':3200000 if jobs else 0});return
   if parsed.path=='/history':route.fulfill(json={'total':1,'items':[{'id':'demo','title':demo[0],'url':'https://example.com/tutorial','format':'video','quality':'max','size':10485760,'completed_at':'2026-10-22T09:00:00+03:00','path':'C:/Downloads/Video.mp4','file_exists':True}]});return
   if parsed.path=='/get-info':route.fulfill(json={'status':'success','url':json.loads(req.post_data)['url'],'title':demo[0],'thumbnail':'','video_qualities':[]});return
   with patch.object(app,'ensure_download_state'):
    response=client.open(parsed.path+('?' + parsed.query if parsed.query else ''),method=req.method,data=req.post_data,content_type=req.headers.get('content-type'))
   route.fulfill(status=response.status_code,body=response.data,content_type=response.content_type)
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
   page=browser.new_page(viewport={'width':1120,'height':1100},device_scale_factor=1,reduced_motion='reduce')
   page.on('pageerror',lambda error:errors.append(str(error)))
   page.route('**/*',serve)
   page.goto('http://workspace.test/',wait_until='domcontentloaded')
   page.wait_for_function('typeof interfaceText==="function"')
   page.wait_for_timeout(150)
   for lang in LANGUAGES:
    current[0]=lang;jobs.clear();demo=DEMO[lang]
    page.evaluate('''lang=>{clearInterval(progressInterval);setLanguage(lang);toggleTheme(true);setWorkspaceView('new');document.getElementById('urlInput').value='';}''',lang)
    page.evaluate('pollDownloadProgress()')
    page.locator('#formatSelectDiv .custom-select__trigger').click()
    page.locator('#formatSelectDiv [data-value=video]').click()
    expect(page.locator('#formatText')).to_have_text(page.evaluate('translations[currentLang].video'))
    page.wait_for_function('document.fonts.status==="loaded"')
    def shot(topic,selector):
     # These are the real controls in the selected language; no pixel/text overlays.
     node=page.locator(selector)
     if lang!='tr':
      for phrase in ['Ayarlar','İndirme','Kayıtları','Sonuçları','Sırada','Bağlantı hatası','Altyazı','Ses, seçtiğin','Otomatik','gösteriliyor','kullanılabilir']:
       assert phrase not in node.inner_text(),f'Turkish copy in {lang}/{topic}: {phrase}'
     node.screenshot(path=str(target/lang/(topic+'.png')),animations='disabled')
     width,height=struct.unpack('>II',(target/lang/(topic+'.png')).read_bytes()[16:24])
     manifest['screenshots'].append({'language':lang,'topic':topic,'path':f'{lang}/{topic}.png','width':width,'height':height})
    expect(page.locator('label[for=settingMode]')).to_have_text(page.evaluate('interfaceText("management")'))
    shot('start','.download-studio')
    page.locator('#formatSelectDiv .custom-select__trigger').click()
    page.locator('#formatSelectDiv [data-value=audio]').click()
    page.locator('#qualitySelectDiv .custom-select__trigger').click()
    shot('formats','.download-studio')
    page.keyboard.press('Escape')
    entries=[{'id':str(i),'title':f'0{i+1} · '+demo[i+2],'group':demo[1],'available':True,'duration':(i+1)*120,'total_bytes':(i+1)*10485760} for i in range(3)]
    page.evaluate('''entries=>{playlistPreview={token:'demo',status:'ready',entries};playlistChosen.clear();playlistChosen.add('0');playlistChosen.add('1');openFeature('playlistModal');renderPlaylistSelection();}''',entries)
    shot('playlist','#playlistModal .feature-card')
    page.keyboard.press('Escape')
    page.evaluate('openHistory()')
    expect(page.locator('#historyEntries .feature-row')).to_have_count(1)
    shot('history','#historyView')
    page.locator('[data-workspace=new]').click()
    page.evaluate('openSettings()')
    expect(page.locator('#settingsView')).to_be_visible()
    shot('settings','#settingsView')
    page.locator('#diagnosticsPanel summary').click()
    shot('troubleshooting','#diagnosticsPanel')
    page.locator('#diagnosticsPanel summary').click()
    page.keyboard.press('Escape')
    for index,status in reversed(list(enumerate(['downloading','paused','finished','error','queued']))):
     jobs.append({'url':f'https://example.com/{lang}/video-{index}','title':[demo[0],demo[5],demo[4],demo[2],demo[6]][index],
      'thumbnail':'','format':'video','quality':'max','percent':100 if status=='finished' else 0 if status=='queued' else 42,'status':status,'speed':'3.2 MB/s','total_bytes':10485760,'eta':5,'error_code':'network_error' if status=='error' else ''})
    page.evaluate('''async()=>{setWorkspaceView('queue',true);await pollDownloadProgress();}''')
    expect(page.locator('#queueCount')).to_have_text('5')
    shot('queue','.queue-panel')
    print(lang+': 7 localized screens captured',flush=True)
   assert not errors,errors
   browser.close()
  app.download_manager.close()
 (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('70 screenshots captured from the localized live UI.',flush=True)

if __name__=='__main__':main()
