"""On-demand, bounded pywebview page inspection. No credentials or JS API exposed."""
import threading
import time
import uuid
from urllib.parse import urlsplit

SNAPSHOT = """(() => ({
 title: document.querySelector('h1')?.textContent || document.title,
 thumbnail: document.querySelector('meta[property="og:image"]')?.content || '',
 embeds: Array.from(document.querySelectorAll('iframe')).map(e => e.getAttribute('data-src') || e.getAttribute('src')).filter(Boolean)
}))()"""


PLAYER_SNAPSHOT = r"""(() => {
 const sources=[]; let drm=false;
 try {
   if(typeof jwplayer === 'function') {
     const item=jwplayer().getPlaylist()?.[0];
     if(item) {
       drm=Boolean(item.drm);
       if(item.file) sources.push(item.file);
       for(const source of (item.sources || []).slice(0,12)) {
         if(source.drm) drm=true;
         if(source.file) sources.push(source.file);
       }
     }
   }
 } catch(_) {}
 for(const element of document.querySelectorAll('video,video source')) {
   const value=element.currentSrc || element.src;
   if(value && /^https:\/\//i.test(value)) sources.push(value);
 }
 return {sources:[...new Set(sources)].slice(0,12),drm,user_agent:navigator.userAgent};
})()"""


class BrowserRequired(ValueError):
    def __init__(self, token):
        super().__init__('Sayfa kullanıcı doğrulaması veya etkileşim bekliyor. Tarayıcıda devam edip tekrar kontrol edin.')
        self.token = token


