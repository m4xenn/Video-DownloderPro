import sys, pathlib,unittest,tempfile,os,json,time,threading,struct,subprocess
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'src'))
from services.extension_bridge import ExtensionBridge

class BridgeTests(unittest.TestCase):
 def test_simultaneous_inspections_share_one_browser_job(self):
  results=[];failures=[]
  def resolve():
   try:results.append(self.b.resolve('https://example.com/watch',timeout=2))
   except Exception as error:failures.append(type(error).__name__)
  with patch.object(self.b,'available',return_value=True),patch('services.extension_bridge.public_url',return_value=True):
   workers=[threading.Thread(target=resolve) for _ in range(2)]
   for worker in workers:worker.start()
   deadline=time.monotonic()+1
   while time.monotonic()<deadline:
    with self.b.lock:
     if len(self.b.jobs)==1 and next(iter(self.b.jobs.values())).get('waiters')==2:break
    time.sleep(.01)
   with self.b.lock:
    self.assertEqual(len(self.b.jobs),1);identity=next(iter(self.b.jobs));self.assertEqual(self.b.jobs[identity]['waiters'],2)
   self.b.exchange({'type':'result','id':identity,'page':'https://example.com/watch','source':'https://cdn.example/video.mp4'})
   for worker in workers:worker.join(3)
  self.assertFalse(failures);self.assertEqual(len(results),2);self.assertEqual(results[0],results[1]);self.assertFalse(self.b.jobs)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='build');self.env=patch.dict(os.environ,VIDEO_DOWNLOADER_DATA_DIR=self.tmp.name);self.env.start();self.b=ExtensionBridge();self.b.start()
 def tearDown(self):self.b.close();self.env.stop();self.tmp.cleanup()
 def request(self,msg,token=None,origin=None):
  headers={'Authorization':'Bearer '+(token or self.b.secret),'Content-Type':'application/json'}
  if origin:headers['Origin']=origin
  with urlopen(Request(f'http://127.0.0.1:{self.b.server.server_port}/exchange',data=json.dumps(msg).encode(),headers=headers),timeout=2) as r:return json.load(r)
 def test_focus_only_targets_pending_app_owned_jobs(self):
  self.b.jobs['job']={'url':'https://example.com/watch','created':time.monotonic(),'event':threading.Event()}
  with self.assertRaises(ValueError):self.b.request_focus('https://example.com/other')
  self.b.request_focus('https://example.com/watch');self.assertEqual(self.b.exchange({'type':'poll'})['jobs'][0]['focus_seq'],1)
  self.b.request_focus('https://example.com/watch');self.assertEqual(self.b.exchange({'type':'poll'})['jobs'][0]['focus_seq'],2)
 def test_unauthorized(self):
  with self.assertRaises(HTTPError) as e:self.request({},token='wrong')
  self.assertEqual(e.exception.code,403)
 def test_web_origin(self):
  with self.assertRaises(HTTPError):self.request({},origin='https://example.com')
 def test_disconnected_noop(self):self.assertIsNone(self.b.resolve('https://example.com'))
 def job(self):
  self.request({});result=[]
  with patch('services.extension_bridge.public_url',return_value=True):
   t=threading.Thread(target=lambda:result.append(self.b.resolve('https://example.com/watch',timeout=2)));t.start()
   for _ in range(100):
    jobs=self.request({})['jobs']
    if jobs:break
    time.sleep(.01)
  return t,result,jobs[0]
 def test_resolve(self):
  t,result,j=self.job()
  with patch('services.extension_bridge.public_url',return_value=True):self.request({'type':'result','id':j['id'],'page':j['url'],'source':'https://example.com/video.m3u8','kind':'hls'})
  t.join(3);self.assertEqual(result[0]['discovery_method'],'extension');self.assertNotIn('Cookie',result[0]['source_headers'][result[0]['stream']]);self.assertFalse(self.b.jobs)
 def test_bad_page_and_private(self):
  self.b.jobs['id']={'url':'https://example.com','created':time.monotonic(),'event':threading.Event()}
  for page,source in [('https://evil.example','https://example.com/a'),('https://example.com','http://127.0.0.1/a')]:
   with self.assertRaises(HTTPError):self.request({'type':'result','id':'id','page':page,'source':source})
 def test_drm(self):
  self.b.jobs['id']={'url':'https://example.com','created':time.monotonic(),'event':threading.Event()}
  with patch('services.extension_bridge.public_url',return_value=True),self.assertRaises(HTTPError):self.request({'type':'result','id':'id','page':'https://example.com','source':'https://example.com/a','drm':True})
 def test_expired(self):
  self.b.jobs['old']={'url':'https://example.com','created':time.monotonic()-181};self.assertEqual(self.request({})['jobs'],[])
 def test_generic_handoff_cached(self):
  from services.generic_resolver import GenericResolver
  browser=unittest.mock.Mock()
  resolver=GenericResolver(browser=browser)
  data={'stream':'https://cdn.example/a.mp4','streams':['https://cdn.example/a.mp4'],'title':'Test','thumbnail':'','headers':{}}
  with patch('services.extension_bridge.extension_bridge.resolve',return_value=data) as resolve,patch('services.generic_resolver.public_url',return_value=True):
   self.assertEqual(resolver.details('https://example.com/watch'),data)
   self.assertEqual(resolver.details('https://example.com/watch'),data)
   self.assertEqual(resolve.call_count,1);browser.discover.assert_not_called()
 def test_supported_interaction_uses_extension(self):
  from services.site_resolver import extract_media_info
  from services.site_browser import BrowserRequired
  with patch('services.site_resolver.site_resolver.extract',side_effect=BrowserRequired('token')),patch('services.extension_bridge.extension_bridge.available',return_value=True),patch('services.generic_resolver.generic_resolver.extract',return_value={'id':'extension'}) as external:
   self.assertEqual(extract_media_info(None,'https://www.fullhdfilmizlesene.now/film/example/'),{'id':'extension'})
   external.assert_called_once()
 def test_supported_interaction_without_extension_preserved(self):
  from services.site_resolver import extract_media_info
  from services.site_browser import BrowserRequired
  with patch('services.site_resolver.site_resolver.extract',side_effect=BrowserRequired('token')),patch('services.extension_bridge.extension_bridge.available',return_value=False),self.assertRaises(BrowserRequired):
   extract_media_info(None,'https://www.fullhdfilmizlesene.now/film/example/')
 def test_language_changes_are_sent_on_every_exchange_without_jobs(self):
  from state.app_state import state
  with patch.dict(state,current_lang='fr'):
   self.assertEqual(self.request({'type':'poll'})['language'],'fr')
   state['current_lang']='ja'
   self.assertEqual(self.request({'type':'poll'})['language'],'ja')
   state['current_lang']='unsupported'
   self.assertEqual(self.request({'type':'poll'})['language'],'en')
 def test_language_is_not_controlled_by_extension_message(self):
  from state.app_state import state
  with patch.dict(state,current_lang='de'):
   self.assertEqual(self.request({'type':'poll','language':'fr'})['language'],'de')
 def test_set_language_route_syncs_live_bridge(self):
  import app
  from state.app_state import state
  with patch.dict(state,current_lang='tr'),patch.object(app,'save_settings_to_file') as save:
   data=app.app.test_client().post('/set-lang',json={'lang':'fr','persist':False}).get_json()
   self.assertEqual(data['status'],'success')
   self.assertEqual(self.request({'type':'poll'})['language'],'fr')
   save.assert_not_called()
 def test_native_host(self):
  folder=pathlib.Path(self.tmp.name)/'YoutubePro';folder.mkdir();(folder/'extension-endpoint.json').write_text(json.dumps({'port':self.b.server.server_port,'token':self.b.secret}))
  data=b'{"type":"poll"}';host=pathlib.Path(__file__).resolve().parents[1]/'scripts/extension_native_host.py'
  p=subprocess.run([sys.executable,str(host)],input=struct.pack('<I',len(data))+data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,APPDATA=self.tmp.name),timeout=5)
  n=struct.unpack('<I',p.stdout[:4])[0];self.assertEqual(json.loads(p.stdout[4:4+n])['jobs'],[]);self.assertIn(json.loads(p.stdout[4:4+n])['language'],('tr','en','de','es','fr','pt','ru','zh','ja','hi'))
if __name__=='__main__':unittest.main()
