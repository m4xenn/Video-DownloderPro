"""Real HLS download through the site adapter, with synthetic local media only."""
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from core.queue_manager import DownloadManager
from services.site_resolver import site_resolver

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class SiteLocalDownloadTests(unittest.TestCase):
    def test_selected_quality_reaches_real_output(self):
        bin_dir=Path(os.environ['APPDATA'])/'YoutubePro/bin'
        if not (bin_dir/'ffmpeg.exe').is_file():self.skipTest('FFmpeg required')
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            base=Path(temporary);source=base/'source';source.mkdir();output=base/'output';output.mkdir()
            for height,width in [(180,320),(360,640)]:
                subprocess.run([str(bin_dir/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-f','lavfi','-i',f'testsrc2=s={width}x{height}:r=10','-f','lavfi','-i','sine=frequency=440','-t','2','-c:v','libx264','-preset','ultrafast','-g','10','-c:a','aac','-hls_time','1','-hls_playlist_type','vod',str(source/f'{height}.m3u8')],check=True,timeout=30)
            (source/'master.m3u8').write_text('#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=300000,RESOLUTION=320x180,FRAME-RATE=10,CODECS="avc1.42c00b,mp4a.40.2"\n180.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,FRAME-RATE=10,CODECS="avc1.42c01e,mp4a.40.2"\n360.m3u8\n')
            for height,width,bandwidth in [(180,320,300000),(360,640,800000)]:
                (source/f'master{height}.m3u8').write_text(f'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={width}x{height},FRAME-RATE=10,CODECS="avc1.42c01e,mp4a.40.2"\n{height}.m3u8\n')
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(source)))
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            stream=f'http://127.0.0.1:{server.server_port}/master.m3u8'
            try:
                with patch.object(site_resolver,'details',return_value={'stream':stream,'streams':[stream.replace('master.m3u8','master360.m3u8'),stream.replace('master.m3u8','master180.m3u8')],'headers':{'Referer':'https://rapidvid.net/'},'title':'Synthetic embedded video','thumbnail':''}) as resolve,patch('core.queue_manager.show_notification'):
                    manager=DownloadManager()
                    try:
                        manager.submit(['https://www.fullhdfilmizlesene.now/film/synthetic/'],{'format':'video','quality':'source:180:10','embed_subs':False},str(output),str(bin_dir))
                        manager.wait()
                        resolve.assert_called_once_with('https://www.fullhdfilmizlesene.now/film/synthetic/',fresh=True)
                        files=list(output.glob('*.mp4'));self.assertEqual(len(files),1)
                        data=json.loads(subprocess.check_output([str(bin_dir/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(files[0])]))
                        self.assertEqual(next(s for s in data['streams'] if s['codec_type']=='video')['height'],180)
                        self.assertTrue(any(s['codec_type']=='audio' for s in data['streams']))
                        manager.submit(['https://www.fullhdfilmizlesene.now/film/synthetic/'],{'format':'video','quality':'max','embed_subs':False},str(output),str(bin_dir))
                        manager.wait()
                        second=next(file for file in output.glob('*.mp4') if file!=files[0])
                        best=json.loads(subprocess.check_output([str(bin_dir/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(second)]))
                        self.assertEqual(next(s for s in best['streams'] if s['codec_type']=='video')['height'],360)

                    finally:manager.close()
            finally:
                server.shutdown();server.server_close();worker.join(timeout=5)
