"""Synthetic HLS failures: retry without silently losing video segments."""
import http.server
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from core.retry_policy import fragment_retry_wait
from core.bandwidth import DownloadPaused
from yt_dlp import YoutubeDL
from yt_dlp.downloader.hls import HlsFD
from yt_dlp.utils import DownloadError


class FragmentRecoveryTests(unittest.TestCase):
    def test_backoff_is_bounded_and_cancellable(self):
        now = [0.]
        wait = fragment_retry_wait(lambda: False,
            sleep=lambda seconds: now.__setitem__(0, now[0] + seconds), clock=lambda: now[0])
        for attempt, expected in [(0, 5), (1, 10), (9, 60)]:
            before = now[0]
            self.assertEqual(wait(attempt), 0)
            self.assertAlmostEqual(now[0] - before, expected)
        with self.assertRaises(DownloadPaused):
            fragment_retry_wait(lambda: True)(0)

    def run_hls(self, permanent):
        attempts = {}
        chunks = {f'/{i}.ts': (bytes([65+i]) * 188 * 10) for i in range(3)}
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                attempts[self.path] = attempts.get(self.path, 0) + 1
                if self.path == '/index.m3u8':
                    data = ('#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXT-X-MEDIA-SEQUENCE:0\n' +
                            ''.join(f'#EXTINF:1,\n{i}.ts\n' for i in range(3)) + '#EXT-X-ENDLIST\n').encode()
                elif self.path == '/1.ts' and (permanent[0] or attempts[self.path] == 1):
                    self.send_response(429); self.end_headers(); return
                else:
                    data = chunks[self.path]
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers(); self.wfile.write(data)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        sleeps = []
        try:
            with tempfile.TemporaryDirectory() as folder, YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                path = Path(folder) / 'video.mp4'
                info = {'url': f'http://127.0.0.1:{server.server_port}/index.m3u8',
                        'ext': 'mp4', 'protocol': 'm3u8_native', 'http_headers': {}}
                params = {'quiet': True, 'noprogress': True, 'concurrent_fragment_downloads': 1,
                          'fragment_retries': 2, 'skip_unavailable_fragments': False,
                          'retry_sleep_functions': {'fragment': lambda n: sleeps.append(n) or 0}}
                if permanent[0]:
                    with self.assertRaises(DownloadError):
                        HlsFD(ydl, params).download(str(path), info)
                    self.assertFalse(path.exists(), 'Failed download must not become a completed file')
                    self.assertEqual(attempts['/1.ts'], 3)
                    permanent[0] = False
                self.assertTrue(HlsFD(ydl, params).download(str(path), info)[0])
                self.assertEqual(path.read_bytes(), b''.join(chunks.values()))
                self.assertTrue(sleeps)
        finally:
            server.shutdown(); server.server_close(); thread.join(5)

    def test_429_recovery_has_every_fragment(self):
        self.run_hls([False])

    def test_exhausted_retries_fail_then_resume_without_gaps(self):
        self.run_hls([True])


if __name__ == '__main__':
    unittest.main()
