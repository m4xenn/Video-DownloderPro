"""Transactional local queue/history containing URLs and paths, not media bytes/cookies."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit


def media_key(url, info=None):
    if info and info.get('id'):
        extractor = info.get('extractor_key') or info.get('extractor') or info.get('ie_key')
        if extractor and str(extractor).lower() != 'generic':
            return f'{str(extractor).lower()}:{info["id"]}'
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower().removeprefix('www.')
    query = parse_qs(parsed.query)
    if host in ('youtube.com', 'm.youtube.com', 'youtu.be', 'music.youtube.com'):
        identity = query.get('v', [None])[0]
        if host == 'youtu.be':
            identity = parsed.path.strip('/').split('/')[0]
        elif parsed.path.startswith(('/shorts/', '/embed/', '/live/')):
            identity = parsed.path.split('/')[2]
        if identity:
            return 'youtube:' + identity
    clean = [(key, value) for key, values in sorted(query.items())
             if not key.startswith('utm_') and key not in ('fbclid', 'gclid') for value in values]
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, urlencode(clean), ''))


class DownloadStore:
    def __init__(self, path=None):
        folder = Path(os.environ.get('VIDEO_DOWNLOADER_DATA_DIR') or (Path(os.environ.get('APPDATA', str(Path.home()))) / 'YoutubePro'))
        self.path = Path(path) if path else folder / 'downloads.sqlite3'
        self.path = self.path.resolve()
        self.read_error = ''

    @contextmanager
    def connection(self, write=False):
        if write:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=10)
        else:
            connection = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            if write:
                connection.execute('PRAGMA journal_mode=WAL')
                connection.execute('CREATE TABLE IF NOT EXISTS state (name TEXT PRIMARY KEY, payload TEXT NOT NULL)')
                connection.execute('''CREATE TABLE IF NOT EXISTS history (
                    id TEXT PRIMARY KEY, media_key TEXT NOT NULL, url TEXT NOT NULL,
                    title TEXT NOT NULL, thumbnail TEXT NOT NULL, format TEXT NOT NULL,
                    quality TEXT NOT NULL, embed_subs INTEGER NOT NULL, path TEXT NOT NULL,
                    size INTEGER, completed_at TEXT NOT NULL)''')
                connection.execute('CREATE INDEX IF NOT EXISTS history_match ON history(media_key, format, quality, embed_subs)')
            yield connection
            if write:
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _state(self, name, default):
        if not self.path.exists():
            return default
        with self.connection() as connection:
            row = connection.execute('SELECT payload FROM state WHERE name=?', (name,)).fetchone()
            return json.loads(row['payload']) if row else default

    def load_queue(self):
        return self._state('queue', [])

    def load_drafts(self):
        return self._state('drafts', [])

    def save_drafts(self, entries):
        with self.connection(True) as connection:
            connection.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('drafts', json.dumps(entries)))

    def commit_queue(self, jobs, completed=(), clear_drafts=()):
        if self.read_error:
            raise ValueError(self.read_error)
        with self.connection(True) as connection:
            connection.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('queue', json.dumps(jobs)))
            for record in completed:
                connection.execute('''INSERT OR IGNORE INTO history
                    VALUES (:id,:media_key,:url,:title,:thumbnail,:format,:quality,:embed_subs,:path,:size,:completed_at)''', record)
            if clear_drafts:
                row = connection.execute("SELECT payload FROM state WHERE name='drafts'").fetchone()
                drafts = json.loads(row['payload']) if row else []
                drafts = [entry for entry in drafts if entry['url'] not in clear_drafts]
                connection.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('drafts', json.dumps(drafts)))

    def history(self, query='', offset=0, limit=50):
        if not self.path.exists():
            return {'items': [], 'total': 0}
        with self.connection() as connection:
            values = ('%' + query + '%', '%' + query + '%')
            total = connection.execute('SELECT COUNT(*) FROM history WHERE title LIKE ? OR url LIKE ?', values).fetchone()[0]
            rows = connection.execute('''SELECT * FROM history WHERE title LIKE ? OR url LIKE ?
                ORDER BY completed_at DESC LIMIT ? OFFSET ?''', (*values, limit, offset)).fetchall()
            return {'items': [self._public(row) for row in rows], 'total': total}

    def get_history(self, identity):
        if not self.path.exists():
            return None
        with self.connection() as connection:
            row = connection.execute('SELECT * FROM history WHERE id=?', (identity,)).fetchone()
            return self._public(row) if row else None

    @staticmethod
    def _public(row):
        record = dict(row)
        record['file_exists'] = Path(record['path']).is_file()
        record['embed_subs'] = bool(record['embed_subs'])
        return record

    def duplicates(self, key, url, options):
        if not self.path.exists():
            return []
        with self.connection() as connection:
            rows = connection.execute('''SELECT * FROM history WHERE (media_key=? OR url=?)
                AND format=? AND quality=? AND embed_subs=? ORDER BY completed_at DESC''',
                (key, url, options['format'], options['quality'], bool(options.get('embed_subs')))).fetchall()
            return [dict(row) for row in rows if Path(row['path']).is_file()]


def completion_record(job):
    path = Path(job.output_path)
    return {'id': job.id, 'media_key': job.media_key or media_key(job.url), 'url': job.url,
            'title': job.title, 'thumbnail': job.thumbnail, 'format': job.options['format'],
            'quality': job.options['quality'], 'embed_subs': bool(job.options.get('embed_subs')),
            'path': str(path.resolve()), 'size': path.stat().st_size,
            'completed_at': datetime.now(timezone.utc).isoformat()}
