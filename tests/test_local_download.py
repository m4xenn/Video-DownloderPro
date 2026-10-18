"""Real yt-dlp/FFmpeg smoke test using generated media on localhost only."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from core import queue_manager
from state.app_state import state
from services.download_store import DownloadStore, media_key
from services.preview_service import create_preview
from PIL import Image
from yt_dlp import YoutubeDL


class LocalDownloadTests(unittest.TestCase):
    def test_real_mp4_and_mp3_download(self):
        bin_dir = Path(os.environ['APPDATA']) / 'YoutubePro' / 'bin'
        if not all((bin_dir / name).exists() for name in ('ffmpeg.exe', 'ffprobe.exe')):
            self.skipTest('FFmpeg/FFprobe missing from APPDATA/YoutubePro/bin')
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            base = Path(directory)
            source = base / 'source'
            source.mkdir()
            Image.new('RGB',(120,180),'orange').save(source/'cover.jpg')
            subprocess.run([str(bin_dir / 'ffmpeg.exe'), '-hide_banner', '-loglevel', 'error',
                            '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:r=10',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100',
                            '-t', '2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                            str(source / 'sample.mp4')], check=True, timeout=30)
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(source))
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/sample.mp4'
                with YoutubeDL({'quiet':True}) as ydl:
                    preview=create_preview(ydl,{'thumbnail':f'http://127.0.0.1:{server.server_port}/cover.jpg'},
                        source/'sample.mp4',bin_dir,base/'previews','b'*32)
                    self.assertEqual(preview,'/previews/'+'b'*32+'.jpg')
                for kind, quality, extension in [('video', '720p', 'mp4'), ('audio', 'mp3', 'mp3')]:
                    with self.subTest(format=kind):
                        output = base / kind
                        output.mkdir()
                        store = DownloadStore(base / (kind + '.sqlite3'))
                        with patch.object(queue_manager, 'show_notification'):
                            manager = queue_manager.DownloadManager(store=store)
                            options = {'format':kind, 'quality':quality, 'embed_subs':False}
                            try:
                                manager.submit([url], options, str(output), str(bin_dir))
                                manager.wait()
                                self.assertEqual(store.history()['total'], 1)
                                if kind == 'video':
                                    self.assertTrue(store.history()['items'][0]['thumbnail'].startswith('/previews/'))
                                self.assertEqual(len(store.duplicates(media_key(url), url, options)), 1)
                                manager.submit([url], options, str(output), str(bin_dir))
                                manager.wait()
                                self.assertEqual(store.history()['total'], 2)
                            finally:
                                manager.close()
                            recovered = queue_manager.DownloadManager(store=store)
                            try:
                                recovered.restore()
                                self.assertEqual(recovered.jobs, [])
                                self.assertEqual(store.history()['total'], 2)
                            finally:
                                recovered.close()
                        self.assertEqual(state['download_status']['status'], 'idle')
                        files = list(output.glob(f'*.{extension}'))
                        self.assertEqual(len(files), 2)
                        self.assertTrue(any(' (1).' in item.name for item in files))
                        probe = subprocess.run([str(bin_dir / 'ffprobe.exe'), '-v', 'error',
                                                '-show_streams', '-show_format', '-of', 'json', str(files[0])],
                                               capture_output=True, text=True, check=True, timeout=15)
                        info = json.loads(probe.stdout)
                        self.assertGreater(float(info['format']['duration']), 1)
                        types = {s['codec_type'] for s in info['streams']}
                        self.assertIn('audio', types)
                        if kind == 'video':
                            self.assertIn('video', types)
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
