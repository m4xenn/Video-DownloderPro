"""On-demand, bounded pywebview page inspection. No credentials or JS API exposed."""
import threading
import time
import uuid

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

    def inspect(self, url, player_url=None):
        import webview
        if not self.enabled or not webview.windows:
            raise ValueError('Bu sayfa için masaüstü uygulamasındaki tarayıcı desteği gerekiyor.')
        with self.lock:
            session = self.session
            if session and (session['url'] != url or session.get('target') != (player_url or url)):
                raise ValueError('Önce açık olan site incelemesini tamamlayın veya iptal edin.')
            if not session:
                session = {'url': url, 'target':player_url or url, 'candidates':[], 'token': uuid.uuid4().hex, 'loaded': threading.Event(), 'closed': False}
                self.session = session
                try:
                    window = webview.create_window('Video Downloader Pro · Kaynak inceleme', html='<html><body></body></html>',
                        hidden=True, focus=False, width=1000, height=760, js_api=None)
                    session['window'] = window
                    window.events.loaded += lambda: session['loaded'].set()
                    window.events.closed += lambda: self._closed(session)
                    if player_url:
                        from webview.event import Event
                        # Apply navigation headers synchronously before WebView2 sends them.
                        window.events.request_sent = Event(window, should_lock=True)
                        def on_request(request):
                            if request.url.split('#')[0] == player_url.split('#')[0]:
                                request.headers['Referer'] = url
                        def on_response(response):
                            content_type=next((str(v).split(';')[0].strip().lower() for k,v in response.headers.items() if k.lower()=='content-type'),'')
                            if response.status_code in (200,206) and content_type in ('application/vnd.apple.mpegurl','application/x-mpegurl','application/dash+xml'):
                                if len(session['candidates'])<20:session['candidates'].append(response.url)
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
                            target['result'] = session['window'].evaluate_js(PLAYER_SNAPSHOT if player_url else SNAPSHOT)
                        except Exception:
                            pass
                        finally:
                            target['done'].set()
                    threading.Thread(target=evaluate, daemon=True).start()
                pending['done'].wait(.5)
                if pending['done'].is_set():
                    result = pending['result']
                    session['evaluation'] = None
                    if isinstance(result, dict):
                        if player_url:
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
        raise BrowserRequired(session['token'])

    def inspect_player(self, player_url, page_url):
        return self.inspect(page_url, player_url=player_url)

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
