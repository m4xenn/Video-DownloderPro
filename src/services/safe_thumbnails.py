"""Render remote cover images through a bounded, non-executable local image path."""
from collections import OrderedDict
import hashlib,io,threading,time
from PIL import Image
from services.security_policy import public_link

_lock=threading.RLock()
_urls=OrderedDict()
_cache=OrderedDict()


def register(url):
    if not public_link(url):return '/static/media-placeholder.svg'
    identity=hashlib.sha256(url.encode('utf-8')).hexdigest()[:32]
    with _lock:
        _urls[identity]=url;_urls.move_to_end(identity)
        while len(_urls)>2048:_urls.popitem(last=False)
    return '/safe-thumbnails/'+identity+'.jpg'


def sanitize(data,depth=0):
    changed=False
    if depth>10:return False
    if isinstance(data,dict):
        value=data.get('thumbnail')
        if isinstance(value,str) and value and not value.startswith(('/previews/','/safe-thumbnails/','/static/')):
            data['thumbnail']=register(value);changed=True
        for value in data.values():changed=sanitize(value,depth+1) or changed
    elif isinstance(data,list):
        for value in data:changed=sanitize(value,depth+1) or changed
    return changed


def render(identity):
    from services.secure_transport import pin_requests_session
    import requests
    with _lock:
        if identity in _cache:
            _cache.move_to_end(identity);return _cache[identity]
        url=_urls.get(identity)
    if not url:return None
    try:
        deadline=time.monotonic()+10
        with pin_requests_session(requests.Session()) as session:
            session.trust_env=False
            with session.get(url,headers={'Accept-Encoding':'identity'},stream=True,timeout=(4,6)) as response:
                response.raise_for_status()
                if response.headers.get('Content-Encoding','identity').lower()!='identity':return None
                body=bytearray()
                while time.monotonic()<deadline:
                    chunk=response.raw.read1(32768,decode_content=False)
                    if not chunk:break
                    body.extend(chunk)
                    if len(body)>4*1024*1024:return None
                else:return None
        with Image.open(io.BytesIO(body),formats=['JPEG','PNG','WEBP','GIF','AVIF','BMP']) as image:
            if image.width*image.height>20_000_000:return None
            image.thumbnail((480,480));image=image.convert('RGB')
            output=io.BytesIO();image.save(output,format='JPEG',quality=82)
        result=output.getvalue()
        with _lock:
            _cache[identity]=result
            while len(_cache)>64:_cache.popitem(last=False)
        return result
    except Exception:
        return None
