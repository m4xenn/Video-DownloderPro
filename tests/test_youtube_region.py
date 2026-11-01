import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from yt_dlp.extractor.youtube import YoutubeIE
from services.youtube_region import extract_info, COUNTRIES
from services.source_operation import source_operation

def media():
    return {"id":"ok","formats":[{"url":"https://cdn.example/video.mp4","vcodec":"h264","acodec":"aac"}]}

URL='https://www.youtube.com/watch?v=_hJNUVZPRuc'
class YoutubeRegionTests(unittest.TestCase):
    def engine(self):
        engine=YoutubeDL({'quiet':True,'ignoreerrors':True})
        self.addCleanup(engine.close)
        return engine

    def test_success_does_not_change_extractor(self):
        y=self.engine();original=y.get_info_extractor('Youtube')
        with patch.object(y,'extract_info',return_value={'id':'ok'}) as call:
            self.assertEqual(extract_info(y,URL),{'id':'ok'})
        call.assert_called_once_with(URL,download=False)
        self.assertIs(y.get_info_extractor('Youtube'),original)
        self.assertTrue(y.params['ignoreerrors'])

    def test_scoped_country_retry_and_deep_copy(self):
        y=self.engine();original=y.get_info_extractor('Youtube')
        context={'client':{'gl':'TR','nested':{'a':1}}};seen=[]
        def attempt(url,download):
            seen.append(y.get_info_extractor('Youtube'))
            if len(seen)==1:raise DownloadError('Video unavailable. This country domain is restricted.')
            with patch.object(YoutubeIE,'_extract_context',return_value=context):
                self.assertEqual(seen[-1]._extract_context()['client']['gl'],'DE')
            return media()
        with patch.object(y,'extract_info',side_effect=attempt):
            self.assertEqual(extract_info(y,URL)['youtube_player_country'],'DE')
        self.assertEqual(len(seen),2)
        self.assertIsNot(seen[0],seen[1]);self.assertEqual(context['client']['gl'],'TR')
        self.assertIs(y.get_info_extractor('Youtube'),original)
        self.assertTrue(y.params['ignoreerrors'])

    def test_retry_failure_restores_instance(self):
        y=self.engine();original=y.get_info_extractor('Youtube')
        with patch.object(y,'extract_info',side_effect=DownloadError('Video unavailable')) as call:
            with self.assertRaises(DownloadError):extract_info(y,URL)
        self.assertEqual(call.call_count,1+len(COUNTRIES))
        self.assertIs(y.get_info_extractor('Youtube'),original)
        self.assertTrue(y.params['ignoreerrors'])

    def test_other_failures_and_hosts_are_not_retried(self):
        for url,message in [(URL,'HTTP Error 429'),(URL,'Private video'),
                            ('https://youtube.com.evil.example/watch?v=x','Video unavailable'),
                            ('https://example.com/video','Video unavailable')]:
            with self.subTest(url=url,message=message):
                y=self.engine()
                with patch.object(y,'extract_info',side_effect=DownloadError(message)) as call:
                    with self.assertRaises(DownloadError):extract_info(y,url)
                self.assertEqual(call.call_count,1)

    def test_other_instances_unaffected(self):
        y=self.engine();other=self.engine();original=other.get_info_extractor('Youtube')
        with patch.object(y,'extract_info',side_effect=[DownloadError('Video unavailable'),media()]):
            extract_info(y,URL)
        self.assertIs(other.get_info_extractor('Youtube'),original)


    def test_tries_later_country_and_stops_at_success(self):
        y=self.engine();seen=[]
        def attempt(url,download):
            self.assertFalse(download)
            if not seen:
                seen.append('normal');raise DownloadError('Video unavailable')
            with patch.object(YoutubeIE,'_extract_context',return_value={'client':{}}):
                country=y.get_info_extractor('Youtube')._extract_context()['client']['gl']
            seen.append(country)
            if country=='DE':raise DownloadError('Video unavailable')
            return media()
        stages=[]
        with patch.object(y,'extract_info',side_effect=attempt),source_operation(stages.append):
            info=extract_info(y,URL)
        self.assertEqual(seen,['normal','DE','US'])
        self.assertEqual(info['youtube_player_country'],'US')
        self.assertIn('searching_regions',stages)

    def test_rejects_storyboards_empty_and_drm_results(self):
        y=self.engine()
        cases=[None,{'id':'empty'},
               {'formats':[{'url':'https://cdn.example/story','ext':'mhtml'}]},
               {'formats':[{'url':'https://cdn.example/drm','has_drm':True}]}]
        with patch.object(y,'extract_info',side_effect=[DownloadError('Video unavailable'),*cases,media()]) as call:
            info=extract_info(y,URL)
        self.assertEqual(call.call_count,6)
        self.assertEqual(info['youtube_player_country'],COUNTRIES[4])

    def test_throttling_during_search_stops_immediately(self):
        y=self.engine();original=y.get_info_extractor('Youtube')
        with patch.object(y,'extract_info',side_effect=[DownloadError('Video unavailable'),DownloadError('HTTP Error 429')]) as call:
            with self.assertRaisesRegex(DownloadError,'429'):extract_info(y,URL)
        self.assertEqual(call.call_count,2)
        self.assertIs(y.get_info_extractor('Youtube'),original)

    def test_time_budget_stops_search(self):
        y=self.engine()
        with patch('services.youtube_region.time.monotonic',side_effect=[0,0,46]),patch.object(y,'extract_info',side_effect=DownloadError('Video unavailable')) as call:
            with self.assertRaises(DownloadError):extract_info(y,URL)
        self.assertEqual(call.call_count,2)

    def test_cancelled_search_stops_before_country_request(self):
        y=self.engine()
        with patch.object(y,'extract_info',side_effect=DownloadError('Video unavailable')) as call,source_operation(cancelled=lambda:True):
            with self.assertRaisesRegex(Exception,'DOWNLOAD_PAUSED'):extract_info(y,URL)
        self.assertEqual(call.call_count,1)

    def test_restores_timeouts_on_success_and_failure(self):
        for succeeds in (True,False):
            y=self.engine();y.params.update(socket_timeout=19,extractor_retries=4)
            def attempt(url,download):
                if y.params['socket_timeout']==19:raise DownloadError('Video unavailable')
                self.assertEqual(y.params['socket_timeout'],8)
                self.assertEqual(y.params['extractor_retries'],0)
                if succeeds:return media()
                raise DownloadError('Video unavailable')
            with patch.object(y,'extract_info',side_effect=attempt):
                if succeeds:extract_info(y,URL)
                else:
                    with self.assertRaises(DownloadError):extract_info(y,URL)
            self.assertEqual(y.params['socket_timeout'],19)
            self.assertEqual(y.params['extractor_retries'],4)

    def test_download_only_after_finding_playable_country(self):
        y=self.engine()
        with patch.object(y,'extract_info',side_effect=[DownloadError('Video unavailable'),media()]) as probe,patch.object(y,'process_ie_result',return_value={'downloaded':True}) as transfer:
            self.assertEqual(extract_info(y,URL,download=True),{'downloaded':True})
        self.assertEqual(probe.call_args_list[0].kwargs,{'download':True})
        self.assertEqual(probe.call_args_list[1].kwargs,{'download':False})
        transfer.assert_called_once()

if __name__=='__main__':unittest.main()
