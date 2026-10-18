"""Offline invariants for the shared queue, adaptive control and settings."""
import copy
import io
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from core.queue_manager import DownloadManager
from core.adaptive import AdaptiveConcurrency
from core.bandwidth import BandwidthBudget, BudgetReader, DownloadPaused
from utils.download_settings import normalize_settings, bytes_per_second
from state.app_state import state
import app

OPTIONS = {'format': 'video', 'quality': '720p', 'embed_subs': True}


class AdaptiveTests(unittest.TestCase):
    def test_start_at_two(self):
        self.assertEqual(AdaptiveConcurrency(0).limit, 2)

    def test_probe_and_keep_measured_gain(self):
        control = AdaptiveConcurrency(0)
        self.assertEqual(control.sample(10, 10000, 2, 8, 20, False), 3)
        self.assertEqual(control.sample(20, 15000, 3, 7, 20, False), 3)

    def test_probe_reverts_without_gain(self):
        control = AdaptiveConcurrency(0)
        control.sample(10, 10000, 2, 8, 20, False)
        self.assertEqual(control.sample(20, 10100, 3, 7, 20, False), 2)

    def test_cpu_load_reduces_dispatch(self):
        self.assertEqual(AdaptiveConcurrency(0).sample(10, 10000, 2, 8, 90, False), 1)

    def test_conversion_reduces_dispatch(self):
        self.assertEqual(AdaptiveConcurrency(0).sample(10, 10000, 2, 8, 0, True), 1)

    def test_error_reduces_and_cools_down(self):
        control = AdaptiveConcurrency(0)
        control.error(10)
        self.assertEqual(control.sample(20, 10000, 1, 8, 0, False), 1)

    def test_cap_saturation_prevents_probe(self):
        self.assertEqual(AdaptiveConcurrency(0).sample(10, 95000, 2, 8, 0, False, 100000), 2)

    def test_unsaturated_queue_not_used_as_benchmark(self):
        self.assertEqual(AdaptiveConcurrency(0).sample(10, 10000, 1, 0, 0, False), 2)


