"""Bounded HLS history planning; no segment downloads or guessed archive URLs."""
from dataclasses import dataclass,field,replace
from datetime import datetime
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urljoin
import math,time,re,secrets,threading
import requests

MAX_BYTES=2*1024*1024
@dataclass(frozen=True)
class Window:
    durations: tuple
    times: tuple
    target: float
    ended: bool
    body: bytes=field(default=b'',repr=False)
    url: str=field(default='',repr=False)

@dataclass(frozen=True)
class CatchupPlan:
    indices: tuple
    seconds: float=0
    threshold: float=0
    observed_at: float=0
    windows: tuple=field(default=(),repr=False,compare=False)


def parse_window(body,allow_discontinuity=False):
    if len(body)>MAX_BYTES:raise ValueError('Manifest too large')
    text=body.decode('utf-8-sig');lines=text.strip().splitlines()
    if not lines or lines[0].strip()!='#EXTM3U':raise ValueError('Invalid HLS')
    durations=[];times=[];pending=None;timestamp=None;target=1.;ended=False
    for line in lines:
        line=line.strip()
        if line.startswith('#EXT-X-STREAM-INF:'):raise ValueError('Variant playlist required')
        if line=='#EXT-X-DISCONTINUITY' and not allow_discontinuity:raise ValueError('Discontinuous history requires separate handling')
        if line.startswith('#EXT-X-PROGRAM-DATE-TIME:'):
            value=datetime.fromisoformat(line.split(':',1)[1].replace('Z','+00:00'))
            if value.tzinfo is None:raise ValueError('Unzoned program time')
            timestamp=value.timestamp()
        elif line.startswith('#EXT-X-TARGETDURATION:'):
            target=float(line.split(':',1)[1])
            if not math.isfinite(target) or target<=0:raise ValueError('Invalid target')
        elif line.startswith('#EXTINF:'):
            pending=float(line.split(':',1)[1].split(',')[0])
            if not math.isfinite(pending) or pending<=0:raise ValueError('Invalid duration')
        elif line=='#EXT-X-ENDLIST':ended=True
        elif line and not line.startswith('#') and pending is not None:
            durations.append(pending);times.append(timestamp)
            if timestamp is not None:timestamp+=pending
            pending=None
    if not durations:raise ValueError('No HLS history')
    return Window(tuple(durations),tuple(times),target,ended,body)


def read_window(url,headers,allow_discontinuity=False):
    from services.media_discovery import public_url
    # Explicit redirects prevent the manifest probe from following private URLs.
    deadline=time.monotonic()+6
    from services.secure_transport import pin_requests_session
    with pin_requests_session(requests.Session()) as session:
        for _ in range(4):
            if time.monotonic()>deadline:raise ValueError('Manifest inspection deadline')
            if not public_url(url,resolve=True):raise ValueError('Non-public manifest')
            with session.get(url,headers=headers,stream=True,allow_redirects=False,timeout=(3,3)) as response:
                if response.status_code in (301,302,303,307,308):
                    url=urljoin(url,response.headers.get('Location',''));continue
                response.raise_for_status();body=bytearray()
                for chunk in response.iter_content(32768):
                    if time.monotonic()>deadline:raise ValueError('Manifest inspection deadline')
                    body.extend(chunk)
                    if len(body)>MAX_BYTES:raise ValueError('Manifest too large')
                return replace(parse_window(bytes(body),allow_discontinuity),url=url)
    raise ValueError('Too many redirects')


def plan_catchup(formats,headers,cancelled=lambda:False):
    fallback=CatchupPlan(tuple(-3 for _ in formats))
    if not all('m3u8' in f.get('protocol','') or '.m3u8' in f.get('url','').split('?',1)[0] for f in formats):return fallback
    windows=[];observed=time.monotonic()
    try:
        for fmt,context in zip(formats,headers):
            if cancelled():return fallback
            windows.append(read_window(fmt['url'],context))
        if any(w.ended for w in windows):return fallback
        indices=[0]*len(windows)
        if len(windows)>1 and len({f['url'] for f in formats})>1:
            # Independent rendition sequence numbers do not prove synchronization.
            # Require common UTC program-time boundaries instead.
            if any(any(t is None for t in w.times) for w in windows):return fallback
            common=None
            lower=max(w.times[0] for w in windows)
            for point in windows[0].times:
                if point<lower-.05:continue
                matches=[next((i for i,t in enumerate(w.times) if abs(t-point)<.05),None) for w in windows]
                if all(i is not None for i in matches):common=matches;break
            if common is None:return fallback
            indices=common
        seconds=min(sum(w.durations[i:]) for w,i in zip(windows,indices))
        if not math.isfinite(seconds):return fallback
        return CatchupPlan(tuple(indices),seconds,max(w.target for w in windows)*2,observed,tuple(windows))
    except (ValueError,KeyError,TypeError,requests.RequestException,OSError):
        # History inspection failure must not break an otherwise working live source.
        return fallback


class HLSHistoryProxy:
    """Pin each input's first inspected playlist, then refresh from its source.

    Only manifests pass through loopback. Segment/key URLs are made absolute and
    FFmpeg downloads their bytes directly with the existing source context.
    This prevents one rendition's rolling window advancing during input probing
    from silently shifting audio relative to video.
    """
    def __init__(self,plan,formats,headers):
        self.plan,self.formats,self.headers=plan,formats,headers
        self.served=set();self.lock=threading.Lock();self.server=None

    def start(self):
        owner=self;token=secrets.token_urlsafe(24)
        routes={f'/{token}/{i}.m3u8':i for i in range(len(self.formats))}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                index=routes.get(self.path)
                origin=self.headers.get('Origin')
                expected=owner.headers[index].get('Origin') if index is not None else None
                if index is None or self.headers.get('Sec-Fetch-Site') is not None or origin and origin!=expected:
                    self.send_error(404);return
                try:
                    with owner.lock:
                        initial=index not in owner.served;owner.served.add(index)
                    window=owner.plan.windows[index] if initial else read_window(owner.formats[index]['url'],owner.headers[index],allow_discontinuity=True)
                    base=window.url or owner.formats[index]['url']
                    from services.media_discovery import public_url
                    def absolute(uri):
                        value=urljoin(base,uri)
                        if not public_url(value):raise ValueError('Non-public playlist reference')
                        return value
                    lines=[]
                    for line in window.body.decode('utf-8-sig').splitlines():
                        if line.strip() and not line.startswith('#'):line=absolute(line.strip())
                        else:line=re.sub(r'URI="([^"]+)"',lambda m:'URI="'+absolute(m[1])+'"',line)
                        lines.append(line)
                    body=('\n'.join(lines)+'\n').encode()
                    self.send_response(200);self.send_header('Content-Type','application/vnd.apple.mpegurl')
                    self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                except (ValueError,OSError,requests.RequestException):
                    try:self.send_error(502)
                    except OSError:pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True);self.worker.start()
        return [f'http://127.0.0.1:{self.server.server_port}/{token}/{i}.m3u8' for i in range(len(self.formats))]

    def close(self):
        if self.server:
            self.server.shutdown();self.server.server_close();self.worker.join(2);self.server=None
