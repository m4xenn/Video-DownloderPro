"""Frame observations must preserve document ancestry and ignore unrelated ads."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.webview_frames import merge_frames,NativeFrames
from services.site_browser import SiteBrowser

ROOT='https://watch.example/episode/1'
OUTER='https://embed.example/wrapper'
PLAYER='https://player.example/embed/123'
STREAM='https://cdn.example/master.m3u8'


class FrameMergeTests(unittest.TestCase):
    def root(self):return {'url':ROOT,'media':[],'embeds':[{'url':OUTER,'area':300000}],'drm':False,'interaction':False}
    def frames(self):
        return [{'key':1,'parent':None,'snapshot':{'url':OUTER,'media':[],'embeds':[{'url':PLAYER,'area':400000}]}},
                {'key':2,'parent':1,'snapshot':{'url':PLAYER,'media':[{'sources':[STREAM],'area':500000,'document':PLAYER}]}}]

    def test_parent_chain_retained_and_player_area_bounded(self):
        result=merge_frames(self.root(),self.frames())
        self.assertEqual(result['media'][0]['sources'],[STREAM])
        self.assertEqual(result['media'][0]['document'],PLAYER)
        self.assertEqual(result['media'][0]['area'],300000)

    def test_out_of_order_native_events_supported(self):
        self.assertEqual(len(merge_frames(self.root(),list(reversed(self.frames())))['media']),1)

    def test_unrelated_frame_and_pixel_frame_not_promoted(self):
        unrelated={'key':3,'parent':None,'snapshot':{'url':'https://ads.example/ad','media':[{'sources':['https://ads.example/ad.mp4'],'area':999999}]}}
        root=self.root();root['embeds'].append({'url':'https://ads.example/ad','area':1})
        self.assertEqual(len(merge_frames(root,self.frames()+[unrelated])['media']),1)

    def test_frame_without_dom_ancestry_not_accepted(self):
        frames=self.frames();frames[1]['parent']=None
        self.assertEqual(merge_frames(self.root(),frames)['media'],[])

    def test_drm_and_interaction_propagated(self):
        frames=self.frames();frames[1]['snapshot'].update(drm=True,interaction=True)
        result=merge_frames(self.root(),frames)
        self.assertTrue(result['drm']);self.assertTrue(result['interaction'])

    def test_private_child_not_accepted(self):
        frames=self.frames();frames[1]['snapshot']['url']='http://127.0.0.1/secrets'
        self.assertEqual(merge_frames(self.root(),frames)['media'],[])

    def test_unsupported_backend_has_clean_fallback(self):
        frames=NativeFrames(object())
        self.assertFalse(frames.attach());self.assertEqual(frames.read('1'),[])
        frames.close();self.assertFalse(frames.active)

    def test_headers_belong_to_exact_source_and_exclude_unknown_credentials(self):
        frames=NativeFrames(object())
        frames.requests[STREAM]={'origin':'https://player.example','referer':PLAYER,'user-agent':'Browser-UA','cookie':'session=private','Authorization':'never-copy','X-Secret':'never-copy'}
        contexts=frames.headers([STREAM,'https://other.example/master.m3u8'])
        self.assertEqual(contexts[STREAM],{'Origin':'https://player.example','Referer':PLAYER,'User-Agent':'Browser-UA','Cookie':'session=private'})
        self.assertEqual(contexts['https://other.example/master.m3u8'],{})
        frames.close();self.assertEqual(frames.requests,{})

    def test_continue_recreates_visible_control_once_and_keeps_token(self):
        browser=SiteBrowser();window=Mock();replacement=Mock()
        browser.session={'token':'a'*32,'closed':False,'window':window,'loaded':Mock(),'target':ROOT,'discovery':True}
        session=browser.session
        def create_visible(session,visible=False):session['window']=replacement
        with patch.object(browser,'_create_window',side_effect=create_visible) as create:
            browser.show('a'*32);browser.show('a'*32)
        create.assert_called_once_with(session,visible=True)
        window.destroy.assert_called_once();replacement.show.assert_called_once()
        self.assertEqual(session['token'],'a'*32);self.assertFalse(session['closed'])

    def test_continue_does_not_reload_verification_session(self):
        browser=SiteBrowser();window=Mock()
        browser.session={'token':'a'*32,'closed':False,'window':window,'loaded':Mock(),'target':ROOT,'discovery':True,'shown':True}
        browser.show('a'*32)
        window.show.assert_called_once();window.load_url.assert_not_called()
