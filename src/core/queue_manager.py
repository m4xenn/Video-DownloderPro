"""A single scheduler for all submissions, retries, fragments and conversions."""
import copy
from dataclasses import dataclass, field, fields
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import threading
import time
import uuid

import psutil
from core.adaptive import AdaptiveConcurrency
from core.bandwidth import BandwidthBudget, DownloadPaused
from core.format_resolver import get_ydl_opts
from core.downloader import _download_single, progress_hook
from services.notification_service import show_notification
from state.app_state import state, state_actions
from utils.formatters import clean_ansi
from services.download_store import media_key, completion_record
from services.media_catalog import estimate_size
from core.retry_policy import transient_error, retry_delay


@dataclass
class Job:
    url: str
    options: dict
    path: str
    bin_dir: str
    playlist: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = 'Video'
    thumbnail: str = ''
    status: str = 'queued'
    percent: float = 0
    speed: str = 'Sırada...'
    error: str = ''
    future: object = None
    native: bool = True
    media_key: str = ''
    total_bytes: int = None
    downloaded_bytes: int = 0
    duration: float = None
    eta: float = None
    size_estimated: bool = True
    output_path: str = ''
    output_template: str = ''
    retry_count: int = 0
    retry_at: float = 0
    restored: bool = False


class DownloadManager:
    def __init__(self, worker=None, clock=time.monotonic, store=None):
        self.lock = threading.RLock()
        self.clock = clock
        self.worker = worker
        self.jobs = []
        self.mode, self.manual = 'auto', 3
        self.controller = AdaptiveConcurrency(clock())
        self.budget = BandwidthBudget()
        self.samples = []
        self.speed = 0
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix='media')
        self.thread = None
        self.closed = threading.Event()
        self.conversion_slot = threading.Semaphore(1)
        self.notified = False
        self.store = store
        self.restored = False
        self.storage_error = ''
        self.pending_history = []
        self.last_checkpoint = 0

    def restore(self):
        with self.lock:
            if self.restored:
                return
            records = self.store.load_queue() if self.store else []
            if not isinstance(records, list):
                raise ValueError('Kuyruk kayıt biçimi geçersiz.')
            recovered = []
            allowed = {item.name for item in fields(Job)} - {'future', 'retry_at'}
            for record in records:
                if not isinstance(record, dict) or not isinstance(record.get('url'), str):
                    continue
                job = Job(**{key: value for key, value in record.items() if key in allowed})
                if job.status in ('finished','expanded'):
                    continue
                if job.status in ('queued', 'starting', 'downloading', 'converting', 'pausing', 'retry_wait', 'paused'):
                    job.status, job.speed, job.restored = 'paused', 'Önceki oturumdan geri yüklendi', True
                job.retry_at = 0
                job.future = None
                recovered.append(job)
                state_actions.set_cancel_flag(job.url, job.status == 'paused')
            self.jobs = recovered
            self.restored = True
            self._publish()
            if recovered:
                self._start_scheduler()

    def _start_scheduler(self):
        if self.thread is None and not self.closed.is_set():
            self.thread = threading.Thread(target=self._loop, daemon=True, name='download-scheduler')
            self.thread.start()

    def _records(self):
        names = {item.name for item in fields(Job)} - {'future', 'retry_at'}
        return [{name: copy.deepcopy(getattr(job, name)) for name in names} for job in self.jobs]

    def _persist(self, required=False, clear_drafts=()):
        if not self.store:
            return
        try:
            self.store.commit_queue(self._records(), self.pending_history, clear_drafts)
            self.pending_history.clear()
            self.storage_error = ''
            self.last_checkpoint = self.clock()
        except Exception as exc:
            self.storage_error = 'Kuyruk/geçmiş kaydedilemedi: ' + str(exc)
            if required:
                raise ValueError(self.storage_error)

    def _finished(self, job):
        job.status, job.percent, job.speed = 'finished', 100, 'Tamamlandı'
        job.error, job.eta, job.restored = '', 0, False
        if self.store and job.output_path and Path(job.output_path).is_file():
            self.pending_history.append(completion_record(job))

    def _failed(self, job, message, now):
        job.error = message or 'İndirme tamamlanamadı.'
        job.eta = None
        if transient_error(job.error) and job.retry_count < 2 and not self.closed.is_set():
            job.retry_count += 1
            job.retry_at = now + retry_delay(job.retry_count)
            job.status = 'retry_wait'
            job.speed = 'Otomatik yeniden deneme bekleniyor...'
        else:
            job.status = 'error'
        self.controller.error(now)

    def check_configuration(self, mode='auto', manual=3, rate=0):
        if mode not in ('auto', 'manual') or isinstance(manual, bool) or not 1 <= int(manual) <= 10:
            raise ValueError('Geçersiz eşzamanlılık ayarı.')
        if not isinstance(rate, int) or isinstance(rate, bool) or rate < 0:
            raise ValueError('Geçersiz toplam hız sınırı.')
        with self.lock:
            if rate and any(j.future is not None and not j.native for j in self.jobs):
                raise ValueError('Bu yayın türünde hız sınırı uygulanamaz. Aktif yayının bitmesini bekleyin.')

    def configure(self, mode='auto', manual=3, rate=0):
        self.check_configuration(mode, manual, rate)
        with self.lock:
            if mode != self.mode:
                self.controller = AdaptiveConcurrency(self.clock())
            self.mode, self.manual = mode, int(manual)
            self.budget.configure(rate)
            self._publish()

    @property
    def limit(self):
        return self.manual if self.mode == 'manual' else self.controller.limit

    def busy(self):
        with self.lock:
            return any(j.status in ('queued', 'starting', 'downloading', 'converting', 'pausing', 'retry_wait') or j.future is not None for j in self.jobs)

    def submit(self, urls, options, path, bin_dir='', playlist=False):
        if not isinstance(urls, list) or not urls:
            raise ValueError('Kuyruk boş olamaz.')
        target = str(Path(path) / 'Toplu_Indirmeler') if len(urls) > 1 and not playlist else path
        specs = [{'url': url, 'path': target, 'playlist': playlist} for url in urls]
        self.submit_specs(specs, options, bin_dir)

    def submit_specs(self, specs, options, bin_dir='', draft_urls=None):
        with self.lock:
            if self.closed.is_set():
                raise ValueError('İndirme yöneticisi kapalı.')
            if not specs:
                raise ValueError('İndirilecek öğe kalmadı.')
            original = self.jobs[:]
            if not self.busy() and not any(j.status == 'paused' for j in self.jobs):
                self.jobs = []
                self.samples.clear()
                self.controller = AdaptiveConcurrency(self.clock())
            existing = {j.url for j in self.jobs}
            urls = [entry['url'] for entry in specs]
            if len(set(urls)) != len(urls) or existing.intersection(urls):
                self.jobs = original
                raise ValueError('Bu bağlantı mevcut kuyrukta zaten var.')
            for entry in specs:
                self.jobs.append(Job(entry['url'], copy.deepcopy(options), entry['path'], bin_dir,
                    playlist=entry.get('playlist', False), title=entry.get('title') or 'Video',
                    thumbnail=entry.get('thumbnail') or '', media_key=entry.get('media_key') or media_key(entry['url']),
                    total_bytes=entry.get('total_bytes'), duration=entry.get('duration')))
            try:
                self._persist(required=True, clear_drafts=draft_urls or urls)
            except Exception:
                self.jobs = original
                raise
            for url in urls:
                state_actions.set_cancel_flag(url, False)
            self.notified = False
            self._publish()
            self._start_scheduler()

    def pause(self, url):
        with self.lock:
            job = self._find(url)
            if job.status == 'converting':
                raise ValueError('Dönüştürme sırasında duraklatılamaz.')
            if job.status not in ('queued', 'starting', 'downloading', 'retry_wait'):
                raise ValueError('Bu öğe şu anda duraklatılamaz.')
            state_actions.set_cancel_flag(url, True)
            job.status = 'pausing' if job.future else 'paused'
            job.speed = 'Duraklatılıyor...' if job.future else 'Duraklatıldı'
            self._persist()
            self._publish()

    def resume(self, url):
        with self.lock:
            job = self._find(url)
            if job.future is not None:
                raise ValueError('Önce duraklatma işleminin bitmesini bekleyin.')
            if job.status not in ('paused', 'error'):
                raise ValueError('Bu öğe devam ettirilemez.')
            state_actions.set_cancel_flag(url, False)
            job.status, job.error, job.speed = 'queued', '', 'Sırada...'
            job.retry_count, job.retry_at, job.restored = 0, 0, False
            self.notified = False
            self._persist(required=True)
            self._publish()
            self._start_scheduler()

    def resume_restored(self):
        with self.lock:
            for job in self.jobs:
                if job.restored and job.status == 'paused':
                    self.resume(job.url)

    def remove(self, url):
        with self.lock:
            job = self._find(url)
            if job.future is not None:
                raise ValueError('Önce indirmeyi duraklatın.')
            self.jobs.remove(job)
            state['cancel_flags'].pop(url, None)
            self._persist(required=True)
            self._publish()

    def _find(self, url):
        for job in self.jobs:
            if job.url == url:
                return job
        raise ValueError('Kuyruk öğesi bulunamadı.')

    def record(self, count):
        with self.lock:
            self.samples.append((self.clock(), count))

    def _throughput(self, now):
        self.samples[:] = [(t, n) for t, n in self.samples if now - t <= 10]
        if not self.samples:
            return 0
        return sum(n for _, n in self.samples) / max(1, min(10, now - self.samples[0][0]))

    def _publish(self):
        visible = [j for j in self.jobs if j.status != 'expanded']
        running = any(j.future is not None or j.status in ('queued', 'retry_wait') for j in visible)
        failures = [j for j in visible if j.status == 'error']
        if running:
            status = 'downloading'
        elif any(j.status in ('paused', 'pausing') for j in visible):
            status = 'paused'
        elif failures:
            status = 'error'
        elif visible and all(j.status == 'finished' for j in visible):
            status = 'finished_all'
        else:
            status = 'idle'
        state_actions.update_download_status({
            'status': status, 'error': '; '.join(j.error for j in failures),
            'restored_count': sum(j.restored and j.status == 'paused' for j in visible),
            'storage_error': self.storage_error,
            'total_items': len(visible), 'items': [
                {'id': j.id, 'url': j.url, 'title': j.title, 'thumbnail': j.thumbnail,
                 'percent': j.percent, 'speed': j.speed, 'status': j.status, 'error': j.error,
                 'total_bytes': j.total_bytes, 'downloaded_bytes': j.downloaded_bytes, 'eta': j.eta,
                 'format': j.options.get('format'), 'quality': j.options.get('quality'),
                 'size_estimated': j.size_estimated, 'retry_count': j.retry_count,
                 'retry_in': max(0, round(j.retry_at - self.clock())) if j.status == 'retry_wait' else None}
                for j in visible],
            'concurrency_mode': self.mode, 'concurrency_limit': self.limit,
            'active_count': sum(j.future is not None for j in visible),
            'queued_count': sum(j.status == 'queued' for j in visible),
            'total_speed_bps': round(self.speed) if running else 0, 'speed_limit_bps': self.budget.rate,
        })

    def snapshot(self):
        with self.lock:
            self._publish()
            return copy.deepcopy(state['download_status'])

    def _loop(self):
        while not self.closed.wait(0.2):
            self.tick()

    def tick(self):
        notify = False
        with self.lock:
            if self.closed.is_set():
                return
            now = self.clock()
            dirty = False
            for job in list(self.jobs):
                if job.future is None or not job.future.done():
                    continue
                dirty = True
                try:
                    success = job.future.result()
                    if job.status != 'expanded':
                        if state['cancel_flags'].get(job.url):
                            job.status, job.speed = 'paused', 'Duraklatıldı'
                        elif success:
                            self._finished(job)
                        else:
                            self._failed(job, job.error, now)
                except Exception as exc:
                    if state['cancel_flags'].get(job.url):
                        job.status, job.error = 'paused', ''
                    else:
                        self._failed(job, str(exc), now)
                job.future = None
            for job in self.jobs:
                if job.status == 'retry_wait' and now >= job.retry_at:
                    job.status, job.speed = 'queued', 'Tekrar hazırlanıyor...'
                    dirty = True
            self.speed = self._throughput(now)
            active = sum(j.future is not None for j in self.jobs)
            waiting = [j for j in self.jobs if j.status == 'queued']
            converting = any(j.status == 'converting' for j in self.jobs)
            if self.mode == 'auto':
                self.controller.sample(now, self.speed, active, len(waiting),
                                       psutil.cpu_percent(), converting, self.budget.rate)
            # Existing work is not killed when the limit is reduced; stop dispatching.
            if not converting:
                for job in waiting[:max(0, self.limit - active)]:
                    job.status = 'starting'
                    job.future = self.executor.submit(self._execute, job)
                    dirty = True
            if dirty or self.pending_history or (active and self.clock() - self.last_checkpoint >= 2):
                self._persist()
            self._publish()
            if state['download_status']['status'] == 'finished_all' and not self.notified:
                self.notified = True
                notify = True
        if notify:
            show_notification('Video Downloader Pro', 'Tüm indirmeler tamamlandı.')

    def _expand(self, job):
        from yt_dlp import YoutubeDL
        from core.bandwidth import attach_budget
        options = {'extract_flat': 'in_playlist', 'quiet': True, 'noplaylist': False}
        with YoutubeDL(options) as ydl:
            attach_budget(ydl, self.budget, lambda: bool(state['cancel_flags'].get(job.url)), self.record)
            info = ydl.extract_info(job.url, download=False)
        if not info:
            raise ValueError('Oynatma listesi bilgileri alınamadı.')
        title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', info.get('title') or 'Playlist').rstrip('. ')[:120] or 'Playlist'
        if title.upper().split('.')[0] in {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))}:
            title = '_' + title
        entries = info.get('entries')
        if entries is None:
            job.playlist = False
            return self._execute(job)
        children = []
        known = set()
        for entry in entries:
            if not entry:
                continue
            url = entry.get('webpage_url') or entry.get('url')
            if url and url not in known:
                known.add(url)
                children.append(Job(url, copy.deepcopy(job.options), str(Path(job.path) / title), job.bin_dir,
                                    title=entry.get('title') or 'Video'))
        if not children:
            raise ValueError('Oynatma listesinde indirilebilir öğe bulunamadı.')
        with self.lock:
            if state['cancel_flags'].get(job.url):
                raise DownloadPaused('DOWNLOAD_PAUSED')
            existing = {j.url for j in self.jobs if j is not job}
            self.jobs.extend(child for child in children if child.url not in existing)
            job.status = 'expanded'
            self._persist()
        return True

    def _execute(self, job):
        if job.playlist:
            return self._expand(job)
        Path(job.path).mkdir(parents=True, exist_ok=True)
        conversion_held = [False]
        conversion_depth = [0]
        def hook(data):
            if state['cancel_flags'].get(job.url):
                raise DownloadPaused('DOWNLOAD_PAUSED')
            data.setdefault('info_dict', {})['webpage_url'] = job.url
            with self.lock:
                if job.status != 'pausing':
                    job.status = 'converting' if data['status'] == 'finished' else 'downloading'
                total = data.get('total_bytes') or data.get('total_bytes_estimate')
                if total:
                    job.percent = min(100, round(data.get('downloaded_bytes', 0) * 100 / total, 1))
                job.downloaded_bytes = data.get('downloaded_bytes', job.downloaded_bytes)
                job.total_bytes = total or job.total_bytes
                job.size_estimated = not bool(data.get('total_bytes'))
                job.eta = data.get('eta') if data['status'] == 'downloading' else None
                job.speed = clean_ansi(data.get('_speed_str') or job.speed)
                job.title = data['info_dict'].get('title') or job.title
                job.thumbnail = data['info_dict'].get('thumbnail') or job.thumbnail
                # The scheduler publishes at 5 Hz, rather than copying the full
                # queue on every fragment/network block callback.
        def postprocess(data):
            if data['status'] == 'started':
                conversion_depth[0] += 1
                if conversion_depth[0] > 1:
                    return
                with self.lock:
                    job.status, job.speed = 'converting', 'İşleniyor...'
                while not self.conversion_slot.acquire(timeout=0.1):
                    if state['cancel_flags'].get(job.url):
                        raise DownloadPaused('DOWNLOAD_PAUSED')
                conversion_held[0] = True
            elif data['status'] == 'finished':
                conversion_depth[0] = max(0, conversion_depth[0] - 1)
                if conversion_depth[0] == 0 and conversion_held[0]:
                    self.conversion_slot.release()
                    conversion_held[0] = False
        opts = get_ydl_opts(job.options['format'], job.options['quality'], job.path, 0,
                            job.options.get('embed_subs', False), hook, job.bin_dir)
        # Native fragments use the shared response budget, never independent rate caps.
        opts.update(outtmpl=job.output_template or str(Path(job.path) / '%(title)s [%(id)s].%(ext)s'),
                    ignoreerrors=False, hls_prefer_native=True, external_downloader=None,
                    concurrent_fragment_downloads=3, postprocessor_hooks=[postprocess],
                    socket_timeout=15, retries=3, fragment_retries=3)
        def protocol_support(native):
            with self.lock:
                job.native = native
                if not native and self.budget.rate:
                    raise ValueError('Bu yayın türü toplam hız sınırını desteklemiyor. Sınırı kaldırarak tekrar deneyin.')
        def metadata(info):
            with self.lock:
                job.title = info.get('title') or job.title
                job.thumbnail = info.get('thumbnail') or job.thumbnail
                job.media_key = media_key(job.url, info)
                job.total_bytes = estimate_size(info) or job.total_bytes
                job.duration = info.get('duration') or job.duration
        def completed(path):
            with self.lock:
                job.output_path = path
                job.downloaded_bytes = Path(path).stat().st_size
                job.total_bytes, job.size_estimated, job.eta = job.downloaded_bytes, False, 0
        def thumbnail(path):
            with self.lock:
                job.thumbnail=path
        request = dict(job.options, _budget=self.budget, _record=self.record,
                       _error=lambda message: setattr(job, 'error', message),
                       _protocol_support=protocol_support, _metadata=metadata, _completed=completed,
                       _thumbnail=thumbnail, _preview_id=job.id,
                       _preview_dir=str(self.store.path.parent/'previews') if self.store else None,
                       _resume_target=bool(job.output_template),
                       _target=lambda template: setattr(job, 'output_template', template))
        try:
            return (self.worker or _download_single)(job.url, opts, job.path, request, None)
        finally:
            if conversion_held[0]:
                self.conversion_slot.release()

    def wait(self, timeout=60):
        deadline = self.clock() + timeout
        while self.busy():
            if self.clock() > deadline:
                raise TimeoutError('İndirme kuyruğu zaman aşımı.')
            time.sleep(0.02)
        return self.snapshot()

    def close(self):
        self.closed.set()
        with self.lock:
            for job in self.jobs:
                if job.future is not None:
                    state_actions.set_cancel_flag(job.url, True)
        self.executor.shutdown(wait=True, cancel_futures=True)
        with self.lock:
            for job in self.jobs:
                if job.future is not None:
                    try:
                        success = job.future.result() if job.future.done() and not job.future.cancelled() else False
                    except Exception:
                        success = False
                    if success and job.output_path and Path(job.output_path).is_file():
                        self._finished(job)
                    elif job.status != 'expanded':
                        job.status, job.speed = 'paused', 'Duraklatıldı'
                    job.future = None
            self._persist()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=2)


def run_download(urls, format_type, quality, save_path, is_playlist, speed_limit=0,
                 embed_subs=False, concurrent=3, bin_dir=''):
    """Synchronous compatibility helper for standalone smoke tests, not HTTP requests."""
    manager = DownloadManager()
    try:
        manager.configure('manual', int(concurrent), int(speed_limit or 0))
        manager.submit(urls, {'format': format_type, 'quality': quality, 'embed_subs': embed_subs},
                       save_path, bin_dir, is_playlist)
        manager.wait()
    except Exception as exc:
        state_actions.update_download_status({'status': 'error', 'error': str(exc)})
    finally:
        manager.close()
