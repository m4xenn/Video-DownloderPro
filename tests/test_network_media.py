from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.network_media import media_kind,select_network_media
from services.webview_frames import NativeFrames

PAGE='https://player.example/watch'
SOURCE='https://cdn.example/opaque'


class NetworkMediaTests(unittest.TestCase):
    def snapshot(self):return {'url':PAGE,'players':[{'document':PAGE,'area':200000,'kind':'canvas'}]}
    def response(self,url=SOURCE):return {'url':url,'mime':'application/vnd.apple.mpegurl','status':200,'document':PAGE,'headers':{'Referer':PAGE}}
    def test_extensionless_manifest_with_no_dom_source(self):
        result=select_network_media(self.snapshot(),[self.response()])
        self.assertEqual(result['sources'],[SOURCE]);self.assertEqual(result['discovery_method'],'network')
    def test_html_failed_and_segments_not_candidates(self):
        for url,mime,status in [(SOURCE,'text/html',200),(SOURCE,'video/mp4',403),
                               (SOURCE+'.m3u8','application/json',200),('https://cdn.example/a.ts','video/mp2t',200),
                               ('https://cdn.example/init.mp4','video/mp4',200),('https://cdn.example/a.m4s','video/mp4',200)]:
            self.assertIsNone(media_kind(url,mime,status))
    def test_manifest_and_direct_types(self):
        self.assertEqual(media_kind(SOURCE,'application/dash+xml',200),'dash')
        self.assertEqual(media_kind(SOURCE,'video/mp4',206),'file')
    def test_unrelated_document_and_private_source_not_used(self):
        for response in [dict(self.response(),document='https://ads.example/'),self.response('http://127.0.0.1/video.m3u8')]:
            self.assertIsNone(select_network_media(self.snapshot(),[response]))
    def test_no_player_evidence_no_network_guess(self):
        self.assertIsNone(select_network_media({'url':PAGE},[self.response()]))
    def test_worker_document_can_use_observed_player_referer(self):
        response=dict(self.response(),document='https://player.example/worker.js',worker=True)
        self.assertEqual(select_network_media(self.snapshot(),[response])['sources'],[SOURCE])
    def test_multiple_unlinked_manifests_remain_ambiguous(self):
        self.assertIsNone(select_network_media(self.snapshot(),[self.response(),self.response(SOURCE+'/other')]))
    def test_manifest_not_preferred_over_unrelated_video_file(self):
        file=dict(self.response(SOURCE+'/feature.mp4'),mime='video/mp4')
        self.assertIsNone(select_network_media(self.snapshot(),[self.response(),file]))
    def test_verification_and_drm_stop_network_selection(self):
        for flag in ('verification','drm'):
            self.assertIsNone(select_network_media(dict(self.snapshot(),**{flag:True}),[self.response()]))
    def test_dom_match_preserves_quality_variants(self):
        snapshot={'url':PAGE,'media':[{'document':PAGE,'area':200000,'sources':[SOURCE,SOURCE+'/720']} ]}
        self.assertEqual(set(select_network_media(snapshot,[self.response()])['sources']),{SOURCE,SOURCE+'/720'})
    def test_blob_and_jw_same_player_keep_other_qualities(self):
        snapshot={'url':PAGE,'media':[{'document':PAGE,'area':200000,'sources':[],'blob':True,'duration':120},
                                    {'document':PAGE,'area':200000,'sources':[SOURCE,SOURCE+'/720']} ]}
        self.assertEqual(set(select_network_media(snapshot,[self.response()])['sources']),{SOURCE,SOURCE+'/720'})
    def test_equal_players_do_not_merge(self):
        other=SOURCE+'/other'
        snapshot={'url':PAGE,'media':[{'document':PAGE,'area':200000,'sources':[SOURCE]},
                                    {'document':PAGE,'area':200000,'sources':[other]}]}
        self.assertIsNone(select_network_media(snapshot,[self.response(),self.response(other)]))
    def test_larger_unloaded_iframe_prevents_parent_ad_selection(self):
        snapshot=self.snapshot();snapshot['embeds']=[{'url':'https://embed.example/player','area':600000}]
        self.assertIsNone(select_network_media(snapshot,[self.response()]))
    def test_pending_main_player_not_replaced_by_requested_ad(self):
        snapshot={'url':PAGE,'media':[{'document':PAGE,'area':400000,'sources':[SOURCE+'/main']},
                                    {'document':PAGE,'area':10000,'sources':[SOURCE]}]}
        self.assertIsNone(select_network_media(snapshot,[self.response()]))
    def test_unknown_main_does_not_consume_known_ad_request(self):
        snapshot={'url':PAGE,'media':[{'document':PAGE,'area':400000,'sources':[],'blob':True},
                                    {'document':PAGE,'area':10000,'sources':[SOURCE]}]}
        self.assertIsNone(select_network_media(snapshot,[self.response()]))
    def test_cdp_response_uses_actual_document_and_exact_headers(self):
        probe=NativeFrames(object());probe.request_documents[('child','1')]=PAGE
        probe.requests[SOURCE]={'Cookie':'private','Authorization':'never-copy','Referer':PAGE}
        probe.observe_response({'requestId':'1','type':'Fetch','response':{'url':SOURCE,'status':200,'mimeType':'application/vnd.apple.mpegurl'}},'child')
        result=probe.network_candidates()[0]
        self.assertEqual(result['document'],PAGE);self.assertEqual(result['headers'],{'Cookie':'private','Referer':PAGE})
        probe.close();self.assertEqual(probe.network_candidates(),[])
    def test_response_buffer_bounded_and_closed_probe_ignores_events(self):
        probe=NativeFrames(object())
        for i in range(100):probe.observe_response({'response':{'url':SOURCE+str(i),'mimeType':'video/mp4','status':200}})
        self.assertEqual(len(probe.network_candidates()),40)
        probe.close();probe.observe_response({'response':{'url':SOURCE,'mimeType':'video/mp4','status':200}})
        self.assertEqual(probe.network_candidates(),[])


if __name__=='__main__':unittest.main()
