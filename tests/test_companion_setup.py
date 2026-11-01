import sys,json,tempfile,unittest,types
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services import companion_setup as setup
from services.extension_bridge import ExtensionBridge
ORIGINAL_HOST_SOURCE=setup.host_source

class FakeRegistry(types.ModuleType):
 HKEY_CURRENT_USER=1;REG_SZ=1
 def __init__(self):super().__init__('winreg');self.values={}
 class Key:
  def __init__(self,path):self.path=path
  def __enter__(self):return self
  def __exit__(self,*args):pass
 def OpenKey(self,root,path):
  if path not in self.values:raise FileNotFoundError()
  return self.Key(path)
 def CreateKey(self,root,path):self.values.setdefault(path,'');return self.Key(path)
 def SetValueEx(self,key,name,reserved,kind,value):self.values[key.path]=value
 def QueryValueEx(self,key,name):return self.values[key.path],1

class SetupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='build');self.root=Path(self.tmp.name);self.target=self.root/'user-profile-\u00fc';self.exe=self.root/'helper.exe';self.exe.write_bytes(b'MZ test helper')
  self.registry=FakeRegistry();self.patches=[patch.object(setup,'install_root',return_value=self.target),patch.object(setup,'host_source',return_value=self.exe),patch.object(setup,'browser_exe',return_value=self.exe),patch.dict(sys.modules,winreg=self.registry)]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def test_explicit_consent_required_without_writes(self):
  for consent in (False,None,1,'true'):
   with self.assertRaisesRegex(ValueError,'consent_required'):setup.prepare('brave',consent)
  self.assertFalse(self.target.exists());self.assertFalse(self.registry.values)
 def test_invalid_browser(self):
  with self.assertRaisesRegex(ValueError,'invalid_browser'):setup.prepare('file:///bad',True)
 def test_missing_package(self):
  with patch.object(setup,'host_source',return_value=self.root/'absent'),self.assertRaisesRegex(ValueError,'package_incomplete'):setup.prepare('brave',True)
  self.assertFalse(self.target.exists())
 def test_prepare_complete_and_registered(self):
  result=setup.prepare('brave',True)
  self.assertTrue(result['prepared']);self.assertTrue(next(b for b in result['browsers'] if b['id']=='brave')['registered'])
  self.assertEqual((self.target/'BrowserBridge/VDPBrowserBridge.exe').read_bytes(),self.exe.read_bytes())
  manifest=json.loads(setup.manifest_path().read_text(encoding='utf-8'))
  self.assertEqual(manifest['allowed_origins'],['chrome-extension://'+setup.extension_id()+'/'])
  self.assertTrue((self.target/'BrowserExtension/icons/icon-128.png').is_file())
  self.assertNotIn(chr(92)*2,setup.registry_path('brave'))
 def test_preserves_other_approved_ids(self):
  setup.prepare('edge',True);p=setup.manifest_path();d=json.loads(p.read_text());old='chrome-extension://'+'a'*32+'/'
  d['allowed_origins']+=[old,'https://untrusted.example/'];p.write_text(json.dumps(d))
  setup.prepare('brave',True);origins=json.loads(p.read_text())['allowed_origins']
  self.assertIn(old,origins);self.assertNotIn('https://untrusted.example/',origins)
  self.assertEqual(len(self.registry.values),2)
 def test_stable_identity_after_copy(self):
  original=setup.extension_id();setup.prepare('brave',True)
  with patch.object(setup,'extension_source',return_value=self.target/'BrowserExtension'):self.assertEqual(original,setup.extension_id())
 def test_open_only_known_browser_page(self):
  with patch.object(setup.subprocess,'Popen') as launch:
   setup.open_browser('brave');self.assertEqual(launch.call_args.args[0],[str(self.exe),'--new-window','brave://extensions/'])
  with self.assertRaises(ValueError):setup.open_browser('https://evil.example')
 def test_current_client_required(self):
  b=ExtensionBridge();b.server=Mock();identity='a'*32
  b.exchange({'type':'poll','extension_id':identity,'version':'0.2.0'})
  self.assertTrue(b.client_connected(identity,'0.2.0'));self.assertFalse(b.client_connected(identity,'0.1.0'));self.assertFalse(b.client_connected('b'*32,'0.2.0'))
 def test_frozen_resources_resolve_without_source_checkout(self):
  with patch.object(setup.sys,'frozen',True,create=True),patch.object(setup.sys,'_MEIPASS',str(self.root),create=True):
   self.assertEqual(setup.extension_source(),self.root/'browser-extension');self.assertEqual(ORIGINAL_HOST_SOURCE(),self.root/'browser-bridge/VDPBrowserBridge.exe')

class RouteTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import app
  cls.client=app.app.test_client()
 def test_cross_origin_rejected(self):
  response=self.client.post('/browser-companion/action',json={'action':'prepare','browser':'brave','consent':True},headers={'Origin':'https://evil.example'})
  self.assertEqual(response.status_code,403)
 def test_setup_called_only_with_explicit_action(self):
  with patch.object(setup,'prepare',return_value={'connected':False}) as prepare:
   response=self.client.post('/browser-companion/action',json={'action':'prepare','browser':'brave','consent':True})
   self.assertEqual(response.status_code,200);prepare.assert_called_once_with('brave',True)
 def test_non_json_rejected(self):self.assertEqual(self.client.post('/browser-companion/action',data='x').status_code,403)
 def test_invalid_action(self):self.assertEqual(self.client.post('/browser-companion/action',json={'action':'execute','browser':'brave'}).status_code,400)
if __name__=='__main__':unittest.main()
