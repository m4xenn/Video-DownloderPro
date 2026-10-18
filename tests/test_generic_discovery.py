"""Offline tests for provider-independent discovery and credential scoping."""
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch
from http.cookiejar import CookieJar
from urllib.request import Request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from yt_dlp.utils import DownloadError
from services.media_discovery import public_url, choose_media
from services.generic_resolver import GenericResolver, apply_source_context, can_discover_after, generic_resolver
from services.site_resolver import extract_media_info, site_resolver
from services.site_browser import BrowserRequired

PAGE='https://cinema.example/watch/something'
FRAME='https://player.example/e/123'
STREAM='https://cdn.example/media/master.m3u8'


def observation(sources=None,**extra):
    return dict(title='Example film',url=PAGE,thumbnail='https://cinema.example/poster.jpg',
                sources=sources or [],embeds=[],**extra)


class DiscoveryPolicyTests(unittest.TestCase):
    def test_public_addresses_only(self):
        for url in ['https://cdn.example/master','http://player.example/video','https://8.8.8.8/a']:
            self.assertTrue(public_url(url))
        for url in [None,{},'file:///secret','https://localhost/a','http://127.0.0.1/a','https://10.0.0.1/a','https://[::1]/a','https://cdn.local/a','https://u:p@cdn.example/a','https://cdn.example:5056/a','https://cdn.example/has space']:
            self.assertFalse(public_url(url))

    def test_dns_private_or_mixed_resolution_rejected(self):
        for addresses in [[(2,1,6,'',('127.0.0.1',443))],[(2,1,6,'',('93.184.216.34',443)),(2,1,6,'',('192.168.1.1',443))]]:
            with patch('services.media_discovery.socket.getaddrinfo',return_value=addresses):
                self.assertFalse(public_url(PAGE,resolve=True))

    def test_fallback_only_for_extraction_failures(self):
        self.assertTrue(can_discover_after(PAGE,DownloadError('Unsupported URL: '+PAGE)))
        for message in ['DRM protected: no video formats','Login required','Network timeout','Private video','Sign in','copyright unsupported URL']:
            self.assertFalse(can_discover_after(PAGE,DownloadError(message)))

    def test_native_success_never_opens_browser(self):
        ydl=Mock();ydl.extract_info.return_value={'id':'native'}
        with patch.object(generic_resolver,'pending',return_value=False),patch.object(generic_resolver,'extract') as fallback:
            self.assertEqual(extract_media_info(ydl,PAGE),{'id':'native'})
        fallback.assert_not_called()

    def test_unsupported_native_uses_discovery(self):
        ydl=Mock();ydl.extract_info.side_effect=DownloadError('Unsupported URL: '+PAGE)
        with patch.object(generic_resolver,'pending',return_value=False),patch.object(generic_resolver,'extract',return_value={'id':'generic'}) as fallback:
            self.assertEqual(extract_media_info(ydl,PAGE,True),{'id':'generic'})
        fallback.assert_called_once_with(ydl,PAGE,fresh=True)

    def test_drm_native_error_is_preserved(self):
        ydl=Mock();ydl.extract_info.side_effect=DownloadError('DRM: no video formats')
        with patch.object(generic_resolver,'pending',return_value=False),patch.object(generic_resolver,'extract') as fallback:
            with self.assertRaises(DownloadError):extract_media_info(ydl,PAGE)
        fallback.assert_not_called()

    def test_existing_site_with_other_provider_can_fallback(self):
        ydl=Mock()
        with patch.object(site_resolver,'extract',side_effect=ValueError('Unknown provider')),patch.object(generic_resolver,'extract',return_value={'id':'new-provider'}) as fallback:
            self.assertEqual(extract_media_info(ydl,'https://www.fullhdfilmizlesene.now/film/other/')['id'],'new-provider')
        fallback.assert_called_once()

    def test_main_video_wins_over_small_ad(self):
        data={'url':PAGE,'media':[{'sources':['https://ads.example/ad.mp4'],'area':10000}, {'sources':[STREAM],'area':300000,'document':FRAME}]}
        selected=choose_media(data)
        self.assertEqual(selected['sources'],[STREAM])
        self.assertEqual(selected['source_headers'][STREAM]['Referer'],FRAME)

    def test_equal_unrelated_videos_are_not_merged(self):
        data={'media':[{'sources':[STREAM],'area':10000},{'sources':['https://ads.example/ad.mp4'],'area':10000}]}
        self.assertIsNone(choose_media(data))

    def test_small_parent_ad_does_not_hide_larger_embedded_player(self):
        data={'media':[{'sources':['https://ads.example/ad.mp4'],'area':10000,'document':PAGE}],
              'embeds':[{'url':FRAME,'area':300000}]}
        self.assertIsNone(choose_media(data))

    def test_same_player_variants_survive(self):
        second=STREAM.replace('master','other-quality')
        data={'media':[{'sources':[STREAM,second],'area':10000},{'sources':[STREAM],'area':10000}]}
        self.assertEqual(choose_media(data)['sources'],[STREAM,second])

    def test_blob_requires_matching_document_and_unique_network_source(self):
        data={'media':[{'sources':[],'blob':True,'document':FRAME,'area':1000}]}
        network=[{'url':STREAM,'headers':{'Referer':FRAME}}]
        self.assertEqual(choose_media(data,network)['sources'],[STREAM])
        self.assertIsNone(choose_media(data,[{'url':STREAM,'headers':{'Referer':PAGE}}]))
        self.assertIsNone(choose_media(data,network+[{'url':STREAM+'?ad=1','headers':{'Referer':FRAME}}]))

    def test_drm_and_private_media_rejected(self):
        with self.assertRaisesRegex(ValueError,'DRM'):choose_media({'drm':True})
        self.assertIsNone(choose_media({'media':[{'sources':['http://127.0.0.1/a']}]}))

    def test_cookie_scoped_to_media_host_and_not_global_header(self):
        ydl=Mock();ydl.params={'http_headers':{'Cookie':'old=secret','Referer':'old','Accept':'*/*'}};ydl.cookiejar=CookieJar()
        apply_source_context(ydl,STREAM,{'Cookie':'session=secret','Referer':FRAME,'User-Agent':'Browser-UA','Authorization':'do-not-copy'})
        self.assertNotIn('Cookie',ydl.params['http_headers']);self.assertNotIn('Authorization',ydl.params['http_headers'])
        same=Request('https://cdn.example/media/segment.ts');ydl.cookiejar.add_cookie_header(same)
        other=Request('https://other.example/media/segment.ts');ydl.cookiejar.add_cookie_header(other)
        outside=Request('https://cdn.example/account');ydl.cookiejar.add_cookie_header(outside)
        subdomain=Request('https://other.cdn.example/media/segment.ts');ydl.cookiejar.add_cookie_header(subdomain)
        self.assertEqual(same.get_header('Cookie'),'session=secret')
        self.assertIsNone(other.get_header('Cookie'));self.assertIsNone(outside.get_header('Cookie'))
        self.assertIsNone(subdomain.get_header('Cookie'))


