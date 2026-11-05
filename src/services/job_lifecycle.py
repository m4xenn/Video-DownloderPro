"""Durable attempt/stage summaries; monotonic clocks never survive a restart."""
import time
import math
from datetime import datetime,timezone


class JobLifecycle:
    def __init__(self, job, clock=time.monotonic):
        self.job,self.clock=job,clock
        previous=job.workflow if isinstance(job.workflow,dict) else {}
        timings=previous.get('stage_seconds',{})
        attempts=previous.get('attempts',0)
        if not isinstance(attempts,int) or isinstance(attempts,bool):attempts=0
        self.data={'schema':1,'attempts':min(99999,max(0,attempts))+1,
                   'stage_seconds':{k:v for k,v in list(timings.items())[:64] if isinstance(k,str) and isinstance(v,(int,float)) and math.isfinite(v) and v>=0} if isinstance(timings,dict) else {},
                   'started_utc':datetime.now(timezone.utc).isoformat(),
                   'validated':False,'published':False,'last_stage':job.phase}
        job.workflow=self.data
        self.phase=job.phase;self.changed=clock();self.closed=False

    def stage(self, phase):
        if self.closed or phase==self.phase:return
        self._account()
        self.phase=self.job.phase=phase
        self.data['last_stage']=phase

    def _account(self):
        now=self.clock();elapsed=max(0,now-self.changed);self.changed=now
        self.data['stage_seconds'][self.phase]=round(self.data['stage_seconds'].get(self.phase,0)+elapsed,3)

    def elapsed(self):return max(0,self.clock()-self.changed) if not self.closed else 0

    def close(self):
        if not self.closed:
            self._account();self.closed=True


def file_signature(path):
    from pathlib import Path
    details=Path(path).stat()
    return {'size':details.st_size,'mtime_ns':details.st_mtime_ns,'device':details.st_dev,'inode':details.st_ino}
