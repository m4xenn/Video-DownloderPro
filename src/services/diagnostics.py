"""Bounded local diagnostics. Raw errors, URLs, headers and paths never persist."""
from datetime import datetime, timezone
from contextlib import closing
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import threading
import platform
from urllib.parse import urlsplit


MESSAGES = {
    'started': 'Operation started.', 'resolved': 'Media source resolved.',
    'finished': 'Download completed.', 'interaction_required': 'Browser interaction required.',
    'no_player': 'No usable player was detected before the inspection deadline.',
    'network_resolved': 'Media source correlated with a successful browser network response.',
    'source_refresh': 'Refreshing an expired or rejected source once before media download.',
    'source_mismatch': 'Refreshed source failed the video identity or format check.',
    'partial_preserved': 'Partial media was preserved; automatic source replacement was stopped.',
    'verification_required': 'A verification or login screen was detected.',
    'rate_limited': 'Server returned HTTP 429 (too many requests).',
    'access_denied': 'Server denied access (HTTP 401/403).',
    'not_found': 'Remote source not found (HTTP 404).',
    'fragment_failed': 'A video fragment could not be downloaded.',
    'local_file_missing': 'A local or temporary file could not be found.',
    'network_error': 'Connection failed or timed out.', 'unsupported': 'No supported media source was found.',
    'drm': 'Protected media detected.', 'unexpected': 'Operation failed; see the stage and error code.',
    'invalid_media': 'Embedded media metadata or playable formats could not be validated.',
}
STAGES = {'metadata', 'browser', 'playback', 'download', 'postprocess'}


def error_code(error):
    text = str(error).lower()
    for pattern, code in [
        (r'aynı video ve format', 'source_mismatch'),(r'kısmi dosya korundu', 'partial_preserved'),
        (r'\b429\b', 'rate_limited'), (r'\b(?:401|403)\b', 'access_denied'),
        (r'\b404\b', 'not_found'), (r'drm|widevine|playready', 'drm'),
        (r'doğrulaması|etkileşim bekliyor', 'interaction_required'),
        (r'kaynak doğrulanamadı|formatı doğrulanamadı|tekil medya kaynağı', 'invalid_media'),
        (r'no such file|filenotfounderror|winerror 2\b', 'local_file_missing'),
        (r'fragment|parça', 'fragment_failed'),
        (r'timeout|timed out|connection|network|name resolution', 'network_error'),
        (r'unsupported|no video|no formats|kaynağı bulunamadı|oynatıcısı bulunamadı', 'unsupported'),
    ]:
        if re.search(pattern, text): return code
    return 'unexpected'


def source_identity(url):
    """Keep a host and opaque correlation ID, never URL paths/query/userinfo."""
    try:
        host = urlsplit(url).hostname or ''
        host = host.encode('idna').decode('ascii').lower()
        if not re.fullmatch(r'[a-z0-9.-]{1,253}', host): host = ''
    except (ValueError, UnicodeError, TypeError):
        host = ''
    return host, hashlib.sha256(str(url).encode()).hexdigest()[:16]


class Diagnostics:
    def __init__(self, path=None, limit=300):
        folder = Path(os.environ.get('VIDEO_DOWNLOADER_DATA_DIR') or
                      Path(os.environ.get('APPDATA', str(Path.home()))) / 'YoutubePro')
        self.path = Path(path) if path else folder / 'diagnostics.sqlite3'
        self.limit = limit
        self.lock = threading.RLock()
        self.available = True

    def record(self, stage, url='', code=None, error=None):
        stage = stage if stage in STAGES else 'download'
        code = error_code(error) if error is not None else code
        code = code if code in MESSAGES else 'unexpected'
        host, source = source_identity(url)
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        try:
            with self.lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
                    db.execute('''CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY, first_at TEXT, last_at TEXT,
                        stage TEXT, host TEXT, source TEXT, code TEXT, count INTEGER)''')
                    last = db.execute('SELECT id,stage,source,code FROM events ORDER BY id DESC LIMIT 1').fetchone()
                    if last and last[1:] == (stage, source, code):
                        db.execute('UPDATE events SET last_at=?,count=count+1 WHERE id=?', (now, last[0]))
                    else:
                        db.execute('INSERT INTO events(first_at,last_at,stage,host,source,code,count) VALUES(?,?,?,?,?,?,1)',
                                   (now, now, stage, host, source, code))
                    db.execute('DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT ?)', (self.limit,))
                self.available = True
        except (OSError, sqlite3.Error):
            self.available = False  # Diagnostics must never interrupt the download.

    def report(self,url=None):
        events = []
        try:
            with self.lock:
                if self.path.exists():
                    with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
                        db.row_factory = sqlite3.Row
                        query='SELECT * FROM events'+(' WHERE source=?' if url is not None else '')+' ORDER BY id DESC LIMIT ?'
                        params=(source_identity(url)[1],self.limit) if url is not None else (self.limit,)
                        events = [dict(row) for row in db.execute(query,params)]
        except (OSError, sqlite3.Error):
            self.available = False
        # Construct export from explicit fields and fixed messages only.
        lines = ['Video Downloader Pro — diagnostic report (UTC)',
                 'URLs, titles, cookies, headers and local file paths are excluded.']
        try:
            from antigravity_config import CURRENT_VERSION
            from services.component_runtime import runtime_version
            lines.append(f'App: {CURRENT_VERSION} | Python: {platform.python_version()} | yt-dlp: {runtime_version()}')
        except (ImportError, OSError, ValueError):
            pass
        for event in events:
            lines.append(f"{event['last_at']} | {event['stage']} | {event['host']} | {event['source']} | "
                         f"{event['code']} x{event['count']} | {MESSAGES.get(event['code'], MESSAGES['unexpected'])}")
        return {'text': '\n'.join(lines), 'count': len(events), 'available': self.available}


class DiagnosticLogger:
    def __init__(self, stage, url, progress=None, warning_callback=None):
        self.stage, self.url, self.progress, self.warning_callback = stage, url, progress, warning_callback
    def debug(self, message):
        # yt-dlp reports fragment retry errors through to_screen/logger.debug.
        if isinstance(message,str) and '[download] Got error:' in message:self.warning(message)
    def warning(self, message):
        diagnostics.record(self.stage, self.url, error=message)
        if self.warning_callback:self.warning_callback(message)
        if self.progress and error_code(message)=='rate_limited':self.progress('waiting_server')
    def error(self, message): diagnostics.record(self.stage, self.url, error=message)


diagnostics = Diagnostics()
