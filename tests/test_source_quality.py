"""Real yt-dlp selector evaluation against source format fixtures; no network."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from services.source_quality import source_qualities, parse_source_quality
from services.media_catalog import MediaCatalog
from core.format_resolver import get_ydl_opts
import app
from state.app_state import state
from yt_dlp import YoutubeDL

FORMATS=[{'format_id':str(h)+'-'+str(f),'url':f'https://example.com/{h}-{f}.mp4','ext':'mp4',
          'height':h,'width':h*16//9,'fps':f,'vcodec':'avc1','acodec':'aac','protocol':'https'}
         for h,f in [(720,30),(1080,30),(1080,60),(2160,30)]]

class SourceQualityTests(unittest.TestCase):
    def choose(self,quality,formats):
        options=get_ydl_opts('video',quality,str(ROOT),0,False,lambda _:None,'')
        with YoutubeDL({'quiet':True,'skip_download':True,'format':options['format'],
                        'format_sort':options.get('format_sort',[])}) as ydl:
            result=ydl.process_ie_result({'id':'video','title':'Test','extractor':'Generic',
                'webpage_url':'https://example.com/video','formats':formats},download=False)
        return result['height'], result['fps']

    def test_max_selects_independent_best_for_each_video(self):
        self.assertEqual(self.choose('max',FORMATS),(2160,30))
        self.assertEqual(self.choose('max',FORMATS[:1]),(720,30))

    def test_selected_source_resolution_and_fps(self):
        self.assertEqual(self.choose('source:1080:30',FORMATS),(1080,30))
        self.assertEqual(self.choose('source:1080:60',FORMATS),(1080,60))

    def test_fractional_frame_rate_survives_display_rounding(self):
        formats=[dict(FORMATS[1],fps=30000/1001)]
        choice=source_qualities({'formats':formats})[0]
        self.assertEqual(self.choose(choice['value'],formats)[0],1080)

    def test_no_arbitrary_selector_or_out_of_range_value(self):
        for value in ['source:1080:60]/best','source:0:30','source:20000:30','source:720:999','mp3']:
            self.assertIsNone(parse_source_quality(value))

    def test_choices_deduplicate_and_exclude_drm_audio_storyboards(self):
        formats=FORMATS+[FORMATS[0],dict(FORMATS[0],height=144,has_drm=True),
                         dict(FORMATS[0],height=90,vcodec='images'),dict(FORMATS[0],height=480,vcodec='none')]
        choices=source_qualities({'formats':formats})
        self.assertEqual(len(choices),4)
        self.assertEqual(choices[0]['value'],'source:2160:30')

    def test_unknown_sizes_not_presented_as_complete(self):
        choices=source_qualities({'formats':[dict(FORMATS[0],acodec='none',filesize=1000)]})
        self.assertIsNone(choices[0]['total_bytes'])

    def test_catalog_keeps_only_public_quality_metadata(self):
        catalog=MediaCatalog();catalog.remember('https://example.com/video',{'formats':FORMATS})
        item=catalog.lookup('https://example.com/video')
        self.assertEqual(len(item['video_qualities']),4)
        self.assertNotIn('url',item['video_qualities'][0])

    def test_api_rejects_source_quality_in_bulk_or_unknown_choice(self):
        catalog=MediaCatalog();catalog.remember('https://example.com/a',{'formats':FORMATS})
        original=state['current_download_path'];state['current_download_path']=str(ROOT)
        try:
            with patch.object(app,'media_catalog',catalog),patch.object(app,'ensure_download_state'),patch.object(app,'prepare_download') as submit:
                submit.return_value=({'status':'success'},202)
                client=app.app.test_client()
                data={'urls':['https://example.com/a'],'format':'video','quality':'source:1080:60'}
                self.assertEqual(client.post('/download',json=data).status_code,202)
                self.assertEqual(submit.call_args.args[1]['quality'],'source:1080:60')
                self.assertEqual(client.post('/download',json=dict(data,quality='source:4320:60')).status_code,400)
                self.assertEqual(client.post('/download',json=dict(data,urls=['https://example.com/a','https://example.com/b'])).status_code,400)
                self.assertEqual(client.post('/download',json=dict(data,is_playlist=True)).status_code,400)
        finally: state['current_download_path']=original

if __name__=='__main__': unittest.main()
