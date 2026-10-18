import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.source_operation import source_operation,current_operation
from services.source_recovery import same_media,has_partial,source_checkpoint,can_resume_embedded
from services.site_browser import SiteBrowser
from core.downloader import _download_single
from core.bandwidth import DownloadPaused

URL='https://watch.example/video'


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]);self.base=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def info(self):return {'id':'video','duration':120,'height':1080,'width':1920,'fps':30,'vcodec':'h264','acodec':'aac','ext':'mp4','protocol':'m3u8_native','extractor_key':'EmbeddedMedia'}

    def run_download(self,second=None,partial=False,bytes_seen=False,always=False):
        released=[];phases=[];errors=[];captured={};calls=[]
        ydl=Mock();ydl.params={'outtmpl':{'default':'unused'}}
        ydl.__enter__=Mock(return_value=ydl);ydl.__exit__=Mock(return_value=False)
        ydl.prepare_filename.return_value=str(self.base/'video.mp4')
        def create(options):captured.update(options);return ydl
        def extract(*_,**__):
            current_operation().releases.append(lambda:released.append(True))
            return self.info()
        def process(info,download):
            calls.append(info)
            if len(calls)==1 or always:
                if len(calls)==1:self.assertFalse(released)
                if partial:(self.base/'video.mp4.part').write_bytes(b'partial')
                if bytes_seen:captured['progress_hooks'][0]({'status':'downloading','downloaded_bytes':4})
                raise RuntimeError('HTTP Error 403: Forbidden')
            template=ydl.params['outtmpl']['default']
            output=self.base/'video.mp4' if template=='unused' else Path(template.replace('%(ext)s','mp4'))
            output.write_bytes(b'video')
            captured['progress_hooks'][0]({'status':'downloading','downloaded_bytes':5})
            self.assertTrue(released)
            return info
        ydl.process_ie_result.side_effect=process
        with patch('yt_dlp.YoutubeDL',side_effect=create),patch('services.site_resolver.extract_media_info',side_effect=extract),patch('services.source_recovery.refresh_source',return_value=second or self.info()) as refresh:
            result=_download_single(URL,{},str(self.base),{'format':'video','_stage':phases.append,'_error':errors.append})
        self.assertTrue(released)
        return result,refresh.call_count,calls,phases,errors

    def test_one_refresh_before_bytes_and_release_on_progress(self):
        result,count,calls,phases,_=self.run_download()
        self.assertTrue(result);self.assertEqual(count,1);self.assertEqual(len(calls),2)
        self.assertIn('refreshing_source',phases)
    def test_partial_file_not_appended_to_new_source(self):
        result,count,_,_,_=self.run_download(partial=True)
        self.assertFalse(result);self.assertEqual(count,0)
        self.assertEqual((self.base/'video.mp4.part').read_bytes(),b'partial')
    def test_received_bytes_stop_refresh(self):
        self.assertEqual(self.run_download(bytes_seen=True)[:2],(False,0))
    def test_second_403_stops_after_one_refresh(self):
        result,count,calls,_,errors=self.run_download(always=True)
        self.assertFalse(result);self.assertEqual(count,1);self.assertEqual(len(calls),2)
        self.assertIn('403',errors[0])
    def test_changed_quality_rejected(self):
        result,count,calls,_,_=self.run_download(second=dict(self.info(),height=720))
        self.assertFalse(result);self.assertEqual(count,1);self.assertEqual(len(calls),1)
    def test_new_submission_does_not_reuse_preserved_partial(self):
        partial=self.base/'video.mp4.part';partial.write_bytes(b'old media')
        result,_,_,_,_=self.run_download()
        self.assertTrue(result);self.assertEqual(partial.read_bytes(),b'old media')
        self.assertTrue((self.base/'video (1).mp4').is_file())
    def test_same_media_rejects_unknown_duration_live_and_changed_id(self):
        for change in [{'duration':None},{'duration':float('nan')},{'is_live':True},{'id':'other'},{'acodec':'opus'}]:
            self.assertFalse(same_media(self.info(),dict(self.info(),**change)))
    def test_empty_part_and_zero_checkpoint_are_safe(self):
        (self.base/'video.mp4.part').write_bytes(b'')
        (self.base/'video.mp4.ytdl').write_text(json.dumps({'downloader':{'current_fragment':{'index':0}}}))
        self.assertFalse(has_partial(self.base/'video.mp4'))
        (self.base/'video.mp4.ytdl').write_text('broken')
        self.assertTrue(has_partial(self.base/'video.mp4'))
    def test_browser_retained_until_operation_release(self):
        browser=SiteBrowser();window=Mock();session={'token':'a'*32,'window':window,'closed':False}
        browser.session=session
        with source_operation(retain=True) as operation:
            browser.finish_source(session)
            self.assertIsNone(browser.session);window.destroy.assert_not_called()
            self.assertEqual(len(browser.handoffs),1)
            operation.release();window.destroy.assert_called_once()
            self.assertFalse(browser.handoffs)
    def test_exception_always_releases_context(self):
        release=Mock()
        with self.assertRaises(RuntimeError):
            with source_operation() as operation:
                operation.releases.append(release);raise RuntimeError()
        release.assert_called_once();self.assertIsNone(current_operation())
    def test_browser_slot_wait_cancellable_and_slots_reusable(self):
        with source_operation(retain=True) as first:
            first.acquire_browser()
            with source_operation(retain=True) as second:
                second.acquire_browser()
                with source_operation(retain=True,cancelled=lambda:True) as cancelled:
                    with self.assertRaises(DownloadPaused):cancelled.acquire_browser()
        with source_operation(retain=True) as fresh:
            fresh.acquire_browser();self.assertTrue(fresh.browser_held)
    def test_preview_handoff_is_adopted_by_download_and_released(self):
        browser=SiteBrowser();window=Mock();session={'token':'b'*32,'window':window,'closed':False}
        browser.session=session
        with source_operation(retain='preview') as preview:
            preview.acquire_browser();token=browser.finish_source(session)
        window.destroy.assert_not_called()
        with source_operation(retain=True) as download:
            browser.adopt_handoff(token)
            window.destroy.assert_not_called()
            download.release()
        window.destroy.assert_called_once();self.assertFalse(browser.handoffs)
        self.assertFalse(preview.browser_held)
    def test_preview_exception_is_not_left_alive(self):
        browser=SiteBrowser();window=Mock();browser.session={'token':'c'*32,'window':window,'closed':False}
        with self.assertRaises(RuntimeError):
            with source_operation(retain='preview'):
                browser.finish_source(browser.session);raise RuntimeError()
        window.destroy.assert_called_once();self.assertFalse(browser.handoffs)
    def test_partial_resume_requires_same_source_hash_and_format(self):
        info=dict(self.info(),url='https://cdn.example/master.m3u8?sig=private')
        checkpoint=source_checkpoint(info)
        self.assertNotIn('private',json.dumps(checkpoint))
        self.assertTrue(can_resume_embedded(checkpoint,info))
        self.assertFalse(can_resume_embedded(checkpoint,dict(info,url='https://cdn.example/master.m3u8?sig=changed')))
        self.assertFalse(can_resume_embedded({},info))


if __name__=='__main__':unittest.main()
