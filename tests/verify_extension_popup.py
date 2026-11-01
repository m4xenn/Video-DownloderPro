"""Rendered popup locale sync, live updates and stable source identity."""
import pathlib,json
from playwright.sync_api import sync_playwright
root=pathlib.Path.cwd();folder=root/'build/extension-language-preview';folder.mkdir(exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,chromium_sandbox=True)
 page=browser.new_page(viewport={'width':420,'height':760},device_scale_factor=1);errors=[]
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.add_init_script("""window.fixtureLanguage='fr';window.fixtureConnected=true;window.fixtureJobs=true;
 window.chrome={i18n:{getUILanguage:()=> 'de-DE'},runtime:{sendMessage:async m=>{
 window.lastCompanionMessage=m;if(m.type==='select')window.selectedSourceIndex=m.index;
 const language=window.fixtureLanguage,t=(key,values)=>VDPI18n.text(key,language,values);
 return m.type==='popup-status'?{language,connected:window.fixtureConnected,jobs:window.fixtureJobs?[{id:'test',state:t('choose'),candidates:[
 {index:2,host:'cdn.example',label:t('master'),detail:t('masterDetail',{count:4}),recommended:true},
 {index:1,host:'cdn.example',label:'804p · '+t('video'),detail:'804p · 3.2 Mbps'},
 {index:0,host:'cdn.example',label:'536p · '+t('video'),detail:'536p · 1.8 Mbps'}]}]:[]}:true;}}};""")
 def route(r):
  name=r.request.url.rsplit('/',1)[-1]
  if name in ('popup.html','popup.js','locales.js'):
   r.fulfill(status=200,content_type='text/html' if name.endswith('html') else 'application/javascript',body=(root/'browser-extension'/name).read_text(encoding='utf-8'))
  elif name in ('icon-16.png','icon-32.png','icon-48.png','icon-128.png'):r.fulfill(status=200,content_type='image/png',body=(root/'browser-extension/icons'/name).read_bytes())
  else:r.abort()
 page.route('**/*',route);page.goto('https://preview.example/popup.html')
 page.get_by_role('button',name='Flux principal',exact=False).wait_for()
 assert page.locator('.source').count()==3
 assert page.locator('#intro').inner_text().startswith('Collez')
 page.wait_for_function("document.querySelector('h3 img').naturalWidth===48")
 page.screenshot(path=str(folder/'popup-fr.png'),full_page=True)
 for language in ['tr','en','de','es','fr','pt','ru','zh','ja','hi']:
  page.evaluate("async lang=>{window.fixtureLanguage=lang;await render();}",language)
  assert page.locator('html').get_attribute('lang')==language
  assert page.locator('#intro').inner_text()
  assert page.locator('.source').first.locator('strong').inner_text()==page.evaluate("VDPI18n.text('master',window.fixtureLanguage)")
 page.locator('.source').first.focus()
 page.evaluate("window.focusedSource=document.activeElement;window.fixtureLanguage='fr'")
 page.wait_for_function("document.documentElement.lang==='fr'")
 assert page.evaluate('document.activeElement===window.focusedSource')
 assert 'Flux principal' in page.locator('.source').first.inner_text()
 page.locator('.source').first.click()
 assert page.evaluate('window.selectedSourceIndex')==2
 # Empty/disconnected strings also follow the last matched application locale.
 page.evaluate("document.activeElement.blur();window.fixtureJobs=false;window.fixtureConnected=false")
 page.mouse.move(410,740);page.evaluate('render()')
 assert 'En attente' in page.locator('#jobs').inner_text()
 page.screenshot(path=str(folder/'popup-fr-disconnected.png'),full_page=True)
 assert not errors,errors
 (folder/'result.json').write_text(json.dumps({'passed':True,'locales':10,'errors':errors,'live_focus_preserved':True,'source_index':2},indent=2))
 browser.close()
print('Popup passed: ten languages, live French update, focus/source identity, disconnected text and logo')
