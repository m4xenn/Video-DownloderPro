"""Per-operation progress and bounded browser handoff, isolated across threads."""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import threading
import time

PHASES={'finding_player','starting_player','validating_source','waiting_server','refreshing_source','downloading','postprocess','ready','error'}
_current=ContextVar('source_operation',default=None)
_browser_slots=threading.BoundedSemaphore(2)


class SourceOperation:
    def __init__(self,progress=None,retain=False,cancelled=None):
        self.progress=progress or (lambda code:None)
        self.retain=retain
        self.releases=[]
        self.cancelled=cancelled or (lambda:False)
        self.lock=threading.RLock()
        self.browser_held=False
        self.transferred=False
    def acquire_browser(self):
        if self.browser_held:return
        if self.cancelled():
            from core.bandwidth import DownloadPaused
            raise DownloadPaused('DOWNLOAD_PAUSED')
        while not _browser_slots.acquire(timeout=.1):
            self.stage('waiting_server')
            if self.cancelled():
                from core.bandwidth import DownloadPaused
                raise DownloadPaused('DOWNLOAD_PAUSED')
        self.browser_held=True
        def release_slot():
            self.browser_held=False;_browser_slots.release()
        with self.lock:self.releases.append(release_slot)
    def stage(self,code):
        if code in PHASES:self.progress(code)
    def release(self):
        with self.lock:callbacks,self.releases=self.releases,[]
        for callback in callbacks:
            try:callback()
            except Exception:pass


def current_operation():return _current.get()
def report_stage(code):
    operation=_current.get()
    if operation:operation.stage(code)


@contextmanager
def source_operation(progress=None,retain=False,cancelled=None):
    operation=SourceOperation(progress,retain,cancelled)
    token=_current.set(operation)
    try:
        yield operation
    except BaseException:
        operation.release();raise
    else:
        if not operation.transferred:operation.release()
    finally:_current.reset(token)


class SourceProgress:
    def __init__(self):self.lock=threading.RLock();self.entries={}
    def set(self,url,phase):
        key=hashlib.sha256(url.encode()).hexdigest()
        with self.lock:
            self.entries={k:v for k,v in self.entries.items() if time.monotonic()-v[1]<180}
            if len(self.entries)>=100:self.entries.pop(next(iter(self.entries)))
            self.entries[key]=(phase if phase in PHASES else 'finding_player',time.monotonic())
    def get(self,url):
        with self.lock:
            phase,at=self.entries.get(hashlib.sha256(url.encode()).hexdigest(),('',0))
            return phase if time.monotonic()-at<180 else ''


source_progress=SourceProgress()