class GenericTraversalTests(unittest.TestCase):
    def setUp(self):
        self.browser=Mock();self.resolver=GenericResolver(browser=self.browser)
        self.guard=patch('services.generic_resolver.public_url',side_effect=lambda value,resolve=False:public_url(value))
        self.guard.start();self.addCleanup(self.guard.stop)

    def test_history_identity_includes_site_and_meaningful_query(self):
        identity=self.resolver.media_identity
        self.assertNotEqual(identity('https://first.example/watch/123'),identity('https://second.example/watch/123'))
        self.assertNotEqual(identity('https://first.example/watch?id=1'),identity('https://first.example/watch?id=2'))
        self.assertEqual(identity(PAGE),identity(PAGE+'?utm_source=share'))

    def test_nested_frames_keep_top_page_identity(self):
        nested='https://another-player.example/watch/xyz'
        self.browser.discover.side_effect=[observation(embeds_unused=True)|{'embeds':[{'url':FRAME,'area':1000}]},
            {'url':FRAME,'embeds':[{'url':nested,'area':1000}]}, {'url':nested,'sources':[STREAM]}]
        data=self.resolver.details(PAGE)
        self.assertEqual(data['title'],'Example film');self.assertEqual(data['stream'],STREAM)
        self.assertEqual(self.browser.discover.call_args.kwargs['parent_url'],FRAME)

    def test_cycles_and_frame_count_bounded(self):
        self.browser.discover.side_effect=lambda url,parent_url=None:{'url':url,'embeds':[{'url':PAGE,'area':1000},{'url':url+'/next','area':1000}]}
        with self.assertRaisesRegex(ValueError,'bulunamadı'):self.resolver.details(PAGE)
        self.assertLessEqual(self.browser.discover.call_count,6)

    def test_handoff_resumes_exact_frame(self):
        self.browser.discover.side_effect=[observation()|{'embeds':[{'url':FRAME,'area':1000}]},BrowserRequired('a'*32),{'url':FRAME,'sources':[STREAM]}]
        with self.assertRaises(BrowserRequired):self.resolver.details(PAGE)
        self.assertTrue(self.resolver.pending(PAGE))
        self.assertEqual(self.resolver.details(PAGE)['stream'],STREAM)
        self.assertEqual([call.args[0] for call in self.browser.discover.call_args_list],[PAGE,FRAME,FRAME])

    def test_cache_and_fresh_resolution(self):
        now=[0];self.resolver.clock=lambda:now[0]
        self.browser.discover.return_value=observation([STREAM])
        self.resolver.details(PAGE);self.resolver.details(PAGE)
        self.assertEqual(self.browser.discover.call_count,1)
        self.resolver.details(PAGE,fresh=True)
        self.assertEqual(self.browser.discover.call_count,1)
        now[0]=61
        self.resolver.details(PAGE,fresh=True)
        self.assertEqual(self.browser.discover.call_count,2)

    def test_native_lookup_does_not_wait_for_browser_work(self):
        started=threading.Event();release=threading.Event()
        def inspect(*args,**kwargs):
            started.set();release.wait(3)
            return observation([STREAM])
        self.browser.discover.side_effect=inspect
        worker=threading.Thread(target=lambda:self.resolver.details(PAGE))
        worker.start()
        try:
            self.assertTrue(started.wait(1))
            done=threading.Event()
            check=threading.Thread(target=lambda:(self.resolver.pending('https://youtube.com/watch?v=other'),done.set()))
            check.start()
            self.assertTrue(done.wait(.5),'Native extraction lookup blocked by hidden browser')
            check.join(1)
        finally:
            release.set();worker.join(3)

    def test_private_redirect_and_frame_never_accepted(self):
        self.browser.discover.return_value={'url':'http://127.0.0.1/private','sources':[STREAM]}
        with self.assertRaises(ValueError):self.resolver.details(PAGE)
        self.assertFalse(self.resolver.pending(PAGE))

    def test_expired_handoff_does_not_skip_native_forever(self):
        now=[0];resolver=GenericResolver(browser=self.browser,clock=lambda:now[0])
        self.browser.discover.side_effect=BrowserRequired('a'*32)
        with self.assertRaises(BrowserRequired):resolver.details(PAGE)
        now[0]=181
        self.assertFalse(resolver.pending(PAGE))

    def test_drm_does_not_try_another_player(self):
        self.browser.discover.side_effect=ValueError('DRM korumalı')
        with self.assertRaisesRegex(ValueError,'DRM'):self.resolver.details(PAGE)
        self.assertEqual(self.browser.discover.call_count,1)


if __name__=='__main__':unittest.main()
