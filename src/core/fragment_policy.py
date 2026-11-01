"""Opt-in probes between VOD jobs, with rollback; no mid-file transport changes."""
import hashlib
import threading
import time
from urllib.parse import urlsplit


class FragmentPolicy:
    def __init__(self,clock=time.monotonic):
        self.clock=clock;self.lock=threading.RLock();self.hosts={}

    def begin(self,info,mode='stable',rate_limit=0):
        embedded=info.get('extractor_key') in ('EmbeddedMedia','FullHDFilmizlesene')
        stable=1 if embedded else 3
        if mode!='auto' or rate_limit or info.get('is_live'):return None,stable
        formats=info.get('requested_formats') or [info]
        if not any('m3u8' in f.get('protocol','') or f.get('protocol')=='http_dash_segments' for f in formats):return None,stable
        hosts=sorted({urlsplit(f.get('manifest_url') or f.get('url') or '').netloc for f in formats})
        key=hashlib.sha256('|'.join(hosts).encode()).hexdigest()
        with self.lock:
            if key not in self.hosts and len(self.hosts)>=128:return None,1
            state=self.hosts.setdefault(key,dict(limit=1,baseline=None,previous=1,cooldown=0,active=0,overlap=False))
            state['active']+=1
            if state['active']>1:state['overlap']=True
            limit=1 if self.clock()<state['cooldown'] else state['limit']
            return (key,self.clock(),limit),limit

    def finish(self,ticket,bytes_received,success,transfer_seconds=None):
        if ticket is None:return
        key,start,limit=ticket
        with self.lock:
            state=self.hosts[key];elapsed=self.clock()-start if transfer_seconds is None else transfer_seconds
            state['active']=max(0,state['active']-1)
            overlap=state['overlap']
            if not state['active']:state['overlap']=False
            if not success:
                state.update(limit=1,baseline=None,cooldown=self.clock()+600)
                return
            if overlap or elapsed<10 or bytes_received<1_000_000 or self.clock()<state['cooldown']:return
            speed=bytes_received/elapsed
            if state['baseline'] is not None:
                if speed<state['baseline']*1.10:
                    state.update(limit=state['previous'],baseline=None,cooldown=self.clock()+600)
                    return
                state['baseline']=None
            if limit<3:
                state.update(previous=limit,baseline=speed,limit=limit+1)


fragment_policy=FragmentPolicy()
