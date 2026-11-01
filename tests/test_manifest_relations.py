"""Explicit master evidence must improve selection without mixing unrelated videos."""
from pathlib import Path
import sys,unittest,json
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.manifest_relations import variant_links,verified_hls_root,ManifestRelations,MAX_MANIFEST_BYTES
from services.network_media import select_network_media

PAGE='https://player.example/watch';MASTER='https://cdn.example/master.m3u8';LOW='https://cdn.example/low.m3u8';HIGH='https://cdn.example/high.m3u8'
def response(url,variants=()):return {'url':url,'mime':'application/vnd.apple.mpegurl','status':200,'kind':'hls','document':PAGE,'headers':{'Referer':PAGE},'variants':list(variants)}
def snapshot():return {'url':PAGE,'media':[{'document':PAGE,'area':200000,'sources':[],'blob':True}]}

class ManifestTests(unittest.TestCase):
    def test_parse_only_explicit_variant_and_audio_uris(self):
        body=b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nlow.m3u8\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",URI="audio.m3u8"\n#EXT-X-KEY:METHOD=AES-128,URI="key"\n#EXTINF:5,\nsegment.ts\n'
        self.assertEqual(variant_links(MASTER,body),[LOW,'https://cdn.example/audio.m3u8'])
    def test_subtitle_and_trickplay_playlists_are_explicitly_related(self):
        body=b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nlow.m3u8\n#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="s",URI="subs.m3u8"\n#EXT-X-I-FRAME-STREAM-INF:BANDWIDTH=2,URI="iframe.m3u8"\n'
        self.assertEqual(variant_links(MASTER,body),[LOW,'https://cdn.example/subs.m3u8','https://cdn.example/iframe.m3u8'])
    def test_related_subtitles_do_not_become_a_separate_video(self):
        sub='https://cdn.example/subs.m3u8'
        self.assertEqual(select_network_media(snapshot(),[response(MASTER,[LOW,sub]),response(LOW),response(sub)])['sources'],[MASTER])

    def test_master_and_observed_variants_collapse_to_master(self):
        result=select_network_media(snapshot(),[response(MASTER,[LOW,HIGH]),response(LOW),response(HIGH)])
        self.assertEqual(result['sources'],[MASTER])
    def test_unrelated_ad_manifest_is_still_ambiguous(self):
        self.assertIsNone(select_network_media(snapshot(),[response(MASTER,[LOW]),response(LOW),response('https://ads.example/ad.m3u8')]))
    def test_nearby_urls_without_manifest_evidence_are_not_related(self):
        self.assertIsNone(select_network_media(snapshot(),[response(MASTER),response(LOW)]))
    def test_cycles_are_rejected_even_below_a_root(self):
        self.assertIsNone(verified_hls_root({MASTER:response(MASTER,[LOW]),LOW:response(LOW,[HIGH]),HIGH:response(HIGH,[LOW])}))
    def test_mixed_hls_and_file_not_collapsed(self):
        self.assertIsNone(verified_hls_root({MASTER:response(MASTER,[LOW]),LOW:dict(response(LOW),kind='file')}))
    def test_drm_and_verification_remain_blocked(self):
        for flag in ['drm','verification']:
            self.assertIsNone(select_network_media(dict(snapshot(),**{flag:True}),[response(MASTER,[LOW]),response(LOW)]))
    def test_enrichment_never_follows_redirects_or_copies_authorization(self):
        reply=Mock();reply.__enter__=Mock(return_value=reply);reply.__exit__=Mock(return_value=False)
        reply.status_code=302;reply.headers={}
        fetch=Mock(return_value=reply);relations=ManifestRelations(fetch=fetch)
        records=[dict(response(MASTER),headers={'Cookie':'scoped','Authorization':'never','Referer':PAGE}),response(LOW)]
        with patch('services.media_discovery.public_url',return_value=True):relations.enrich(records)
        self.assertFalse(fetch.call_args_list[0].kwargs['allow_redirects'])
        self.assertNotIn('Authorization',fetch.call_args_list[0].kwargs['headers'])
    def test_read_budget_and_attempts_are_bounded(self):
        reply=Mock();reply.__enter__=Mock(return_value=reply);reply.__exit__=Mock(return_value=False)
        reply.status_code=200;reply.headers={'Content-Type':'application/vnd.apple.mpegurl'}
        reply.iter_content.side_effect=lambda *_:iter([b'x'*(MAX_MANIFEST_BYTES+1)])
        fetch=Mock(return_value=reply);relations=ManifestRelations(fetch=fetch)
        records=[response('https://cdn.example/'+str(i)+'.m3u8') for i in range(20)]
        with patch('services.media_discovery.public_url',return_value=True):
            result=relations.enrich(records);relations.enrich(records)
        self.assertLessEqual(fetch.call_count,6);self.assertTrue(all(not r['variants'] for r in result))
    def test_late_rendition_keeps_original_master_evidence(self):
        reply=Mock();reply.__enter__=Mock(return_value=reply);reply.__exit__=Mock(return_value=False)
        reply.status_code=200;reply.headers={'Content-Type':'application/vnd.apple.mpegurl'}
        reply.iter_content.side_effect=[iter([b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nlow.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=2\nhigh.m3u8\n']),iter([b'#EXTM3U\n#EXTINF:5,\nsegment.ts\n']),iter([b'#EXTM3U\n#EXTINF:5,\nsegment.ts\n'])]
        relations=ManifestRelations(fetch=Mock(return_value=reply))
        with patch('services.media_discovery.public_url',return_value=True):
            relations.enrich([response(MASTER),response(LOW)])
            enriched=relations.enrich([response(MASTER),response(LOW),response(HIGH)])
        self.assertEqual(select_network_media(snapshot(),enriched)['sources'],[MASTER])

    def test_browser_response_body_supplies_exact_manifest_evidence(self):
        from services.webview_frames import NativeFrames
        probe=NativeFrames(object())
        for record in [response(MASTER),response(LOW),response(HIGH)]:
            probe.observe_response({'requestId':record['url'],'response':{'url':record['url'],'mimeType':record['mime'],'status':200},'type':'Fetch'})
            probe.media_responses[record['url']]['document']=PAGE
        probe.observe_response_body(MASTER,json.dumps({'body':'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nlow.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=2\nhigh.m3u8\n','base64Encoded':False}))
        self.assertEqual(select_network_media(snapshot(),probe.network_candidates())['sources'],[MASTER])
        probe.close();self.assertFalse(probe.response_keys)
    def test_invalid_or_oversized_browser_payload_is_ignored(self):
        from services.webview_frames import NativeFrames
        probe=NativeFrames(object())
        for payload in ['{bad','[]','x'*(MAX_MANIFEST_BYTES*2+1),json.dumps({'body':'%%%','base64Encoded':True})]:
            probe.observe_response_body(MASTER,payload)
        self.assertFalse(probe.media_responses)

    def test_private_manifest_is_not_fetched(self):
        fetch=Mock();relations=ManifestRelations(fetch=fetch)
        with patch('services.media_discovery.public_url',return_value=False):relations.enrich([response(MASTER),response(LOW)])
        fetch.assert_not_called()

if __name__=='__main__':unittest.main()
