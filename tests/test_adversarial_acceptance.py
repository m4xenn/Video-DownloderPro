import copy,io,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import app
from state.app_state import state
from services.security_policy import public_link

class AdversarialAcceptance(unittest.TestCase):
 def test_every_static_api_route_rejects_foreign_origin_before_execution(self):
  client=app.app.test_client();checked=0
  for rule in app.app.url_map.iter_rules():
   if '<' in rule.rule:continue
   method='POST' if 'POST' in rule.methods else 'GET'
   response=client.open(rule.rule,method=method,json={},headers={'Origin':'https://attacker.example'})
   self.assertEqual(response.status_code,403,rule.rule);checked+=1
  self.assertGreater(checked,20)
 def test_native_bridge_rejects_forged_or_oversized_requests(self):
  import tempfile,urllib.request,urllib.error
  from services.extension_bridge import ExtensionBridge
  with tempfile.TemporaryDirectory(dir=ROOT/'build') as temporary,patch('services.extension_bridge.endpoint_file',return_value=Path(temporary)/'endpoint.json'):
   bridge=ExtensionBridge();bridge.start()
   try:
    url=f'http://127.0.0.1:{bridge.server.server_port}/exchange'
    for headers,status in [({},403),({'Authorization':'Bearer invalid'},403),({'Authorization':'Bearer '+bridge.secret,'Origin':'https://attacker.example'},403),({'Authorization':'Bearer '+bridge.secret,'Content-Length':'65537'},400)]:
     request=urllib.request.Request(url,data=b'{}',headers=headers,method='POST')
     with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request,timeout=4)
     self.assertEqual(error.exception.code,status)
   finally:bridge.close()
 def test_unknown_length_request_is_bounded(self):
  body=json.dumps({'padding':'x'*(2*1024*1024)}).encode()
  from werkzeug.test import EnvironBuilder
  environ=EnvironBuilder(path='/queue/recover',method='POST',data=body,content_type='application/json').get_environ()
  environ.pop('CONTENT_LENGTH',None);environ['wsgi.input_terminated']=True
  with app.app.request_context(environ):response=app.app.full_dispatch_request()
  self.assertIn(response.status_code,(400,413))
  self.assertGreater(environ['wsgi.input'].tell(),0)
  self.assertLessEqual(environ['wsgi.input'].tell(),2*1024*1024)
 def test_zero_port_is_not_silently_replaced_with_default(self):
  self.assertFalse(public_link('https://example.com:0/video'))
 def test_foreign_origins_are_blocked_on_all_privileged_routes(self):
  routes=['/save-settings','/select-folder','/open-folder','/download','/history/action','/queue/recover','/recordings/recover','/queue/drafts','/set-lang','/recording/finish']
  client=app.app.test_client()
  for route in routes:
   for origin in ['null','https://attacker.example','http://localhost:9999']:
    with self.subTest(route=route,origin=origin):self.assertEqual(client.post(route,json={},headers={'Origin':origin}).status_code,403)
 def test_host_rebinding_and_private_alias_matrix(self):
  client=app.app.test_client()
  for host in ['attacker.example','127.0.0.1.attacker.example','localhost.attacker.example']:
   self.assertEqual(client.get('/get-settings',base_url='http://'+host).status_code,403)
  for url in ['http://0177.0.0.1/','http://0x7f000001/','http://[::ffff:127.0.0.1]/','http://169.254.169.254/','file:///C:/Windows/win.ini','https://user:password@example.com/']:
   self.assertFalse(public_link(url),url)
