"""A single scheduler for all submissions, retries, fragments and conversions."""
import copy
from dataclasses import dataclass, field, fields
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import threading
import time
import uuid
from collections import deque

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
from core.retry_policy import transient_error, retry_delay, fragment_retry_wait


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
    error_code: str = ''
    error_phase: str = ''
    source_signature: dict = field(default_factory=dict)
    phase: str = 'finding_player'
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
    is_live: bool = False
    recorded_seconds: float = 0
    recording_speed_bps: float = 0
    recording_pace: float = 0
    recording_phase: str = 'live'
    catchup_remaining_seconds: float = 0
    catchup_available_seconds: float = 0
    catchup_from_start: bool = False
    recording_limit: float = 0
    stop_requested: bool = False
    recovery_reason: str = ''
    security_status: str = ''
    work_path: str = ''
    workflow: dict = field(default_factory=dict)
    publication_intent: dict = field(default_factory=dict)
    quality_summary: dict = field(default_factory=dict)
    recording_parts: list = field(default_factory=list)
    session_exports: dict = field(default_factory=dict)
    recording_action: dict = field(default_factory=dict)


class DownloadManager:
    def __init__(self, worker=None, clock=time.monotonic, store=None):
        self.lock = threading.RLock()
        self.clock = clock
        self.worker = worker
        self.jobs = []
        self.mode, self.manual = 'auto', 3
        self.controller = AdaptiveConcurrency(clock())
        self.budget = BandwidthBudget()
        self.samples = deque()
        self.speed = 0
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix='media')
        self.recording_executor = ThreadPoolExecutor(max_workers=2,thread_name_prefix='recording-recovery')
        self.thread = None
        self.closed = threading.Event()
        self.conversion_slot = threading.Semaphore(1)
        self.notified = False
        self.store = store
        self.restored = False
        self.storage_error = ''
        self.pending_history = []
        self.last_checkpoint = 0
        self.traces = {}
        self.recording_operations = {}

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
                for name in ('workflow','publication_intent','quality_summary','session_exports'):
                    if not isinstance(getattr(job,name),dict):setattr(job,name,{})
                if not isinstance(job.recording_parts,list):job.recording_parts=[]
                job.recording_action={}
                if job.status in ('finished','expanded'):
                    from services.recording_sessions import recoverable_parts
                    if job.status!='finished' or not recoverable_parts(job):continue
                if job.status in ('queued', 'starting', 'downloading', 'converting', 'pausing', 'retry_wait', 'paused'):
                    job.recovery_reason = job.recovery_reason or ('paused' if job.status == 'paused' else 'interrupted')
                    job.status, job.speed, job.restored = 'paused', 'Önceki oturumdan geri yüklendi', True
                from services.publication_recovery import has_saved_target
                if job.status!='finished' and has_saved_target(job):
                    job.recovery_reason='publication'
                    job.status,job.restored='paused',True
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
        job.error_code=job.error_phase=''
        if self.store and job.output_path and Path(job.output_path).is_file():
            self.pending_history.append(completion_record(job))

    def _failed(self, job, message, now):
        job.error = message or 'İndirme tamamlanamadı.'
        from services.diagnostics import diagnostics
        from services.diagnostics import error_code
        job.error_code=error_code(job.error)
        job.error_phase=job.phase
        diagnostics.record('download', job.url, error=job.error)
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
            return any(j.status in ('queued', 'starting', 'downloading', 'converting', 'pausing', 'retry_wait') or j.future is not None for j in self.jobs) or any(op['data']['status'] in ('queued','running') for op in self.recording_operations.values())

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
            original_history=self.pending_history[:]
            if not self.busy() and not any(j.status == 'paused' for j in self.jobs):
                if self.store:
                    from services.recording_sessions import recoverable_parts
                    from services.download_store import recording_archive_record
                    self.pending_history.extend(recording_archive_record(j) for j in self.jobs if recoverable_parts(j))
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
                self.pending_history=original_history
                raise
            for url in urls:
                state_actions.set_cancel_flag(url, False)
            self.notified = False
            self._publish()
            self._start_scheduler()

    def finish_recording(self,url):
        with self.lock:
            job=self._find(url)
            if not job.is_live or job.future is None or job.status not in ('starting','downloading'):
                raise ValueError('No live recording is active for this item.')
            job.stop_requested=True
            self._publish()

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
            if self.closed.is_set():
                raise ValueError('Uygulama kapanıyor. Kaydı tamamlayıp yeniden açın.')
            job = self._find(url)
            if job.recording_action:raise ValueError('Recording recovery is still running.')
            if job.security_status in ('blocked', 'review'):
                from services.media_gate import SecurityReviewError
                raise SecurityReviewError()
            if job.future is not None:
                raise ValueError('Önce duraklatma işleminin bitmesini bekleyin.')
            if job.status not in ('paused', 'error'):
                raise ValueError('Bu öğe devam ettirilemez.')
            previous = copy.deepcopy({name: getattr(job, name) for name in (
                'status', 'error', 'speed', 'retry_count', 'retry_at', 'restored',
                'stop_requested', 'recovery_reason', 'recorded_seconds',
                  'recording_limit', 'recording_speed_bps', 'recording_pace', 'recording_phase', 'catchup_remaining_seconds', 'catchup_available_seconds', 'catchup_from_start', 'percent', 'duration', 'downloaded_bytes', 'total_bytes')})
            previous_cancel = state['cancel_flags'].get(url, False)
            state_actions.set_cancel_flag(url, False)
            job.status, job.error, job.speed = 'queued', '', 'Sırada...'
            job.retry_count, job.retry_at, job.restored = 0, 0, False
            job.stop_requested=False
            job.recovery_reason=''
            if job.is_live and not job.publication_intent:
                job.recording_speed_bps=0;job.recording_pace=0
                job.recording_phase='live';job.catchup_remaining_seconds=0;job.catchup_available_seconds=0;job.catchup_from_start=False
                job.recorded_seconds=0;job.recording_limit=0;job.percent=0;job.duration=None;job.downloaded_bytes=0;job.total_bytes=None
            self.notified = False
            try:
                self._persist(required=True)
            except Exception:
                for name, value in previous.items():
                    setattr(job, name, value)
                state_actions.set_cancel_flag(url, previous_cancel)
                raise
            self._publish()
            self._start_scheduler()

    def resume_restored(self):
        with self.lock:
            for job in self.jobs:
                if job.restored and job.status == 'paused' and not job.is_live:
                    self.resume(job.url)

    def recover(self, url, refresh=False, action=None, destination=None):
        """Re-resolve the original page; never accept a replacement media URL.

        The worker still verifies source identity/validators before appending.
        """
        with self.lock:
            job = self._find(url)
            if self.closed.is_set() or job.future is not None or job.status not in ('paused', 'error'):
                raise ValueError('Öğe henüz kurtarmaya hazır değil.')
            if job.security_status in ('blocked','review'):
                from services.media_gate import SecurityReviewError
                raise SecurityReviewError()
        action=action or ('refresh' if refresh else 'resume')
        if action not in ('resume','refresh','finalize','mkv','folder','max_quality'):raise ValueError('Invalid recovery action.')
        if action=='mkv' and (job.is_live or job.options.get('format')!='video'):raise ValueError('Invalid recovery action.')
        if action=='folder' and (not isinstance(destination,str) or not Path(destination).is_dir()):raise ValueError('Invalid recovery folder.')
        refresh=refresh or action in ('refresh','max_quality')
        if refresh:
            # Never hold the manager lock while acquiring resolver locks: another
            # inspection can report progress back into this manager.
            from services.site_resolver import site_resolver
            from services.generic_resolver import generic_resolver
            for resolver in (site_resolver, generic_resolver):
                with resolver.lock:
                    resolver.cache.pop(url, None)
                    resolver.pages.pop(url, None)
                    if hasattr(resolver, 'jobs'):
                        resolver.jobs.pop(url, None)
        with self.lock:
            if job.future is not None or job.status not in ('paused','error'):raise ValueError('Öğe henüz kurtarmaya hazır değil.')
            previous=copy.deepcopy({name:getattr(job,name) for name in ('options','path','work_path','output_template','publication_intent')})
            if action=='mkv':job.options['video_container']='mkv'
            elif action=='folder':
                job.path=destination;job.work_path='';job.publication_intent={}
            elif action=='max_quality':
                job.options['quality']='max';job.output_template='';job.publication_intent={}
            try:self.resume(url)
            except BaseException:
                for name,value in previous.items():setattr(job,name,value)
                raise

    def remove(self, url):
        with self.lock:
            job = self._find(url)
            if job.recording_action:raise ValueError('Recording recovery is still running.')
            if job.future is not None:
                raise ValueError('Önce indirmeyi duraklatın.')
            previous_jobs=self.jobs[:];previous_history=self.pending_history[:]
            old_cancel=state['cancel_flags'].get(url)
            from services.recording_sessions import recoverable_parts
            if self.store and recoverable_parts(job):
                from services.download_store import recording_archive_record
                self.pending_history.append(recording_archive_record(job))
            self.jobs.remove(job)
            state['cancel_flags'].pop(url, None)
            try:self._persist(required=True)
            except BaseException:
                self.jobs=previous_jobs;self.pending_history=previous_history
                if old_cancel is not None:state['cancel_flags'][url]=old_cancel
                raise
            self._publish()

    def _find(self, url):
        for job in self.jobs:
            if job.url == url:
                return job
        raise ValueError('Kuyruk öğesi bulunamadı.')

    def recover_recording(self, identity, action, bin_dir, acknowledge_gaps=False, history=False, destination=None):
        from services.recording_sessions import recoverable_parts,RecordingPartError
        if action not in ('export','join') or not isinstance(acknowledge_gaps,bool):raise ValueError('Invalid recording recovery action.')
        with self.lock:
            if self.closed.is_set():raise ValueError('Recording recovery is still running.')
            if any(op['data'].get('parent_id')==identity and op['data']['status'] in ('queued','running') for op in self.recording_operations.values()):
                raise ValueError('Recording recovery is still running.')
            if sum(op['data']['status'] in ('queued','running') for op in self.recording_operations.values())>=10:raise ValueError('Recording recovery is still running.')
            parent=next((j for j in self.jobs if j.id==identity),None) if not history else None
            if history:
                if not self.store:raise RecordingPartError()
                record=self.store.get_history(identity);tracks=self.store.history_track_state(identity)
                if not record:raise RecordingPartError()
                parent=Job(record['url'],{k:record[k] for k in ('format','quality','embed_subs','audio_language','subtitle_language','video_container')},str(Path(record['path']).parent),bin_dir,id=identity,title=record['title'],media_key=record['media_key'],status='finished',recording_parts=tracks.get('recording_parts',[]),session_exports=tracks.get('session_exports',{}))
            if not parent or parent.future is not None or parent.recording_action or not recoverable_parts(parent):raise RecordingPartError()
            if action=='join' and not acknowledge_gaps:raise RecordingPartError('recording_ack_required')
            if destination:
                if not Path(destination).is_dir():raise ValueError('Invalid recovery folder.')
            parent.bin_dir=bin_dir
            token=uuid.uuid4().hex
            data={'id':token,'parent_id':identity,'status':'queued','phase':'session_join' if action=='join' else 'session_export','current':0,'total':len(recoverable_parts(parent)),'error_code':'','saved':0}
            parent.recording_action={'id':token,'status':'running'}
            cancel=threading.Event()
            entry={'data':data,'future':None,'cancel':cancel};self.recording_operations[token]=entry
            for old in list(self.recording_operations):
                if len(self.recording_operations)>64 and self.recording_operations[old]['data']['status'] in ('finished','error','cancelled'):self.recording_operations.pop(old)
            def persist():
                if history:self.store.update_history_track_state(identity,{'recording_parts':parent.recording_parts,'session_exports':parent.session_exports})
                self._persist(required=True)
            try:
                persist()
                future=self.recording_executor.submit(self._recover_recording_worker,parent,action,acknowledge_gaps,data,persist,destination,cancel)
                entry['future']=future
            except BaseException:
                parent.recording_action={};self.recording_operations.pop(token,None);raise
            def completed(future):
                from services.diagnostics import error_code
                with self.lock:
                    try:
                        result=future.result();data.update(status='finished',saved=len(result))
                    except DownloadPaused:data.update(status='cancelled',error_code='')
                    except BaseException as error:data.update(status='error',error_code=error_code(error))
                    parent.recording_action={}
                    try:persist()
                    except ValueError: data.update(status='error',error_code='file_access_denied')
            future.add_done_callback(completed)
            self._start_scheduler();self.notified=False
            return token

    def cancel_recording_recovery(self,token):
        with self.lock:
            entry=self.recording_operations.get(token)
            if not entry:raise ValueError('Invalid recording recovery action.')
            entry['cancel'].set()

    def _recover_recording_worker(self,parent,action,acknowledge_gaps,data,persist,destination,cancel):
        from services.recording_sessions import build_exports
        from services.output_validation import validation_session,validate_output
        from services.malware_scan import scan_file
        from services.media_gate import publish,SecurityReviewError
        from services.job_lifecycle import file_signature
        export_parent=copy.copy(parent);export_parent.path=destination or parent.path
        cancelled=lambda:self.closed.is_set() or cancel.is_set()
        held=False
        try:
            if cancelled():raise DownloadPaused('DOWNLOAD_PAUSED')
            while not self.conversion_slot.acquire(timeout=.1):
                if cancelled():raise DownloadPaused('DOWNLOAD_PAUSED')
            held=True
            def progress(phase,current,total):
                with self.lock:data.update(status='running',phase=phase,current=current,total=total)
            def publish_file(output,directory,identity,checked,summary):
                with self.lock:
                    journal=parent.session_exports.setdefault(identity,{})
                if journal.get('target') and Path(journal['target']).is_file():
                    from services.publication_recovery import recover_saved_file
                    holder=Job(parent.url,{'format':'video','quality':'max'},export_parent.path,parent.bin_dir,work_path=str(directory),publication_intent=journal)
                    saved=recover_saved_file(holder,cancelled)
                    if saved:
                        checked=validate_output(saved,parent.bin_dir,True,expect_audio=summary.get('expected_audio',True),include_duration=True)
                        path=saved
                    else:path=None
                else:path=None
                if checked is None and path is None:return None
                verdict=scan_file(path or output,cancelled)
                if verdict=='review':raise SecurityReviewError()
                if path is None:
                    def prepare(source,target):
                        with self.lock:
                            journal.update(schema=1,source=source,target=target,source_signature=file_signature(source),state='prepared')
                            persist()
                    def created(source,target):
                        with self.lock:journal.update(state='created',target_signature=file_signature(target));persist()
                    path=publish(output,export_parent.path,directory,prepare,created)
                from services.ui_messages import message
                title=parent.title+' ['+(message('session.joined_title') if summary['joined'] else str(data['current']+1))+']'
                child=Job(parent.url,{'format':'video','quality':'max','video_container':'mkv'},export_parent.path,parent.bin_dir,id=identity,title=title,media_key=parent.media_key,output_path=path,
                    quality_summary={'video_reencoded':False,'container':'mkv','recovered_parts':summary,'verified_fields':['streams'],'audio':checked['audio']})
                with self.lock:
                    self.pending_history.append(completion_record(child));journal.update(state='finished',target_signature=file_signature(path));persist()
                return identity
            with validation_session():
                return build_exports(export_parent,parent.bin_dir,action,acknowledge_gaps,progress,cancelled,publish_file)
        finally:
            if held:self.conversion_slot.release()

    def record(self, count):
        with self.lock:
            now=self.clock()
            if self.samples and now-self.samples[-1][0]<.1:
                stamp,total=self.samples[-1];self.samples[-1]=(stamp,total+count)
            else:self.samples.append((now,count))
            while self.samples and self.samples[0][0]<now-10:self.samples.popleft()

    def _throughput(self, now):
        while self.samples and self.samples[0][0]<now-10:self.samples.popleft()
        native = sum(n for _, n in self.samples) / max(1, min(10, now - self.samples[0][0])) if self.samples else 0
        # FFmpeg live capture bypasses the native HTTP byte reader. Include its
        # measured output-byte rate instead of showing a misleading zero total.
        return native + sum(j.recording_speed_bps for j in self.jobs
                            if j.is_live and j.future is not None and j.status == 'downloading')

    def _publish(self):
        from services.recovery import recovery_items
        visible = [j for j in self.jobs if j.status != 'expanded']
        operations=[dict(op['data']) for op in self.recording_operations.values()]
        running = any(j.future is not None or j.status in ('queued', 'retry_wait') for j in visible) or any(op['status'] in ('queued','running') for op in operations)
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
            'recovery_items': recovery_items(visible),
            'recording_operations':operations,
            'shutting_down': self.closed.is_set(),
            'total_items': len(visible), 'items': [
                {'id': j.id, 'url': j.url, 'title': j.title, 'thumbnail': j.thumbnail,
                 'percent': j.percent, 'speed': j.speed, 'status': j.status, 'error': j.error,'error_code':j.error_code,'error_phase':j.error_phase,'phase':j.phase,'security_status':j.security_status,
                 'stage_seconds':self.traces[j.id].elapsed() if j.id in self.traces else 0,
                 'quality_summary':j.quality_summary,'attempts':j.workflow.get('attempts',0),
                 'total_bytes': j.total_bytes, 'downloaded_bytes': j.downloaded_bytes, 'eta': j.eta,
                 'is_live':j.is_live,'recorded_seconds':j.recorded_seconds,'recording_speed_bps':j.recording_speed_bps,'recording_pace':j.recording_pace,'recording_phase':j.recording_phase,'catchup_remaining_seconds':j.catchup_remaining_seconds,'catchup_available_seconds':j.catchup_available_seconds,'catchup_from_start':j.catchup_from_start,'recording_limit':j.recording_limit,'stop_requested':j.stop_requested,
                 'format': j.options.get('format'), 'quality': j.options.get('quality'),
                 'video_container':j.options.get('video_container','mp4'),
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
            from services.ui_messages import message
            show_notification('Video Downloader Pro', message('downloads_complete'))

    def _expand(self, job):
        from yt_dlp import YoutubeDL
        from core.bandwidth import attach_budget
        options = {'extract_flat': 'in_playlist', 'quiet': True, 'noplaylist': False}
        with YoutubeDL(options) as ydl:
            from services.secure_transport import attach_network_guard
            attach_network_guard(ydl)
            attach_budget(ydl, self.budget, lambda: bool(state['cancel_flags'].get(job.url)), self.record)
            from services.youtube_region import extract_info
            info = extract_info(ydl, job.url, download=False)
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
        from services.job_lifecycle import JobLifecycle
        trace=JobLifecycle(job,self.clock)
        with self.lock:self.traces[job.id]=trace
        try:return self._execute_download(job,trace)
        finally:
            with self.lock:
                trace.close();self.traces.pop(job.id,None)

    def _execute_download(self, job, trace):
        if job.publication_intent:
            from services.publication_recovery import recover_saved_file
            saved=recover_saved_file(job,lambda:bool(state['cancel_flags'].get(job.url)))
            if saved:
                from services.output_validation import validate_output
                from services.malware_scan import scan_file
                from services.media_gate import SecurityReviewError
                trace.stage('recovering_file')
                job.status='converting'
                info=copy.deepcopy(job.source_signature)
                if job.quality_summary.get('expected',{}).get('hdr'):info['dynamic_range']='HDR'
                validate_output(saved,job.bin_dir,job.options.get('format')!='audio',
                    expected_duration=info.get('duration') if not job.is_live else None,
                    expect_audio=any(f.get('acodec') not in (None,'none') for f in info.get('requested_formats',[])))
                from services.media_quality import verify_quality
                job.quality_summary=verify_quality(saved,job.bin_dir,info,job.options)
                job.security_status=scan_file(saved,lambda:bool(state['cancel_flags'].get(job.url)))
                if job.security_status=='review':raise SecurityReviewError()
                job.output_path=saved;job.downloaded_bytes=Path(saved).stat().st_size
                job.total_bytes=job.downloaded_bytes;job.size_estimated=False
                trace.data.update(validated=True,published=True)
                with self.lock:self._persist(required=True)
                return True
            job.publication_intent={}
        Path(job.path).mkdir(parents=True, exist_ok=True)
        # Injected test workers retain their contract. New real downloads are
        # staged on the destination volume. Legacy partials migrate by rename,
        # without copying a multi-hour download or restarting its byte offset.
        working_path = job.path
        if not self.worker:
            from services.media_gate import staging_directory, migrate_checkpoint
            work = staging_directory(job.path, job.id, job.work_path)
            job.work_path = working_path = str(work)
            if job.output_template:
                job.output_template = migrate_checkpoint(job.output_template, work)
            with self.lock:self._persist(required=True)
        conversion_held = [False]
        conversion_depth = [0]
        approved = {}
        from services.media_gate import MediaDiskGuard
        disk_guard = MediaDiskGuard(working_path)
        disk_guard.check()
        def stage(code):
            from services.source_operation import PHASES
            if code in PHASES:
                with self.lock:trace.stage(code)
        def hook(data):
            disk_guard.check()
            if state['cancel_flags'].get(job.url):
                raise DownloadPaused('DOWNLOAD_PAUSED')
            data.setdefault('info_dict', {})['webpage_url'] = job.url
            with self.lock:
                if job.status != 'pausing':
                    job.status = 'converting' if data['status'] == 'finished' else 'downloading'
                    trace.stage('postprocess' if data['status']=='finished' else 'downloading')
                total = data.get('total_bytes') or data.get('total_bytes_estimate')
                if total:
                    job.percent = min(100, round(data.get('downloaded_bytes', 0) * 100 / total, 1))
                if job.is_live and 'recorded_seconds' in data:
                    job.recorded_seconds=data['recorded_seconds'];job.recording_limit=data['recording_limit']
                    job.recording_speed_bps=data.get('recording_speed_bps',0)
                    job.recording_pace=data.get('recording_pace',0)
                    job.recording_phase=data.get('recording_phase','live')
                    job.catchup_remaining_seconds=data.get('catchup_remaining_seconds',0)
                    job.catchup_available_seconds=data.get('catchup_available_seconds',0)
                    job.catchup_from_start=bool(data.get('catchup_from_start',False))
                    job.duration=job.recorded_seconds
                    if job.recording_parts and job.recording_parts[-1].get('state')=='recording':
                        job.recording_parts[-1].update(seconds=job.recorded_seconds,bytes=data.get('downloaded_bytes',0))
                    job.percent=min(99,round(job.recorded_seconds/max(1,job.recording_limit)*100,1))
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
        opts = get_ydl_opts(job.options['format'], job.options['quality'], working_path, 0,
                            job.options.get('embed_subs', False), hook, job.bin_dir,video_container=job.options.get('video_container','mp4'))
        # Native fragments use the shared response budget, never independent rate caps.
        opts.update(outtmpl=job.output_template or str(Path(working_path) / '%(title)s [%(id)s].%(ext)s'),
                    ignoreerrors=False, hls_prefer_native=True, external_downloader=None,
                    concurrent_fragment_downloads=3, postprocessor_hooks=[postprocess],
                    socket_timeout=15, retries=3, fragment_retries=5,
                    skip_unavailable_fragments=False,
                    retry_sleep_functions={'fragment': fragment_retry_wait(
                        lambda: bool(state['cancel_flags'].get(job.url)),progress=stage)})
        from services.track_selection import apply_tracks
        apply_tracks(opts, job.options)
        def protocol_support(native):
            with self.lock:
                job.native = native
                if not native and self.budget.rate:
                    raise ValueError('Bu yayın türü toplam hız sınırını desteklemiyor. Sınırı kaldırarak tekrar deneyin.')
        def metadata(info):
            from services.source_recovery import source_checkpoint
            with self.lock:
                job.source_signature=source_checkpoint(info)
                job.is_live=bool(info.get('is_live'))
                if job.is_live and info.get('duration'):job.recorded_seconds=info['duration']
                job.title = info.get('title') or job.title
                job.thumbnail = info.get('thumbnail') or job.thumbnail
                job.media_key = media_key(job.url, info)
                job.total_bytes = estimate_size(info) or job.total_bytes
                job.duration = info.get('duration') or job.duration
        def verify(path, info):
            from services.media_gate import check_media_header, contained_file, withhold, SecurityReviewError
            from services.output_validation import validate_output
            from services.malware_scan import scan_file
            with self.lock:
                job.status, job.phase, job.security_status = 'converting', 'security_check', 'checking'
                trace.stage('security_check')
            if job.work_path:contained_file(path, job.work_path)
            before=Path(path).stat()
            try:
                check_media_header(path)
                # No source may bypass the stream validation through a generic
                # extractor or a forged filename/container extension.
                verified=validate_output(path, job.bin_dir, job.options.get('format') != 'audio',include_duration=True,reuse_validation=True,
                    expected_duration=info.get('duration') if not info.get('is_live') and info.get('extractor_key') in ('EmbeddedMedia','FullHDFilmizlesene') else None,
                    expect_audio=any(f.get('acodec') not in (None, 'none') for f in (info.get('requested_formats') or [info])))
            except ValueError:
                job.security_status = 'blocked'
                if job.work_path:withhold(path, job.work_path)
                raise
            stage('quality_check')
            from services.media_quality import verify_quality,QualityMismatch
            try:job.quality_summary=verify_quality(path,job.bin_dir,info,job.options)
            except QualityMismatch as error:
                job.quality_summary={'expected':error.expected,'actual':error.actual,'mismatch':True}
                job.security_status='pending'
                raise
            stage('security_scan')
            job.security_status = scan_file(path, lambda:bool(state['cancel_flags'].get(job.url)))
            if job.security_status == 'review':
                if job.work_path:withhold(path, job.work_path)
                raise SecurityReviewError()
            after=Path(path).stat()
            signature=lambda details:(details.st_size,details.st_mtime_ns,details.st_ino)
            if signature(before)!=signature(after):
                from services.output_validation import OutputValidationError
                raise OutputValidationError('Media changed during security checks; file withheld.')
            approved[path]=signature(after)
            trace.data['validated']=True
            return verified
        def completed(path):
            from services.file_security import mark_internet_file
            if job.work_path:
                details=Path(path).stat()
                if approved.get(path)!=(details.st_size,details.st_mtime_ns,details.st_ino):
                    from services.output_validation import OutputValidationError
                    raise OutputValidationError('Media has not passed security checks; file withheld.')
                stage('saving_file')
                from services.media_gate import publish
                from services.job_lifecycle import file_signature
                def prepare(source,target):
                    job.publication_intent={'schema':1,'source':source,'target':target,'source_signature':file_signature(source),'state':'prepared'}
                    with self.lock:self._persist(required=True)
                def created(source,target):
                    job.publication_intent.update(state='created',target_signature=file_signature(target))
                    job.recovery_reason='publication'
                    with self.lock:self._persist(required=True)
                path = publish(path, job.path, job.work_path,prepare,created)
            mark_internet_file(path)
            with self.lock:
                job.output_path = path
                job.downloaded_bytes = Path(path).stat().st_size
                job.total_bytes, job.size_estimated, job.eta = job.downloaded_bytes, False, 0
                trace.data['published']=True
                if job.recording_parts and job.recording_parts[-1].get('state')=='captured':
                    job.recording_parts[-1].update(state='published',published_path=path)
                    from services.recording_sessions import save_manifest
                    save_manifest(job,job.work_path)
                self._persist(required=True)
        def thumbnail(path):
            with self.lock:
                job.thumbnail=path
        def checkpoint_target(template):
            # Persist identity and the exact reserved stem before the first byte,
            # not merely at the scheduler's next periodic checkpoint.
            if job.work_path and (not isinstance(template,str) or not template.endswith('.%(ext)s') or Path(template.replace('%%','%')).parent.resolve()!=Path(job.work_path).resolve()):
                from services.output_validation import OutputValidationError
                raise OutputValidationError('Output target escaped its private workspace.')
            with self.lock:
                job.output_template = template
                self._persist(required=True)
        def live_part(event,target,info,error_code=''):
            from services.recording_sessions import part_event
            with self.lock:
                part_event(job,event,target,info,error_code)
                self._persist(required=True)
        from utils.file_helpers import load_settings
        request = dict(job.options, _transfer_mode=load_settings().get('transfer_mode','stable'), _stop_recording=lambda:job.stop_requested, _budget=self.budget, _record=self.record,_stage=stage,
                       _error=lambda message: setattr(job, 'error', message),
                       _protocol_support=protocol_support, _metadata=metadata, _completed=completed,
                       _verify=verify if not self.worker else None,
                       _live_part=live_part,
                       _thumbnail=thumbnail, _preview_id=job.id,
                       _preview_dir=str(self.store.path.parent/'previews') if self.store else None,
                       _resume_target=bool(job.output_template),_source_signature=copy.deepcopy(job.source_signature),
                       _target=checkpoint_target)
        try:
            return (self.worker or _download_single)(job.url, opts, working_path, request, None)
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
        with self.lock:
            # Refuse a graceful exit if the initial durable checkpoint fails.
            # Keep the scheduler usable in that case so the user can free space.
            self._persist(required=True)
            self.closed.set()
            for job in self.jobs:
                if job.future is not None and job.status != 'converting':
                    state_actions.set_cancel_flag(job.url, True)
                    job.recovery_reason = 'shutdown'
                elif job.future is None and job.status in ('queued', 'retry_wait'):
                    state_actions.set_cancel_flag(job.url, True)
                    job.status, job.speed = 'paused', 'Duraklatıldı'
                    job.recovery_reason = 'shutdown'
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.recording_executor.shutdown(wait=True,cancel_futures=True)
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
            self._persist(required=True)
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
