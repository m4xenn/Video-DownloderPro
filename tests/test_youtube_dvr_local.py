"""Native FFmpeg consumes parallel, ordered DVR pieces and follows the live edge."""
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import socket
from urllib.parse import urlsplit, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from services.youtube_dvr import DVRHistoryProxy, DVRFragmentError
from services.live_recording import record_live
from core.bandwidth import DownloadPaused


class DVRLocalTests(unittest.TestCase):
    def setUp(self):
        fixture=patch('services.secure_transport.pin_requests_session',side_effect=lambda value:value)
        fixture.start();self.addCleanup(fixture.stop)
    def run_case(self, fail=False, scenario=''):
        tools = Path(os.environ['APPDATA']) / 'YoutubePro/bin'
        if not (tools / 'ffmpeg.exe').is_file():
            self.skipTest('FFmpeg required')
        with tempfile.TemporaryDirectory(dir=ROOT / 'build', prefix='dvr-native-') as directory:
            base = Path(directory)
            from services.windows_sandbox import protect_workspace
            protect_workspace(base)
            subprocess.run([str(tools / 'ffmpeg.exe'), '-v', 'error', '-f', 'lavfi', '-i',
                'testsrc2=s=320x180:r=10', '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '32',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-g', '10', '-c:a', 'aac',
                '-f', 'dash', '-seg_duration', '1', '-use_template', '1', '-use_timeline', '0',
                '-init_seg_name', 'init-stream$RepresentationID$.m4s',
                '-media_seg_name', 'chunk-stream$RepresentationID$-$Number%05d$.m4s',
                str(base / 'source.mpd')], check=True, timeout=30, cwd=base)
            pieces = [sorted(base.glob(f'chunk-stream{i}-*.m4s')) for i in (0, 1)]
            init = [(base / f'init-stream{i}.m4s').read_bytes() for i in (0, 1)]
            started = time.monotonic(); lock = threading.Lock()
            stats = dict(active=0, maximum=0, sequences=[], attempts={}, refreshes=0)
            class Handler(http.server.BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass
                def respond(self, head_only=False):
                    path = urlsplit(self.path)
                    index = 0 if path.path.endswith('/v') else 1
                    if scenario == 'origin_headers' and self.headers.get('Origin') != 'https://source.example':
                        self.send_error(403); return
                    count = 20 if scenario == 'ended' else min(len(pieces[index]), 20 + int(time.monotonic() - started))
                    if scenario == 'expire_head' and not path.path.startswith('/new/') and time.monotonic()-started > 2:
                        self.send_error(403); return
                    if head_only:
                        self.send_response(200); self.send_header('X-Head-Seqnum', str(count - 1))
                        self.end_headers(); return
                    sequence = int(parse_qs(path.query)['sq'][0])
                    key = (index, sequence)
                    with lock:
                        stats['attempts'][key] = stats['attempts'].get(key, 0) + 1
                        first = stats['attempts'][key] == 1
                    if sequence >= count or fail and index == 0 and sequence == 12:
                        self.send_error(404); return
                    if index == 0 and sequence == 12 and first:
                        if scenario in ('transient_503', 'rate_limit'):
                            self.send_response(503 if scenario == 'transient_503' else 429)
                            self.send_header('Retry-After', '1'); self.end_headers(); return
                        if scenario == 'disconnect':
                            self.connection.shutdown(socket.SHUT_RDWR); self.connection.close(); return
                    with lock:
                        stats['active'] += 1
                        stats['maximum'] = max(stats['maximum'], stats['active'])
                        stats['sequences'].append((index, sequence))
                    try:
                        time.sleep(.03)
                        if index == 0 and sequence == 12 and first and scenario == 'timeout':time.sleep(3.5)
                        if scenario == 'pause' and sequence >= 12:time.sleep(2)
                        body = init[index] + pieces[index][sequence].read_bytes()
                        self.send_response(200); self.send_header('X-Head-Seqnum', str(count - 1))
                        self.send_header('Content-Length', str(len(body))); self.end_headers()
                        if index == 0 and sequence == 12 and first and scenario == 'truncated':
                            self.wfile.write(body[:len(body)//2]); self.close_connection = True
                        else:self.wfile.write(body)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    finally:
                        with lock:
                            stats['active'] -= 1
                def do_HEAD(self):
                    self.respond(True)
                def do_GET(self):
                    self.respond()
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
            url = f'http://127.0.0.1:{server.server_port}'
            formats = [dict(url=url + '/v', format_id='v', vcodec='h264', acodec='none',
                            protocol='http_dash_segments_generator', ext='mp4', target_duration=1),
                       dict(url=url + '/a', format_id='a', vcodec='none', acodec='aac',
                            protocol='http_dash_segments_generator', ext='m4a', target_duration=1)]
            contexts = [{}, {}]
            if scenario == 'origin_headers':
                contexts = [{'Origin':'https://source.example'} for _ in formats]
                for i, fmt in enumerate(formats):fmt['http_headers'] = dict(contexts[i])
            def refresh():
                stats['refreshes'] += 1
                return [dict(f, url=url+'/new/'+('v' if i == 0 else 'a')) for i,f in enumerate(formats)]
            cancelled = lambda: scenario == 'pause' and time.monotonic()-started > .8
            status = (lambda: time.monotonic()-started < 2) if scenario == 'ended' else None
            router = DVRHistoryProxy(formats, contexts, cancelled=cancelled, refresh=refresh, stream_status=status)
            target = base / 'recording.mp4'; events = []
            def progress(event):
                if event['status'] == 'downloading':
                    events.append((time.monotonic() - started, event['recorded_seconds'], event['recording_phase']))
            try:
                with patch('services.media_discovery.public_url', return_value=True), patch('services.youtube_dvr.END_CHECK_SECONDS', .2 if scenario == 'ended' else 30):
                    router.prepare()
                    info = dict(is_live=True, requested_formats=formats)
                    if fail:
                        with self.assertRaises(DVRFragmentError):
                            record_live(info, target, str(tools), dict(format='video', live_record_minutes=1),
                                        lambda: False, lambda: False, progress, dvr_router=router)
                        self.assertFalse(target.exists())
                        self.assertTrue(target.with_suffix('.live.mkv').exists())
                        return
                    if scenario == 'pause':
                        with self.assertRaises(DownloadPaused):
                            record_live(info, target, str(tools), dict(format='video', live_record_minutes=1),
                                        cancelled, lambda:False, progress, dvr_router=router)
                        self.assertFalse(target.exists())
                        self.assertTrue(target.with_suffix('.live.mkv').exists())
                        self.assertLess(time.monotonic()-started, 10)
                        return
                    result = record_live(info, target, str(tools), dict(format='video', live_record_minutes=1),
                        lambda: False, lambda: scenario != 'ended' and time.monotonic() - started > 6, progress, dvr_router=router)
                self.assertTrue(any(wall < (5.5 if scenario == 'timeout' else 4.5 if scenario else 3) and duration >= 18 for wall, duration, _ in events), events)
                self.assertIn('catchup', [event[2] for event in events])
                self.assertIn('live', [event[2] for event in events])
                self.assertGreater(result['recorded_seconds'], 18 if scenario == 'ended' else 22)
                if scenario == 'ended':self.assertLess(time.monotonic()-started, 10)
                if scenario == 'expire_head':self.assertEqual(stats['refreshes'], 1)
                if scenario in ('transient_503','truncated','disconnect','rate_limit','timeout'):
                    self.assertEqual(stats['attempts'][(0,12)], 2)
                self.assertGreater(stats['maximum'], 1)
                # A timed-out client's abandoned response can still occupy one
                # fixture server thread until its delayed write sees the reset.
                self.assertLessEqual(stats['maximum'], 4 if scenario == 'timeout' else 3)
                for index in (0, 1):
                    self.assertEqual(min(sq for track, sq in stats['sequences'] if track == index), 0)
                    if scenario != 'ended':self.assertTrue(any(track == index and sq >= 22 for track, sq in stats['sequences']))
                    self.assertLessEqual(len(router.cache[index]), 8)
                streams = json.loads(subprocess.check_output([str(tools / 'ffprobe.exe'), '-v', 'error',
                    '-show_streams', '-of', 'json', str(target)]))['streams']
                self.assertEqual({s['codec_type'] for s in streams}, {'video', 'audio'})
                self.assertLess(abs(float(streams[0]['duration']) - float(streams[1]['duration'])), .4)
                subprocess.run([str(tools / 'ffmpeg.exe'), '-v', 'error', '-xerror', '-i', str(target),
                                '-f', 'null', '-'], check=True, capture_output=True, timeout=20)
            finally:
                router.close(); server.shutdown(); server.server_close(); worker.join(3)

    def test_parallel_history_then_live_in_one_synchronized_file(self):
        self.run_case()

    def test_missing_old_fragment_preserves_partial_instead_of_skipping_to_live(self):
        self.run_case(True)

    def test_transient_503_retries_same_fragment_without_gap(self):self.run_case(scenario='transient_503')
    def test_truncated_response_retries_complete_fragment(self):self.run_case(scenario='truncated')
    def test_connection_reset_retries_without_skipping(self):self.run_case(scenario='disconnect')
    def test_rate_limit_waits_then_recovers(self):self.run_case(scenario='rate_limit')
    def test_head_expiry_renews_live_source(self):self.run_case(scenario='expire_head')
    def test_pause_during_pending_download_preserves_recoverable_file(self):self.run_case(scenario='pause')
    def test_confirmed_broadcast_end_finishes_without_waiting_for_cap(self):self.run_case(scenario='ended')
    def test_source_origin_header_is_not_sent_to_loopback_browser_guard(self):self.run_case(scenario='origin_headers')
    def test_socket_read_timeout_recovers_the_same_piece(self):self.run_case(scenario='timeout')


if __name__ == '__main__':
    unittest.main()
