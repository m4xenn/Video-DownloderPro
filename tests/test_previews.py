"""Cover preference, black-frame fallback, safe delivery and restart behavior."""
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from services import preview_service as previews
from services.download_store import DownloadStore
from core.queue_manager import DownloadManager
import app

def picture(color):
    output=io.BytesIO();Image.new('RGB',(120,180),color).save(output,format='JPEG');return output.getvalue()

class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT);self.folder=Path(self.temp.name)
        self.identity='a'*32
    def tearDown(self): self.temp.cleanup()

    def response(self,color):
        return io.BytesIO(picture(color))

    def test_black_and_broken_images_are_rejected(self):
        self.assertIsNone(previews.useful_image(picture('black')))
        self.assertIsNone(previews.useful_image(b'not an image'))
        self.assertIsNotNone(previews.useful_image(picture('orange')))

    def test_source_cover_is_preferred_over_extraction(self):
        ydl=Mock();ydl.urlopen.return_value=self.response('orange')
        with patch.object(previews,'middle_frame') as frame:
            result=previews.create_preview(ydl,{'thumbnail':'https://example.com/cover.jpg'},'missing.mp4','',self.folder,self.identity)
        self.assertEqual(result,'/previews/'+self.identity+'.jpg');frame.assert_not_called()
        self.assertTrue((self.folder/(self.identity+'.jpg')).is_file())

    def test_black_source_cover_falls_back_to_middle_frame(self):
        ydl=Mock();ydl.urlopen.return_value=self.response('black')
        with patch.object(previews,'middle_frame',return_value=Image.new('RGB',(100,150),'blue')) as frame:
            result=previews.create_preview(ydl,{'thumbnail':'https://example.com/black.jpg'},'video.mp4','bin',self.folder,self.identity)
        self.assertTrue(result);frame.assert_called_once()

    def test_failed_source_cover_uses_another_platform_cover(self):
        ydl=Mock();ydl.urlopen.side_effect=[OSError('expired'),self.response('green')]
        info={'thumbnail':'https://example.com/expired.jpg','thumbnails':[{'url':'https://example.com/cover.jpg','width':500}]}
        with patch.object(previews,'middle_frame') as frame:
            self.assertTrue(previews.create_preview(ydl,info,'video.mp4','bin',self.folder,self.identity))
        frame.assert_not_called()

    def test_audio_does_not_attempt_video_frame(self):
        with patch.object(previews,'middle_frame') as frame:
            self.assertEqual(previews.create_preview(Mock(),{},'audio.mp3','',self.folder,self.identity,False),'')
        frame.assert_not_called()

    def test_dark_middle_tries_nearby_frame(self):
        with patch.object(previews.subprocess,'run',side_effect=[Mock(stdout=picture('black')),Mock(stdout=picture('orange'))]) as command:
            self.assertIsNotNone(previews.middle_frame('video.mp4','bin',4))
            self.assertEqual(command.call_count,2)
            self.assertIn('2.0',command.call_args_list[0].args[0])
            self.assertIn('1.4',command.call_args_list[1].args[0])

    def test_preview_failure_does_not_raise(self):
        with patch.object(previews,'middle_frame',side_effect=OSError('no ffmpeg')):
            self.assertEqual(previews.create_preview(Mock(),{},'video.mp4','',self.folder,self.identity),'')

    def test_preview_route_restricts_names_to_cache(self):
        store=DownloadStore(self.folder/'downloads.sqlite3');directory=self.folder/'previews';directory.mkdir()
        (directory/(self.identity+'.jpg')).write_bytes(picture('orange'))
        with patch.object(app,'download_store',store):
            client=app.app.test_client();response=client.get('/previews/'+self.identity+'.jpg')
            self.assertEqual(response.status_code,200);self.assertEqual(response.mimetype,'image/jpeg');response.close()
            self.assertEqual(client.get('/previews/settings.json').status_code,404)

    def test_finished_jobs_stay_in_history_after_restart(self):
        store=DownloadStore(self.folder/'downloads.sqlite3')
        file=self.folder/'video.mp4';file.write_bytes(b'output')
        record={'id':'saved','media_key':'test:1','url':'https://example.com/a','title':'Saved','thumbnail':'',
                'format':'video','quality':'max','embed_subs':False,'path':str(file),'size':6,'completed_at':'2026-10-18T00:00:00Z'}
        common={'options':{'format':'video','quality':'max','embed_subs':False},'path':str(self.folder),'bin_dir':''}
        store.commit_queue([{**common,'url':'https://example.com/a','status':'finished'},
                            {**common,'url':'https://example.com/b','status':'downloading'},
                            {**common,'url':'https://example.com/c','status':'error'}],[record])
        manager=DownloadManager(store=store)
        try:
            manager.restore();items=manager.snapshot()['items']
            self.assertEqual([item['status'] for item in items],['paused','error'])
            self.assertEqual(store.history()['total'],1)
        finally: manager.close()

    def test_real_middle_frame_skips_black_opening(self):
        bin_dir=Path(os.environ['APPDATA'])/'YoutubePro/bin'
        if not (bin_dir/'ffmpeg.exe').is_file(): self.skipTest('FFmpeg missing')
        video=self.folder/'black-start.mp4'
        subprocess.run([str(bin_dir/'ffmpeg.exe'),'-hide_banner','-loglevel','error',
            '-f','lavfi','-i','color=c=black:s=160x120:r=10:d=1',
            '-f','lavfi','-i','color=c=orange:s=160x120:r=10:d=3',
            '-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]','-c:v','libx264',str(video)],
            check=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        image=previews.middle_frame(video,bin_dir)
        self.assertIsNotNone(image)
        red,green,blue=image.getpixel((image.width//2,image.height//2))
        self.assertGreater(red,150);self.assertGreater(green,70);self.assertLess(blue,40)

if __name__=='__main__': unittest.main()
