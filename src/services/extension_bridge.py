"""Opt-in native messaging bridge. Ephemeral media data stays in memory."""
import json, secrets, threading, time, os, re, hmac
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from services.media_discovery import public_url

HOST_NAME='com.videodownloaderpro.bridge'

def app_language():
    from state.app_state import state
    from services.language_service import supported_language
    return supported_language(state.get('current_lang')) or 'en'
def endpoint_file():
    return Path(os.environ.get('VIDEO_DOWNLOADER_DATA_DIR') or Path(os.environ.get('APPDATA',str(Path.home())))/'YoutubePro')/'extension-endpoint.json'

class ExtensionBridge:
    def __init__(self):
        self.lock=threading.RLock();self.jobs={};self.clients={};self.seen=0;self.server=None;self.secret=secrets.token_urlsafe(32)
    def exchange(self,message):
        with self.lock:
            self.seen=time.monotonic()
            now=time.monotonic()
            identity=message.get('extension_id');version=message.get('version')
            if isinstance(identity,str) and re.fullmatch(r'[a-p]{32}',identity) and isinstance(version,str) and re.fullmatch(r'\d{1,4}(?:\.\d{1,4}){2,3}',version):
                self.clients={k:v for k,v in self.clients.items() if now-v[0]<60}
                if len(self.clients)<8 or identity in self.clients:self.clients[identity]=(now,version)
            self.jobs={k:v for k,v in self.jobs.items() if now-v['created']<180}
            if message.get('type')=='result':
                job=self.jobs.get(message.get('id'))
                if job and not job.get('result'):
                    source=message.get('source');page=message.get('page')
                    if page!=job['url'] or not public_url(source,resolve=True):raise ValueError('Invalid source')
                    if message.get('drm'):raise ValueError('Protected source')
                    job['result']={'stream':source,'streams':[source],'title':str(message.get('title') or 'Video')[:500],
                        'thumbnail':'','embed':page,'headers':{},'source_headers':{source:{'Referer':page}},
                        'source_types':{source:message['kind']} if message.get('kind') in ('hls','dash') else {},
                        'content_scope':'preview' if message.get('preview') is True else 'unknown','discovery_method':'extension'}
                    job['event'].set()
            return {'language':app_language(),
                    'jobs':[{'id':k,'url':v['url'],'focus_seq':v.get('focus_seq',0)} for k,v in self.jobs.items() if not v.get('result')]}
    def request_focus(self,url):
        with self.lock:
            job=next((j for j in self.jobs.values() if j['url']==url and not j.get('result')),None)
            if job is None:raise ValueError('No pending browser inspection for this link.')
            job['focus_seq']=job.get('focus_seq',0)+1

    def client_connected(self,identity,version):
        with self.lock:
            client=self.clients.get(identity)
            return self.server is not None and bool(client and time.monotonic()-client[0]<=8 and client[1]==version)
    def available(self):
        return self.server is not None and time.monotonic()-self.seen<=8
    def resolve(self,url,timeout=120):
        from services.source_operation import current_operation,report_stage
        if not self.available() or not public_url(url,resolve=True):return None
        with self.lock:
            identity=next((key for key,value in self.jobs.items() if value['url']==url),None)
            if identity is None:
                if len(self.jobs)>=2:raise ValueError('Tarayıcı eklentisi meşgul. Mevcut incelemenin bitmesini bekleyin.')
                identity=secrets.token_urlsafe(24)
                self.jobs[identity]={'url':url,'created':time.monotonic(),'event':threading.Event(),'waiters':0}
            job=self.jobs[identity];job['waiters']=job.get('waiters',0)+1;event=job['event']
        try:
            report_stage('browser_extension')
            deadline=min(time.monotonic()+timeout,job['created']+180)
            while time.monotonic()<deadline:
                op=current_operation()
                if op and op.cancelled():raise ValueError('DOWNLOAD_PAUSED')
                if event.wait(.2):return dict(job['result'])
            raise ValueError('Tarayıcı eklentisi kaynak bulamadı. Açılan sekmede videoyu oynatıp tekrar deneyin.')
        finally:
            with self.lock:
                job['waiters']-=1
                if not job['waiters'] and self.jobs.get(identity) is job:self.jobs.pop(identity,None)
    def start(self):
        bridge=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                # Authenticate before reading an attacker-controlled request body.
                authorization=self.headers.get('Authorization','')
                if (self.path!='/exchange' or not hmac.compare_digest(authorization.encode('utf-8'),('Bearer '+bridge.secret).encode('ascii'))
                        or 'Origin' in self.headers or self.headers.get('Sec-Fetch-Site') is not None
                        or self.headers.get('Transfer-Encoding') is not None):
                    self.close_connection=True;self.send_error(403);return
                try:
                    n=int(self.headers.get('Content-Length','0'))
                    if not 0<n<=65536:raise ValueError()
                    self.connection.settimeout(3)
                    body=self.rfile.read(n)
                    if len(body)!=n:raise ValueError()
                except (ValueError,OSError):
                    self.send_error(400);return
                try:
                    result=bridge.exchange(json.loads(body))
                    data=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
                except Exception:self.send_error(400)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        try:
            path=endpoint_file();path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps({'port':self.server.server_port,'token':self.secret}),encoding='utf-8')
        except OSError:
            self.server.server_close();self.server=None
            raise
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
    def close(self):
        if self.server:self.server.shutdown();self.server.server_close();self.server=None
        try:
            p=endpoint_file()
            if json.loads(p.read_text()).get('token')==self.secret:p.unlink()
        except (OSError,ValueError):pass
extension_bridge=ExtensionBridge()