class SettingTests(unittest.TestCase):
    def test_legacy_migration_defaults_auto(self):
        settings = normalize_settings({'concurrent_downloads': '3', 'speed_limit': '8000'})
        self.assertEqual(settings['concurrency_mode'], 'auto')
        self.assertEqual(bytes_per_second(settings), 1000000)

    def test_mbps_decimal_conversion(self):
        self.assertEqual(bytes_per_second(normalize_settings({'speed_limit_mbps': '1.5'})), 187500)

    def test_invalid_numbers_rejected(self):
        for value in ('-1', 'NaN', 'Infinity', 'abc', '100001', '0.000001'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_settings({'speed_limit_mbps': value})

    def test_worker_limit_validated(self):
        for value in (0, 11, 999, True, '3.5'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_settings({'concurrent_downloads': value})

    def test_mode_validated(self):
        with self.assertRaises(ValueError):
            normalize_settings({'concurrency_mode': 'fastest'})


class BudgetTests(unittest.TestCase):
    def test_zero_means_unlimited(self):
        budget = BandwidthBudget()
        budget.acquire(1000000)

    def test_cancellation_interrupts_wait(self):
        with self.assertRaises(DownloadPaused):
            BandwidthBudget(1).acquire(100, lambda: True)

    def test_read_all_is_complete(self):
        payload = b'abcdef' * 30000
        recorded = []
        reader = BudgetReader(io.BytesIO(payload), BandwidthBudget(), lambda: False, recorded.append)
        self.assertEqual(reader.read(), payload)
        self.assertEqual(sum(recorded), len(payload))

    def test_two_readers_share_one_budget(self):
        budget = BandwidthBudget(100000)
        one = BudgetReader(io.BytesIO(b'a'), budget, lambda: False, lambda _: None)
        two = BudgetReader(io.BytesIO(b'b'), budget, lambda: False, lambda _: None)
        self.assertIs(one.budget, two.budget)

    def test_invalid_budget_rejected(self):
        with self.assertRaises(ValueError):
            BandwidthBudget().configure(-1)


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.saved = copy.deepcopy(state)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.release = threading.Event()
        self.managers = []
        self.notification = patch('core.queue_manager.show_notification')
        self.notification.start()

    def tearDown(self):
        self.release.set()
        for manager in self.managers:
            manager.close()
        self.notification.stop()
        self.temp.cleanup()
        state.clear()
        state.update(self.saved)

    def manager(self, worker):
        manager = DownloadManager(worker)
        self.managers.append(manager)
        return manager

    def wait_for(self, predicate, timeout=4):
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > deadline:
                self.fail('Timed out waiting for scheduler')
            time.sleep(0.01)

    def test_multiple_submissions_share_global_limit(self):
        lock, active, peak = threading.Lock(), [0], [0]
        def worker(*_):
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            self.release.wait(4)
            with lock:
                active[0] -= 1
            return True
        manager = self.manager(worker)
        manager.configure('manual', 2, 0)
        manager.submit(['https://x/a', 'https://x/b'], OPTIONS, self.temp.name)
        self.wait_for(lambda: active[0] == 2)
        manager.submit(['https://x/c', 'https://x/d'], OPTIONS, self.temp.name)
        self.assertEqual(len(manager.snapshot()['items']), 4)
        self.release.set()
        manager.wait(5)
        self.assertEqual(peak[0], 2)

    def test_pause_queued_job_and_resume_original_options(self):
        seen = []
        def worker(url, opts, path, request, *_):
            seen.append((url, request.copy(), path))
            if url.endswith('/a'):
                self.release.wait(4)
            return True
        manager = self.manager(worker)
        manager.configure('manual', 1, 125000)
        manager.submit(['https://x/a', 'https://x/b'], OPTIONS, self.temp.name)
        self.wait_for(lambda: len(seen) == 1)
        manager.pause('https://x/b')
        self.release.set()
        self.wait_for(lambda: manager.snapshot()['status'] == 'paused')
        manager.resume('https://x/b')
        manager.wait(5)
        self.assertEqual(seen[1][1]['quality'], '720p')
        self.assertTrue(seen[1][1]['embed_subs'])
        self.assertEqual(seen[1][1]['_budget'].rate, 125000)
        self.assertEqual(seen[1][2], seen[0][2])

    def test_failed_worker_not_success(self):
        manager = self.manager(lambda *_: False)
        manager.submit(['https://x/a'], OPTIONS, self.temp.name)
        self.assertEqual(manager.wait(5)['status'], 'error')

    def test_exception_is_not_ignored(self):
        def worker(*_):
            raise RuntimeError('requested format missing')
        manager = self.manager(worker)
        manager.submit(['https://x/a'], OPTIONS, self.temp.name)
        self.assertIn('requested format missing', manager.wait(5)['error'])

    def test_resume_waits_for_old_worker(self):
        def worker(*_):
            self.release.wait(4)
            return False
        manager = self.manager(worker)
        manager.submit(['https://x/a'], OPTIONS, self.temp.name)
        self.wait_for(lambda: manager.jobs[0].future is not None)
        manager.pause('https://x/a')
        with self.assertRaises(ValueError):
            manager.resume('https://x/a')

    def test_retry_keeps_failed_row(self):
        calls = []
        def worker(*_):
            calls.append(1)
            return len(calls) > 1
        manager = self.manager(worker)
        manager.submit(['https://x/a'], OPTIONS, self.temp.name)
        first = manager.wait(5)['items'][0]['id']
        manager.resume('https://x/a')
        result = manager.wait(5)
        self.assertEqual(result['status'], 'finished_all')
        self.assertEqual(result['items'][0]['id'], first)

    def test_live_budget_reconfiguration(self):
        manager = self.manager(lambda *_: True)
        budget = manager.budget
        manager.configure('auto', 3, 125000)
        manager.configure('manual', 1, 250000)
        self.assertIs(manager.budget, budget)
        self.assertEqual(budget.rate, 250000)

    def test_nested_postprocessor_hooks_do_not_deadlock(self):
        def worker(url, opts, *_):
            callback = opts['postprocessor_hooks'][0]
            callback({'status': 'started'})
            callback({'status': 'started'})
            callback({'status': 'finished'})
            callback({'status': 'finished'})
            return True
        manager = self.manager(worker)
        manager.submit(['https://x/a'], OPTIONS, self.temp.name)
        self.assertEqual(manager.wait(5)['status'], 'finished_all')

    def test_all_submitted_playlists_are_expanded(self):
        seen = []
        manager = self.manager(lambda url, opts, path, *_: seen.append((url, path)) or True)
        def info(url, download=False):
            prefix = 'a' if url.endswith('/a') else 'b'
            return {'title': 'List: ' + prefix, 'entries': [
                {'url': f'https://media/{prefix}/1', 'title': 'one'},
                {'url': f'https://media/{prefix}/2', 'title': 'two'}]}
        with patch('yt_dlp.YoutubeDL') as ydl:
            ydl.return_value.__enter__.return_value.extract_info.side_effect = info
            manager.submit(['https://list/a', 'https://list/b'], OPTIONS, self.temp.name, playlist=True)
            result = manager.wait(5)
        self.assertEqual(result['status'], 'finished_all')
        self.assertEqual(result['total_items'], 4)
        self.assertEqual(len(seen), 4)
        self.assertTrue(all(':' not in Path(path).name for _, path in seen))

    def test_enabling_cap_rejects_active_external_protocol(self):
        ready = threading.Event()
        def worker(url, opts, path, request, *_):
            request['_protocol_support'](False)
            ready.set()
            self.release.wait(4)
            return True
        manager = self.manager(worker)
        manager.submit(['https://x/a'], OPTIONS, self.temp.name)
        self.assertTrue(ready.wait(3))
        with self.assertRaises(ValueError):
            manager.configure('auto', 3, 10000)
        self.assertEqual(manager.budget.rate, 0)


class QueueRouteTests(unittest.TestCase):
    def test_invalid_settings_rejected_before_write(self):
        with patch.object(app, 'save_settings_to_file') as save:
            response = app.app.test_client().post('/save-settings', json={'concurrent_downloads': 999})
            self.assertEqual(response.status_code, 400)
            save.assert_not_called()

    def test_resume_only_needs_url(self):
        with patch.object(app.download_manager, 'resume') as resume:
            response = app.app.test_client().post('/resume', json={'url': 'https://x/a'})
            self.assertEqual(response.status_code, 200)
            resume.assert_called_once_with('https://x/a')


if __name__ == '__main__':
    unittest.main()
