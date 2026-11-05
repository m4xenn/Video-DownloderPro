import struct
import sys
import unittest
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from services.youtube_dvr import (DVRHistoryProxy, DVRUnavailable, _SourceError,
                                  _mp4_fragment, prepare_youtube_dvr)
from core.bandwidth import DownloadPaused


def fragment():
    return b''.join(struct.pack('>I', 9) + name + b'x'
                    for name in (b'ftyp', b'moov', b'moof', b'mdat'))


def formats():
    return [dict(format_id='v', url='https://cdn.example/v', protocol='http_dash_segments_generator',
                 ext='mp4', vcodec='h264', acodec='none', height=360, target_duration=5),
            dict(format_id='a', url='https://cdn.example/a', protocol='http_dash_segments_generator',
                 ext='m4a', vcodec='none', acodec='aac', target_duration=5)]


class FakeYDL:
    def __init__(self):
        self.params = {'format': 'bestvideo[height=360]+bestaudio[language=fr]'}
        self.format_selector = object()
        self.candidate = dict(id='video', is_live=True, extractor_key='Youtube', requested_formats=formats())
    def build_format_selector(self, expression):
        self.expression = expression
        return expression
    def extract_info(self, url, download):
        assert self.params['live_from_start'] is True
        return self.candidate


class DVRTests(unittest.TestCase):
    def test_complete_initialized_fragments_only(self):
        self.assertTrue(_mp4_fragment(bytearray(fragment())))
        for value in (b'', fragment()[:-1], struct.pack('>I', 8) + b'mdat', b'not media'):
            self.assertFalse(_mp4_fragment(value))

    def test_from_start_selection_preserves_language_quality_and_restores_selector(self):
        ydl = FakeYDL(); selector = ydl.format_selector; original = dict(ydl.params)
        with patch.object(DVRHistoryProxy, 'prepare'):
            info, proxy = prepare_youtube_dvr(ydl, ydl.candidate, 'https://youtube.com/watch?v=video')
        try:
            self.assertIs(info, ydl.candidate)
            self.assertIsNotNone(proxy)
            self.assertIn('[language=fr]', ydl.expression)
            self.assertIn('[height=360]', ydl.expression)
            self.assertIn('[protocol=http_dash_segments_generator]', ydl.expression)
            self.assertEqual(ydl.params, original)
            self.assertIs(ydl.format_selector, selector)
        finally:
            proxy.close()

    def test_other_sites_never_enter_youtube_dvr(self):
        ydl = FakeYDL(); info = dict(is_live=True, extractor_key='EmbeddedMedia')
        with patch.object(ydl, 'extract_info') as extract:
            self.assertEqual(prepare_youtube_dvr(ydl, info, 'https://example.com'), (info, None))
        extract.assert_not_called()

    def test_identity_or_quality_change_is_not_accepted(self):
        for change in ('identity', 'quality'):
            ydl = FakeYDL(); original = dict(ydl.candidate, requested_formats=formats())
            if change == 'identity':
                ydl.candidate['id'] = 'other'
            else:
                ydl.candidate['requested_formats'][0]['height'] = 240
            with patch.object(DVRHistoryProxy, 'prepare') as prepare:
                self.assertEqual(prepare_youtube_dvr(ydl, original, 'https://youtube.com'), (original, None))
            prepare.assert_not_called()

    def test_expired_beginning_falls_back_before_output_not_after_a_gap(self):
        ydl = FakeYDL()
        with patch.object(DVRHistoryProxy, 'prepare', side_effect=_SourceError(404)):
            self.assertEqual(prepare_youtube_dvr(ydl, ydl.candidate, 'https://youtube.com'), (ydl.candidate, None))

    def test_cancellation_is_not_swallowed_as_source_fallback(self):
        ydl = FakeYDL()
        with self.assertRaises(DownloadPaused):
            prepare_youtube_dvr(ydl, ydl.candidate, 'https://youtube.com', lambda: True)

    def test_non_public_media_is_rejected_before_request(self):
        proxy = DVRHistoryProxy(formats(), [{}, {}])
        proxy.local.session = Mock()
        try:
            with patch('services.media_discovery.public_url', return_value=False), patch.object(proxy.stop, 'wait', return_value=False):
                with self.assertRaises(_SourceError):
                    proxy._request(0, 0)
            proxy.local.session.request.assert_not_called()
        finally:
            proxy.close()

    def test_expired_url_refresh_keeps_the_same_fragment_and_track(self):
        refreshed = formats(); refreshed[0]['url'] = 'https://new.example/v'
        proxy = DVRHistoryProxy(formats(), [{}, {}], refresh=Mock(return_value=refreshed))
        try:
            with patch.object(proxy, '_request', side_effect=[_SourceError(403), fragment()]) as request:
                self.assertEqual(proxy._fetch(0, 987), fragment())
            self.assertEqual(request.call_args_list[0].args, (0, 987))
            self.assertEqual(request.call_args_list[1].args, (0, 987))
            proxy.refresh.assert_called_once()
        finally:
            proxy.close()

    def test_refreshed_representation_change_is_rejected(self):
        changed = formats(); changed[0]['format_id'] = 'different'
        proxy = DVRHistoryProxy(formats(), [{}, {}], refresh=lambda: changed)
        try:
            with patch.object(proxy, '_request', side_effect=_SourceError(403)):
                with self.assertRaises(_SourceError):
                    proxy._fetch(0, 123)
        finally:
            proxy.close()

    def test_different_track_segment_durations_are_rejected(self):
        selected = formats(); selected[1]['target_duration'] = 6
        proxy = DVRHistoryProxy(selected, [{}, {}])
        try:
            with self.assertRaises(DVRUnavailable):
                proxy.prepare()
        finally:
            proxy.close()

    def test_expired_head_url_renews_instead_of_failing_live_recording(self):
        import urllib.request
        proxy = DVRHistoryProxy(formats(), [{}, {}], refresh=Mock(return_value=formats()))
        proxy.duration = 5; proxy.heads = [12, 12]
        try:
            with patch.object(proxy, '_request', side_effect=[_SourceError(403), b'']):
                url = proxy.start()[0]
                with urllib.request.urlopen(url, timeout=3) as response:
                    self.assertIn('12.mp4', response.read().decode())
            self.assertFalse(proxy.error)
            proxy.refresh.assert_called_once()
        finally:
            proxy.close()

    def test_contiguous_audio_and_video_delivery_controls_backlog(self):
        proxy = DVRHistoryProxy(formats(), [{}, {}]); proxy.duration = 5; proxy.heads = [1000, 1000]
        try:
            proxy._delivered(0, 1)  # Out-of-order response must not fill a missing beginning.
            self.assertEqual(proxy.remaining_seconds(), 5005)
            proxy._delivered(0, 0)
            proxy._delivered(1, 0)
            self.assertEqual(proxy.remaining_seconds(), 5000)
            for i in (0, 1):
                for sequence in range(1, 999):proxy._delivered(i, sequence)
            self.assertEqual(proxy.remaining_seconds(), 10)
            self.assertEqual(proxy.pending_delivery, [set(), set()])
        finally:
            proxy.close()

    def test_stall_or_unknown_status_is_not_mistaken_for_broadcast_end(self):
        proxy = DVRHistoryProxy(formats(), [{}, {}], stream_status=Mock(return_value=None))
        proxy.changed = [0, 0]
        try:
            proxy._maybe_end()
            self.assertFalse(proxy.ended)
            proxy.stream_status.assert_called_once()
        finally:
            proxy.close()

    def test_confirmed_end_refreshes_final_heads_before_freezing_playlist(self):
        proxy = DVRHistoryProxy(formats(), [{}, {}], stream_status=lambda: False)
        proxy.duration = 5; proxy.changed = [0, 0]; proxy.heads = [10, 10]
        def final_head(index, sequence=None):proxy.heads[index] = 12
        try:
            with patch.object(proxy, '_request', side_effect=final_head):proxy._maybe_end()
            self.assertTrue(proxy.ended)
            self.assertEqual(proxy.heads, [12, 12])
        finally:
            proxy.close()

    def test_rate_limit_retry_uses_bounded_server_delay(self):
        proxy = DVRHistoryProxy(formats(), [{}, {}]); session = Mock(); proxy.local.session = session
        response = Mock(); response.status_code = 429; response.headers = {'Retry-After': '2'}
        session.request.return_value.__enter__ = Mock(return_value=response)
        session.request.return_value.__exit__ = Mock(return_value=False)
        try:
            with patch('services.media_discovery.public_url', return_value=True), patch.object(proxy.stop, 'wait', return_value=False) as wait:
                with self.assertRaises(_SourceError):proxy._request(0, 0)
            self.assertEqual(session.request.call_count, 3)
            self.assertEqual([call.args[0] for call in wait.call_args_list], [2, 2])
        finally:
            proxy.close()

    def test_repeated_manifest_threads_do_not_accumulate_http_sessions(self):
        import threading
        proxy = DVRHistoryProxy(formats(), [{}, {}])
        response = MagicMock(status_code=200, headers={'X-Head-Seqnum': '20'})
        response.__enter__.return_value = response
        try:
            with patch('services.media_discovery.public_url', return_value=True), patch('requests.Session.request', return_value=response):
                for _ in range(40):
                    worker = threading.Thread(target=lambda: proxy._request(0))
                    worker.start(); worker.join(2)
                    self.assertFalse(worker.is_alive())
            self.assertLessEqual(len(proxy.sessions), 2)
        finally:
            proxy.close()


if __name__ == '__main__':
    unittest.main()