class SiteBrowser:
    def __init__(self):
        self.lock = threading.RLock()
        self.session = None
        self.enabled = False

    def inspect(self, url, player_url=None, discovery=False):
        import webview
        if not self.enabled or not webview.windows:
            raise ValueError('Bu sayfa için masaüstü uygulamasındaki tarayıcı desteği gerekiyor.')
        with self.lock:
            session = self.session
            if session and (session['url'] != url or session.get('target') != (player_url or url) or session.get('discovery', False) != discovery):
                raise ValueError('Önce açık olan site incelemesini tamamlayın veya iptal edin.')
            if not session:
                session = {'url': url, 'target':player_url or url, 'discovery':discovery, 'requests':{}, 'candidates':[], 'token': uuid.uuid4().hex, 'loaded': threading.Event(), 'closed': False}
                self.session = session
                try:
                    window = webview.create_window('Video Downloader Pro · Kaynak inceleme', html='<html><body></body></html>',
                        hidden=True, focus=False, width=1000, height=760, js_api=None)
                    session['window'] = window
                    window.events.loaded += lambda: session['loaded'].set()
                    window.events.closed += lambda: self._closed(session)
                    if player_url or discovery:
                        from webview.event import Event
                        # Apply navigation headers synchronously before WebView2 sends them.
                        window.events.request_sent = Event(window, should_lock=True)
                        def on_request(request):
                            if player_url and player_url != url and request.url.split('#')[0] == player_url.split('#')[0]:
                                request.headers['Referer'] = url
                            if discovery:
                                # Credentials stay in memory and only follow their exact media URL.
                                names={'referer':'Referer','origin':'Origin','user-agent':'User-Agent','cookie':'Cookie'}
                                captured={names[k.lower()]:str(v) for k,v in request.headers.items() if k.lower() in names}
                                with self.lock:
                                    if len(session['requests'])>=128:session['requests'].pop(next(iter(session['requests'])))
                                    session['requests'][request.url]=captured
                        def on_response(response):
                            content_type=next((str(v).split(';')[0].strip().lower() for k,v in response.headers.items() if k.lower()=='content-type'),'')
                            manifest=urlsplit(response.url).path.lower().endswith(('.m3u8','.mpd'))
                            if response.status_code in (200,206) and (manifest or content_type in ('application/vnd.apple.mpegurl','application/x-mpegurl','application/mpegurl','audio/mpegurl','audio/x-mpegurl','application/dash+xml','video/mp4','video/webm')):
                                with self.lock:
                                    if len(session['candidates'])<20:
                                        session['candidates'].append({'url':response.url,'headers':dict(session['requests'].get(response.url) or {})} if discovery else response.url)
                        window.events.request_sent += on_request
                        window.events.response_received += on_response
                    window.load_url(player_url or url)
                    timer = threading.Timer(180, lambda: self.close(session['token']))
                    timer.daemon = True
                    session['timer'] = timer
                    timer.start()
                except Exception:
                    self.session = None
                    raise ValueError('Kaynak inceleme tarayıcısı başlatılamadı.')
        deadline = time.monotonic() + 18
        while time.monotonic() < deadline:
            if session['closed']:
                raise ValueError('Site inceleme penceresi kapatıldı. Bağlantıyı tekrar deneyin.')
            if session['loaded'].is_set() or session['window'].events.loaded.is_set():
                pending = session.get('evaluation')
                if pending is None:
                    pending = {'done': threading.Event(), 'result': None}
                    session['evaluation'] = pending
                    def evaluate(target=pending):
                        try:
                            from services.media_discovery import DISCOVERY_SNAPSHOT
                            target['result'] = session['window'].evaluate_js(DISCOVERY_SNAPSHOT if discovery else (PLAYER_SNAPSHOT if player_url else SNAPSHOT))
                        except Exception:
                            pass
                        finally:
                            target['done'].set()
                    threading.Thread(target=evaluate, daemon=True).start()
                pending['done'].wait(.5)
                if pending['done'].is_set():
                    result = pending['result']
                    session['evaluation_result'] = result
                    session['evaluation'] = None
                    if isinstance(result, dict):
                        if discovery:
                            from services.media_discovery import choose_media
                            try:
                                with self.lock:
                                    observed=[{'url':source,'headers':dict(headers)} for source,headers in session['requests'].items()]
                                    # Only successful media responses can resolve a blob URL.
                                    candidates=list(session['candidates'])
                                selected=choose_media(result,candidates)
                            except ValueError:
                                self.close(session['token'])
                                raise
                            if selected:
                                signature=tuple(selected['sources'])
                                if session.get('selected_signature') != signature:
                                    session['selected_signature']=signature
                                    session['selected_at']=time.monotonic()
                                if time.monotonic()-session['selected_at']<2:
                                    time.sleep(.25)
                                    continue
                                # Direct DOM URLs can have headers even before a response arrives.
                                for source in selected['sources']:
                                    request=next((item for item in observed if item['url']==source),None)
                                    if request:selected['source_headers'][source].update(request['headers'])
                                result.update(selected)
                                self.close(session['token'])
                                return result
                            if result.get('embeds') and time.monotonic()-session.setdefault('discovered_at',time.monotonic())>=2:
                                self.close(session['token'])
                                return result
                        elif player_url:
                            if result.get('drm'):
                                self.close(session['token'])
                                raise ValueError('Bu oynatıcının kaynağı DRM korumalı.')
                            sources=result.get('sources') or session['candidates']
                            if sources:
                                result['sources']=sources
                                self.close(session['token'])
                                return result
                        elif result.get('embeds'):
                            self.close(session['token'])
                            return result
            time.sleep(.75)
        if discovery and isinstance(session.get('evaluation_result'), dict) and not session['evaluation_result'].get('interaction'):
            self.close(session['token'])
            raise ValueError('Bu çerçevede kullanılabilir video oynatıcısı bulunamadı.')
        raise BrowserRequired(session['token'])

    def inspect_player(self, player_url, page_url):
        return self.inspect(page_url, player_url=player_url)

    def discover(self, page_url, parent_url=None):
        return self.inspect(parent_url or page_url, player_url=page_url, discovery=True)

    def _closed(self, session):
        with self.lock:
            session['closed'] = True
            session['loaded'].set()
            if self.session is session:
                self.session = None
            if session.get('timer'):
                session['timer'].cancel()

    def show(self, token):
        with self.lock:
            session = self.session
            if not session or session['token'] != token or session['closed']:
                raise ValueError('Site incelemesi sona erdi. Bağlantıyı tekrar kontrol edin.')
            session['window'].show()

    def close(self, token=None):
        with self.lock:
            session = self.session
            if not session or (token is not None and session['token'] != token):
                return
            self.session = None
            session['closed'] = True
            session['loaded'].set()
            if session.get('timer'):
                session['timer'].cancel()
        if session.get('window'):
            try:
                session['window'].destroy()
            except Exception:
                pass


site_browser = SiteBrowser()
