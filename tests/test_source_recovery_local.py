"""Real synthetic HLS: first source is forbidden, one refresh permits complete output."""
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
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from core.queue_manager import DownloadManager
from services.site_resolver import site_resolver
from services.generic_resolver import apply_source_context
from yt_dlp import YoutubeDL


class RecoveryLocalTests(unittest.TestCase):
    def test_transport_headers_updated_after_initial_native_request(self):
        observed=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                observed.append(dict(self.headers))
                valid=self.path=='/warmup' or (self.headers.get('User-Agent')=='Browser-UA' and self.headers.get('Referer')=='https://player.example/' and self.headers.get('Cookie')=='session=private')
                self.send_response(200 if valid else 403);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'ok')
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        origin=f'http://127.0.0.1:{server.server_port}'
        try:
            with YoutubeDL({'quiet':True,'http_headers':{'User-Agent':'Old-UA'}}) as ydl:
                with ydl.urlopen(origin+'/warmup') as response:self.assertEqual(response.read(),b'ok')
                apply_source_context(ydl,origin+'/media',{'User-Agent':'Browser-UA','Referer':'https://player.example/','Cookie':'session=private'})
                with ydl.urlopen(origin+'/media') as response:self.assertEqual(response.read(),b'ok')
            self.assertEqual(observed[0]['User-Agent'],'Old-UA');self.assertEqual(observed[1]['User-Agent'],'Browser-UA')
        finally:server.shutdown();server.server_close();thread.join(5)
    def test_first_fragment_403_refreshes_once_without_losing_media(self):
        binary=Path(os.environ['APPDATA'])/'YoutubePro/bin'
        if not (binary/'ffmpeg.exe').is_file():self.skipTest('FFmpeg required')
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            base=Path(folder);source=base/'source';source.mkdir();out=base/'out';out.mkdir()
            subprocess.run([str(binary/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=s=320x180:r=10',
                '-f','lavfi','-i','sine=frequency=440','-t','2','-c:v','libx264','-preset','ultrafast','-g','10','-c:a','aac',
                '-hls_time','1','-hls_playlist_type','vod',str(source/'media.m3u8')],check=True,timeout=30)
            allowed=[False];blocked=[];calls=[]
            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
                def do_GET(self):
                    if self.path.split('?')[0].endswith('.ts') and not allowed[0]:
                        blocked.append(self.path);self.send_response(403);self.end_headers();return
                    super().do_GET()
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(source)))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            stream=f'http://127.0.0.1:{server.server_port}/media.m3u8'
            def details(url,fresh=False):
                calls.append(url)
                if len(calls)==2:allowed[0]=True
                return {'stream':stream,'headers':{},'title':'Recovery fixture','thumbnail':''}
            manager=DownloadManager()
            try:
                with patch.object(site_resolver,'details',side_effect=details),patch('core.queue_manager.show_notification'):
                    manager.submit(['https://www.fullhdfilmizlesene.now/film/recovery-fixture/'],
                        {'format':'video','quality':'max','embed_subs':False},str(out),str(binary))
                    result=manager.wait(20)
                    self.assertEqual(result['status'],'finished_all',result.get('error'))
                    self.assertEqual(len(calls),2);self.assertTrue(blocked)
                    files=list(out.glob('*.mp4'));self.assertEqual(len(files),1)
                    info=json.loads(subprocess.check_output([str(binary/'ffprobe.exe'),'-v','error','-show_format','-show_streams','-of','json',str(files[0])]))
                    self.assertGreaterEqual(float(info['format']['duration']),2)
                    self.assertTrue(any(s['codec_type']=='audio' for s in info['streams']))
                    self.assertEqual(next(s['height'] for s in info['streams'] if s['codec_type']=='video'),180)
            finally:
                manager.close();server.shutdown();server.server_close();thread.join(5)


if __name__=='__main__':unittest.main()
