"""Bounded player discovery, independent of the film or page hostname."""
from copy import copy
import hashlib
from http.cookiejar import Cookie, DefaultCookiePolicy
from http.cookies import SimpleCookie
import threading
import re
from urllib.parse import urljoin, urlsplit
from requests import RequestException

from services.media_discovery import public_url
from services.site_browser import BrowserRequired
from services.site_resolver import SiteResolver, valid_embed, rapidvid_source


def can_discover_after(url, error):
    if not public_url(url):
        return False
    text=str(error).lower()
    if any(word in text for word in ('drm', 'copyright', 'private video', 'login required', 'sign in', 'geo-restricted')):
        return False
    if re.search(r'http error 403|status code[: ]+403',text) and not urlsplit(url).path.lower().endswith(('.mp4','.webm','.m3u8','.mpd','.mkv','.m4a','.mp3')):
        return True  # A browser can load a public page rejected by a plain HTTP client.
    return any(word in text for word in ('unsupported url', 'unsupported embed', 'no video formats', 'no video could be found', 'unable to extract video url'))


def apply_source_context(ydl, source, headers):
    """Never put a captured Cookie header in global headers (CDNs can redirect)."""
    allowed={'Referer','Origin','User-Agent'}
    clean={key:str(value) for key,value in headers.items() if key in allowed and value}
    previous=dict(ydl.params.get('http_headers') or {})
    ydl.params['http_headers']={key:value for key,value in previous.items() if key.lower() not in ('cookie','referer','origin','authorization','proxy-authorization')}
    ydl.params['http_headers'].update(clean)
    # yt-dlp snapshots default headers when its first HTTP handler is built.
    # A native-page attempt may already have created it before browser fallback.
    # Rebuild only that idle transport, preserving the same scoped cookie jar.
    if previous!=ydl.params['http_headers']:
        director=vars(ydl).pop('_request_director',None)
        if director is not None:director.close()
    raw=headers.get('Cookie')
    if raw:
        # Python's default Netscape policy also sends host-only cookies to
        # subdomains. Enable its strict host-only rule for captured credentials.
        policy=ydl.cookiejar._policy
        if isinstance(policy,DefaultCookiePolicy):
            policy=copy(policy)
            policy.strict_ns_domain |= DefaultCookiePolicy.DomainStrictNonDomain
            ydl.cookiejar.set_policy(policy)
        parsed=urlsplit(source)
        jar=SimpleCookie()
        try:jar.load(raw)
        except Exception:return
        # Request headers do not reveal the original cookie scope. Narrow it to
        # the media host and directory instead of forwarding it across hosts.
        path=parsed.path.rsplit('/',1)[0]+'/'
        for name,morsel in jar.items():
            ydl.cookiejar.set_cookie(Cookie(0,name,morsel.value,None,False,parsed.hostname,False,False,
                path,True,parsed.scheme=='https',None,True,None,None,{},False))


class GenericResolver(SiteResolver):
    extractor_key='EmbeddedMedia'

    def media_identity(self,url):
        from services.download_store import media_key
        return hashlib.sha256(media_key(url).encode('utf-8')).hexdigest()[:24]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.jobs={}
        self.work=threading.RLock()

    def pending(self,url):
        with self.lock:
            now=self.clock()
            job=self.jobs.get(url)
            cached=self.cache.get(url)
            return bool((job and now-job['created']<180) or (cached and now-cached[0]<120))

    def details(self,url,fresh=False):
        if not public_url(url,resolve=True):
            raise ValueError('Kaynak inceleme yalnızca genel internet sayfalarında kullanılabilir.')
        # Serialise helper windows without blocking native-site cache lookups.
        with self.work:
            with self.lock:
                self.jobs={key:value for key,value in self.jobs.items() if self.clock()-value['created']<180}
            cached=self.cache.get(url)
            # Reuse a just-inspected stream when Start Download immediately
            # follows a user-assisted preview; reopening the player could lose
            # that interaction. Older queue entries are resolved again.
            if cached and self.clock()-cached[0]<(60 if fresh else 120):
                self.browser.adopt_handoff(cached[1].get('_handoff_token'))
                return dict(cached[1])
            if url not in self.jobs:
                if len(self.jobs)>=20:self.jobs.pop(next(iter(self.jobs)))
                self.jobs[url]={'created':self.clock(),'started':self.clock(),'queue':[(url,None,0)],'visited':set(),'title':'Video','thumbnail':''}
            job=self.jobs[url]
            last_error=None
            while job['queue'] and len(job['visited'])<6 and self.clock()-job['started']<60:
                target,parent,depth=job['queue'][0]
                if target in job['visited'] or not public_url(target,resolve=True):
                    job['queue'].pop(0)
                    continue
                try:
                    observed=None
                    # Reuse a player adapter wherever it is embedded, regardless
                    # of the parent website. Unknown players use the common probe.
                    if valid_embed(target):
                        try:
                            stream=rapidvid_source(self._html(target,parent))
                            observed={'sources':[stream],'source_headers':{stream:{'Referer':urljoin(target,'/')}},'discovery_method':'adapter'}
                        except (ValueError,RequestException):
                            pass
                    if observed is None:
                        observed=self.browser.discover(target,parent_url=parent)
                    final_url=observed.get('url') or target
                    if not public_url(final_url,resolve=True):
                        raise ValueError('Oynatıcı genel internet dışına yönlendirildi.')
                    if depth==0:
                        job['title']=str(observed.get('title') or 'Video')[:500]
                        thumbnail=urljoin(final_url,str(observed.get('thumbnail') or '')) if observed.get('thumbnail') else ''
                        job['thumbnail']=thumbnail if public_url(thumbnail) else ''
                    streams=list(dict.fromkeys(source for source in observed.get('sources',[]) if public_url(source,resolve=True)))[:8]
                    if streams:
                        contexts=observed.get('source_headers') or {}
                        for stream in streams:
                            contexts.setdefault(stream,{'Referer':final_url,'User-Agent':observed.get('user_agent') or ''})
                        result={'stream':streams[0],'streams':streams,'embed':target,'headers':{},'source_headers':contexts,
                                'discovery_method':observed.get('discovery_method','dom'),
                                '_handoff_token':observed.get('_handoff_token'),
                                'title':job['title'],'thumbnail':job['thumbnail']}
                        if len(self.cache)>=20:self.cache.pop(next(iter(self.cache)))
                        self.cache[url]=(self.clock(),result)
                        self.jobs.pop(url,None)
                        return dict(result)
                    if depth<3:
                        frames=[frame for frame in observed.get('embeds',[]) if isinstance(frame,dict) and public_url(frame.get('url'))]
                        frames.sort(key=lambda frame:float(frame.get('area') or 0),reverse=True)
                        for frame in frames[:3]:
                            child=frame['url']
                            if child not in job['visited'] and child!=target:
                                job['queue'].append((child,final_url,depth+1))
                except BrowserRequired:
                    # Keep this exact frontier for Continue / Check again.
                    job['started']=self.clock()
                    raise
                except ValueError as exc:
                    if 'DRM' in str(exc):
                        self.jobs.pop(url,None)
                        raise
                    self.browser.close()
                    last_error=exc
                job['visited'].add(target)
                job['queue'].pop(0)
            self.jobs.pop(url,None)
            raise ValueError('Sayfada indirilebilir ana video kaynağı bulunamadı. '+str(last_error or 'Oynatıcı erişim veya kullanıcı etkileşimi gerektiriyor olabilir.'))


generic_resolver=GenericResolver()
