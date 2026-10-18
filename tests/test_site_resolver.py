import base64
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from webview.event import Event
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.site_resolver import SiteResolver, supported_page, valid_embed, valid_stream, rapidvid_source, page_details, extract_media_info
from services.site_browser import SiteBrowser, BrowserRequired
import app

PAGE='https://www.fullhdfilmizlesene.now/film/example/'
EMBED='https://rapidvid.net/vod/example123'
STREAM='https://s2.cdnimages1234.shop/master'
HTML='<h1>Example title</h1><meta property="og:image" content="/cover.jpg"><iframe data-src="'+EMBED+'"></iframe>'

def player(stream=STREAM):
    text=base64.b64encode(stream.encode()).decode()
    shifted=''.join(chr(ord(c)+(ord('K9L'[i%3])%5+1)) for i,c in enumerate(text))
    encoded=base64.b64encode(shifted.encode('latin1')).decode()[::-1]
    return 'jwSetup.sources = [{"file": av(\''+encoded+'\'), "type":"hls"}];'

class ResolverTests(unittest.TestCase):
    def test_page_allowlist(self):
        self.assertTrue(supported_page(PAGE))
        for url in [PAGE.replace('https:','http:'),PAGE.replace('.now','.now.evil.com'),PAGE.replace('/film/','/other/'),'https://user@fullhdfilmizlesene.now/film/x','https://fullhdfilmizlesene.now:123/film/x']:
            self.assertFalse(supported_page(url))
    def test_embed_allowlist(self):
        self.assertTrue(valid_embed(EMBED))
        for url in ['http://rapidvid.net/vod/x','https://127.0.0.1/vod/x','https://rapidvid.net.evil.com/vod/x','https://rapidvid.net/admin']:
            self.assertFalse(valid_embed(url))
    def test_stream_allowlist(self):
        self.assertTrue(valid_stream(STREAM))
        for url in ['https://localhost/a','file:///a','https://cdnimages1234.shop.evil.com/a','https://user@s2.cdnimages1234.shop/a']:
            self.assertFalse(valid_stream(url))
    def test_decoder(self):
        self.assertEqual(rapidvid_source(player()),STREAM)
        with self.assertRaises(ValueError):rapidvid_source(player('http://localhost/a'))
    def test_never_eval_unknown_script(self):
        for html in ['eval("danger")','jwSetup.sources = [{"file": other("x")}];',"jwSetup.sources = [{\"file\": av('bad')}];"]:
            with self.assertRaises(ValueError):rapidvid_source(html)
    def test_page_metadata(self):
        data=page_details(HTML,PAGE)
        self.assertEqual(data['title'],'Example title');self.assertEqual(data['embeds'],[EMBED])
        self.assertEqual(data['thumbnail'],'https://www.fullhdfilmizlesene.now/cover.jpg')
    def test_fast_path_and_fresh_source(self):
        browser=Mock();resolver=SiteResolver(browser=browser)
        with patch.object(resolver,'_html',side_effect=[HTML,player(),player()]) as fetch:
            first=resolver.details(PAGE);self.assertEqual(resolver.details(PAGE),first)
            resolver.details(PAGE,fresh=True)
        self.assertEqual(fetch.call_count,3);self.assertEqual(fetch.call_args.args,(EMBED,PAGE));browser.inspect.assert_not_called()
    def test_hidden_browser_fallback(self):
        browser=Mock();browser.inspect.return_value=page_details(HTML,PAGE)
        resolver=SiteResolver(browser=browser)
        with patch.object(resolver,'_html',side_effect=[requests.HTTPError(),player()]):
            self.assertEqual(resolver.details(PAGE)['stream'],STREAM)
        browser.inspect.assert_called_once_with(PAGE)
    def test_interaction_not_suppressed(self):
        browser=Mock();browser.inspect.side_effect=BrowserRequired('a'*32)
        resolver=SiteResolver(browser=browser)
        with patch.object(resolver,'_html',return_value='<html>challenge</html>'),self.assertRaises(BrowserRequired):resolver.details(PAGE)
    def test_extract_keeps_original_identity(self):
        resolver=SiteResolver();ydl=Mock();ydl.params={'http_headers':None};ydl.extract_info.return_value={'formats':[],'id':'opaque','title':'opaque'}
        with patch.object(resolver,'details',return_value={'stream':STREAM,'headers':{'Referer':'https://rapidvid.net/'},'title':'Film','thumbnail':''}):
            info=resolver.extract(ydl,PAGE,True)
        self.assertEqual(info['webpage_url'],PAGE);self.assertEqual(info['title'],'Film');self.assertEqual(info['extractor_key'],'FullHDFilmizlesene')
    def test_other_sites_unchanged(self):
        ydl=Mock();extract_media_info(ydl,'https://example.com/video');ydl.extract_info.assert_called_once_with('https://example.com/video',download=False)
    def test_route_handoff(self):
        with patch.object(app,'extract_media_info',side_effect=BrowserRequired('a'*32)):
            data=app.app.test_client().post('/get-info',json={'url':PAGE}).json
        self.assertEqual(data['status'],'interaction_required');self.assertEqual(data['inspection_id'],'a'*32)
    def test_cross_origin_window_open_blocked(self):
        with patch.object(app.site_browser,'show') as show:
            r=app.app.test_client().post('/site-inspection/show',json={'inspection_id':'a'*32},headers={'Origin':'https://evil.example'})
        self.assertEqual(r.status_code,403);show.assert_not_called()
    def test_inspection_show_and_cancel(self):
        with patch.object(app.site_browser,'show') as show,patch.object(app.site_browser,'close') as close:
            for action in ['show','cancel']:
                self.assertEqual(app.app.test_client().post('/site-inspection/'+action,json={'inspection_id':'a'*32}).status_code,200)
        show.assert_called_once();close.assert_called_once()
    def test_headless_mode_clear_error(self):
        with self.assertRaisesRegex(ValueError,'masaüstü'):SiteBrowser().inspect(PAGE)

class BrowserLifecycleTests(unittest.TestCase):
    def test_hidden_window_is_closed_after_metadata(self):
        browser=SiteBrowser();browser.enabled=True
        window=Mock();window.events=SimpleNamespace(loaded=Event(window),closed=Event(window));window.events.loaded.set()
        window.evaluate_js.return_value={'title':'Example','embeds':[EMBED]}
        with patch('webview.windows',[object()]),patch('webview.create_window',return_value=window) as create,patch('services.site_browser.threading.Timer'):
            result=browser.inspect(PAGE)
        self.assertEqual(result['embeds'],[EMBED])
        self.assertTrue(create.call_args.kwargs['hidden']);self.assertIsNone(create.call_args.kwargs['js_api'])
        window.destroy.assert_called_once();self.assertIsNone(browser.session)
    def test_wrong_token_cannot_show_or_cancel_window(self):
        browser=SiteBrowser();window=Mock()
        browser.session={'token':'a'*32,'closed':False,'window':window,'loaded':Mock()}
        with self.assertRaises(ValueError):browser.show('b'*32)
        browser.close('b'*32);window.destroy.assert_not_called()
        browser.close('a'*32);window.destroy.assert_called_once()
    def test_expired_session_stops_timer(self):
        browser=SiteBrowser();window=Mock();timer=Mock()
        session={'token':'a'*32,'closed':False,'window':window,'loaded':Mock(),'timer':timer}
        browser.session=session;browser._closed(session)
        self.assertIsNone(browser.session);timer.cancel.assert_called_once()
