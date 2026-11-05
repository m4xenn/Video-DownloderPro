import socket
import types
import unittest
from unittest.mock import patch,Mock
from services.security_policy import public_link
from services.browser_security import navigation_allowed, install_browser_security
import app


class SecurityBoundaryTests(unittest.TestCase):
    def test_malicious_destinations(self):
        for url in ('file:///C:/Windows/win.ini','javascript:alert(1)','data:text/html,hello','https://user:pass@example.com/',
                    'http://127.0.0.1/','http://127.1/','http://2130706433/','http://0x7f000001/',
                    'http://[::1]/','http://[::ffff:127.0.0.1]/','http://169.254.169.254/latest/',
                    'http://192.168.1.1/','http://router.local/','http://localhost./','https://example.com\\@127.0.0.1/',
                    'http://224.0.0.1/','http://[ff02::1]/',
                    'https://example.com:99999/','https://example.com/\x00','https://example.com/\nheader'):
            with self.subTest(url=url):self.assertFalse(public_link(url))

    def test_public_links_and_dns(self):
        for url in ('https://www.youtube.com/watch?v=test&t=4s','https://cdn.example.com/video.m3u8?token=abc',
                    'https://example.com:8443/v.mp4','https://[2606:4700:4700::1111]/'):
            self.assertTrue(public_link(url),url)
        answers=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]
        with patch('socket.getaddrinfo',return_value=answers):self.assertTrue(public_link('https://video.example.com',True))
        answers.append((socket.AF_INET,socket.SOCK_STREAM,6,'',('10.1.2.3',443)))
        with patch('socket.getaddrinfo',return_value=answers):self.assertFalse(public_link('https://video.example.com',True))
        with patch('socket.getaddrinfo',side_effect=socket.gaierror()):self.assertFalse(public_link('https://video.example.com',True))

    def test_all_local_routes_reject_foreign_browser_requests(self):
        client=app.app.test_client()
        for path in ('/save-settings','/select-folder','/download','/set-lang','/open-folder','/queue/drafts','/history/action'):
            for headers in ({'Origin':'https://evil.example'},{'Origin':'null'},{'Sec-Fetch-Site':'cross-site'},
                            {'Referer':'https://evil.example/page'},{'Sec-Fetch-Site':'same-site'}):
                with self.subTest(path=path,headers=headers):
                    self.assertEqual(client.post(path,json={},headers=headers).status_code,403)
        self.assertEqual(client.get('/get-settings',base_url='http://evil.example:1234').status_code,403)
        self.assertEqual(client.get('/get-settings',headers={'Origin':'http://localhost:9999'}).status_code,403)
        self.assertEqual(client.get('/get-settings').status_code,200)

    def test_unsafe_input_stops_before_extraction(self):
        with patch('services.site_resolver.extract_media_info') as extract:
            for url in ('http://127.1/admin','file:///C:/secret','http://192.168.1.1/'):
                data=app.app.test_client().post('/get-info',json={'url':url})
                self.assertEqual(data.status_code,400)
                self.assertEqual(data.json['message_key'],'error.unsafe_link')
            extract.assert_not_called()

    def test_security_headers_and_frame_policy(self):
        with patch.object(app,'ensure_download_state'):
            response=app.app.test_client().get('/')
        self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff')
        self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
        self.assertIn("object-src 'none'",response.headers['Content-Security-Policy'])
        self.assertFalse(navigation_allowed('ms-settings:privacy'))
        self.assertFalse(navigation_allowed('file:///C:/secret'))
        self.assertTrue(navigation_allowed('about:blank'))
        self.assertTrue(navigation_allowed('https://video.example.com'))

    def test_windows_internet_marker_preserves_file_bytes(self):
        import os,tempfile
        from pathlib import Path
        from services.file_security import mark_internet_file
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'build') as directory:
            target=Path(directory)/'video.mp4';target.write_bytes(b'fixture-media')
            marked=mark_internet_file(target)
            self.assertEqual(target.read_bytes(),b'fixture-media')
            if os.name=='nt' and marked:
                self.assertEqual(Path(str(target)+':Zone.Identifier').read_text(encoding='ascii'),'[ZoneTransfer]\nZoneId=3\n')

    def test_native_events_block_permissions_download_and_protocol(self):
        class Event:
            def __init__(self):self.handlers=[]
            def __iadd__(self,handler):self.handlers.append(handler);return self
        core=types.SimpleNamespace(Settings=types.SimpleNamespace())
        for name in ('NavigationStarting','PermissionRequested','DownloadStarting','LaunchingExternalUriScheme','WebResourceRequested'):
            setattr(core,name,Event())
        module=types.ModuleType('Microsoft.Web.WebView2.Core');module.CoreWebView2PermissionState=types.SimpleNamespace(Deny='deny')
        with patch.dict('sys.modules',{'Microsoft.Web.WebView2.Core':module}):
            handlers=install_browser_security(core,Mock())
        for name in ('DownloadStarting','LaunchingExternalUriScheme'):
            args=types.SimpleNamespace(Cancel=False,Handled=False)
            getattr(core,name).handlers[0](None,args);self.assertTrue(args.Cancel)
        args=types.SimpleNamespace(State='allow',SavesInProfile=True,Handled=False)
        core.PermissionRequested.handlers[0](None,args)
        self.assertEqual(args.State,'deny');self.assertFalse(args.SavesInProfile)
        self.assertFalse(core.Settings.AreHostObjectsAllowed)
        self.assertFalse(core.Settings.IsPasswordAutosaveEnabled)
        args=types.SimpleNamespace(Uri='http://127.0.0.1/',Cancel=False)
        core.NavigationStarting.handlers[0](None,args);self.assertTrue(args.Cancel)
        self.assertEqual(len(handlers),5)
