"""A capability-scoped, streaming HTTP gateway for FFmpeg live inputs.

The recorder only sees loopback URLs. Remote manifests, segments, keys and
redirects use the same pinned HTTP transport as ordinary downloads.
"""
import queue,re,secrets,threading,time,base64,binascii
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,urljoin
from xml.etree import ElementTree as ET
import requests
from services.security_policy import require_public_link,UnsafeLink
from services.secure_transport import pin_requests_session
from services.safe_xml import parse_manifest

ET.register_namespace('','urn:mpeg:dash:schema:mpd:2011')


def rewrite_hls(body,base,make):
    lines=[]
    for line in body.decode('utf-8-sig').splitlines():
        if line.strip() and not line.startswith('#'):line=make(urljoin(base,line.strip()))
        else:line=re.sub(r'URI=([\"\x27])(.*?)\1',lambda m:'URI="'+make(urljoin(base,m[2]))+'"',line)
        lines.append(line)
    return ('\n'.join(lines)+'\n').encode()


def rewrite_dash(body,base,make):
    root=parse_manifest(body)
    if root.tag.rsplit('}',1)[-1]!='MPD':raise ValueError('Invalid DASH manifest')
    def walk(element,parent):
        bases=[child for child in element if child.tag.rsplit('}',1)[-1]=='BaseURL']
        own=urljoin(parent,bases[0].text.strip()) if bases and bases[0].text else parent
        for child in bases:
            if child.text:child.text=make(urljoin(parent,child.text.strip()))
        for key,value in list(element.attrib.items()):
            if key.rsplit('}',1)[-1] in ('media','initialization','sourceURL','index','href'):
                element.set(key,make(urljoin(own,value)))
        if element.tag.rsplit('}',1)[-1]=='Location' and element.text:element.text=make(urljoin(parent,element.text.strip()))
        if element.tag.rsplit('}',1)[-1]=='UTCTiming' and element.get('value','').startswith(('http:','https:')):
            element.set('value',make(element.get('value')))
        for child in element:
            if child not in bases:walk(child,own)
    walk(root,base)
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


class LiveNetwork:
    def __init__(self,contexts,owned=()):
        self.contexts=contexts;self.owned=set(owned);self.token=secrets.token_urlsafe(24)
        self.routes={};self.reverse={};self.lock=threading.RLock();self.server=None
        self.sessions=[];self.available=queue.Queue()
        self.closing=threading.Event()
        self.unsafe=False

    def url(self,remote,index):
        if isinstance(remote,str) and remote.startswith('data:application/octet-stream;base64,') and len(remote)<256:
            try:
                if len(base64.b64decode(remote.split(',',1)[1],validate=True))==16:return remote
            except (ValueError,binascii.Error):pass
        if remote not in self.owned:require_public_link(remote)
        parsed=urlsplit(remote);origin=parsed.scheme+'://'+parsed.netloc
        with self.lock:
            identity=self.reverse.get((origin,index))
            if identity is None:
                if len(self.routes)>=256:raise ValueError('Live source origin limit')
                identity=secrets.token_hex(12);self.routes[identity]=(origin,index);self.reverse[(origin,index)]=identity
        return f'http://127.0.0.1:{self.server.server_port}/{self.token}/{identity}'+(parsed.path or '/')+('?' + parsed.query if parsed.query else '')

    def start(self,inputs):
        owner=self
        for _ in range(8):
            session=pin_requests_session(requests.Session());session.trust_env=False
            self.sessions.append(session);self.available.put(session)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_HEAD(self):self.transfer(True)
            def do_GET(self):self.transfer(False)
            def transfer(self,head):
                parts=self.path.split('/',3)
                route=owner.routes.get(parts[2]) if len(parts)==4 and parts[1]==owner.token else None
                if not route or self.headers.get('Sec-Fetch-Site') is not None:
                    self.send_error(404);return
                origin,index=route;target=origin+'/'+parts[3]
                headers=dict(owner.contexts[index],**{'Accept-Encoding':'identity'})
                if self.headers.get('Origin') and self.headers['Origin']!=headers.get('Origin'):
                    self.send_error(404);return
                if self.headers.get('Range'):headers['Range']=self.headers['Range']
                session=None;local=None;started=False
                try:
                    if target in owner.owned:
                        # Only an exact URL from our own manifest router gets
                        # this capability; never arbitrary loopback destinations.
                        local=requests.Session();local.trust_env=False;session=local
                    else:
                        require_public_link(target);session=owner.available.get(timeout=3)
                    with session.request('HEAD' if head else 'GET',target,headers=headers,stream=True,
                                         allow_redirects=local is None,timeout=(5,15)) as response:
                        response.raise_for_status()
                        mime=response.headers.get('Content-Type','application/octet-stream').split(';')[0].lower()
                        path=urlsplit(response.url).path.lower()
                        if response.headers.get('Content-Encoding','identity')!='identity':raise ValueError('Unexpected live encoding')
                        prefix=bytearray();deadline=time.monotonic()+10
                        if not head:
                            while len(prefix)<16:
                                if time.monotonic()>deadline or owner.closing.is_set():raise ValueError('Live response deadline')
                                chunk=response.raw.read1(4096,decode_content=False)
                                if not chunk:break
                                prefix.extend(chunk)
                        sniff=bytes(prefix).lstrip(b'\xef\xbb\xbf \r\n\t')
                        dash=mime=='application/dash+xml' or path.endswith('.mpd') or sniff.startswith((b'<?xml',b'<MPD'))
                        manifest=dash or mime in ('application/vnd.apple.mpegurl','application/x-mpegurl','application/mpegurl','audio/mpegurl','audio/x-mpegurl') or path.endswith('.m3u8') or sniff.startswith(b'#EXTM3U')
                        body=None
                        if manifest and not head:
                            body=bytearray(prefix)
                            while True:
                                if time.monotonic()>deadline or owner.closing.is_set():raise ValueError('Live manifest deadline')
                                chunk=response.raw.read1(32768,decode_content=False)
                                if not chunk:break
                                body.extend(chunk)
                                if len(body)>4*1024*1024:raise ValueError('Live manifest limit')
                            make=lambda value:owner.url(value,index)
                            body=rewrite_dash(body,response.url,make) if dash else rewrite_hls(body,response.url,make)
                        self.send_response(response.status_code)
                        for key in ('Content-Type','Content-Range','Accept-Ranges'):
                            if key in response.headers:self.send_header(key,response.headers[key])
                        if body is not None:self.send_header('Content-Length',str(len(body)))
                        else:
                            for key in ('Content-Length','Content-Encoding'):
                                if key in response.headers:self.send_header(key,response.headers[key])
                        self.end_headers();started=True
                        if head:return
                        if body is not None:self.wfile.write(body)
                        else:
                            self.wfile.write(prefix)
                            while not owner.closing.is_set():
                                chunk=response.raw.read1(65536,decode_content=False)
                                if not chunk:break
                                self.wfile.write(chunk)
                except Exception as exc:
                    if isinstance(exc,UnsafeLink):owner.unsafe=True
                    if not started:
                        try:self.send_error(502)
                        except OSError:pass
                finally:
                    if local:local.close()
                    elif session:owner.available.put(session)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True);self.worker.start()
        return [self.url(remote,index) for index,remote in enumerate(inputs)]

    def close(self):
        self.closing.set()
        if self.server:
            self.server.shutdown();self.server.server_close();self.worker.join(2);self.server=None
        for session in self.sessions:session.close()
