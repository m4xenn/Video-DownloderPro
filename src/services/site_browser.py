"""On-demand, bounded pywebview page inspection. No credentials or JS API exposed."""
import threading
import time
import uuid

SNAPSHOT = """(() => ({
 title: document.querySelector('h1')?.textContent || document.title,
 thumbnail: document.querySelector('meta[property="og:image"]')?.content || '',
 embeds: Array.from(document.querySelectorAll('iframe')).map(e => e.getAttribute('data-src') || e.getAttribute('src')).filter(Boolean)
}))()"""


class BrowserRequired(ValueError):
    def __init__(self, token):
        super().__init__('Sayfa kullanıcı doğrulaması veya etkileşim bekliyor. Tarayıcıda devam edip tekrar kontrol edin.')
        self.token = token


class SiteBrowser:
    def __init__(self):
        self.lock = threading.RLock()
        self.session = None
        self.enabled = False

    def inspect(self, url):
        import webview
        if not self.enabled or not webview.windows:
            raise ValueError('Bu sayfa için masaüstü uygulamasındaki tarayıcı desteği gerekiyor.')
        with self.lock:
            session = self.session
            if session and session['url'] != url:
                raise ValueError('Önce açık olan site incelemesini tamamlayın veya iptal edin.')
            if not session:
                session = {'url': url, 'token': uuid.uuid4().hex, 'loaded': threading.Event(), 'closed': False}
                self.session = session
                try:
                    window = webview.create_window('Video Downloader Pro · Kaynak inceleme', url,
                        hidden=True, focus=False, width=1000, height=760, js_api=None)
                    session['window'] = window
                    window.events.loaded += lambda: session['loaded'].set()
                    window.events.closed += lambda: self._closed(session)
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
                            target['result'] = session['window'].evaluate_js(SNAPSHOT)
                        except Exception:
                            pass
                        finally:
                            target['done'].set()
                    threading.Thread(target=evaluate, daemon=True).start()
                pending['done'].wait(.5)
                if pending['done'].is_set():
                    result = pending['result']
                    session['evaluation'] = None
                    if isinstance(result, dict) and result.get('embeds'):
                        self.close(session['token'])
                        return result
            time.sleep(.75)
        raise BrowserRequired(session['token'])

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
