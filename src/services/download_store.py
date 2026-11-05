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
                if 'track_options' not in {row[1] for row in connection.execute('PRAGMA table_info(history)')}:
                    connection.execute("ALTER TABLE history ADD COLUMN track_options TEXT NOT NULL DEFAULT '{}'")
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
                    (id,media_key,url,title,thumbnail,format,quality,embed_subs,path,size,completed_at,track_options)
                    VALUES (:id,:media_key,:url,:title,:thumbnail,:format,:quality,:embed_subs,:path,:size,:completed_at,:track_options)''', dict(record, track_options=record.get('track_options', '{}')))
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

    def history_track_state(self, identity):
        if not self.path.exists():return {}
        with self.connection() as connection:
            row=connection.execute('SELECT track_options FROM history WHERE id=?',(identity,)).fetchone()
            return json.loads(row[0]) if row else {}

    def update_history_track_state(self, identity, fields):
        if set(fields)-{'recording_parts','session_exports'}:raise ValueError('Invalid recording metadata.')
        with self.connection(True) as connection:
            row=connection.execute('SELECT track_options FROM history WHERE id=?',(identity,)).fetchone()
            if not row:raise ValueError('History entry missing.')
            data=json.loads(row[0]);data.update(fields)
            connection.execute('UPDATE history SET track_options=? WHERE id=?',(json.dumps(data),identity))

    @staticmethod
    def _public(row):
        record = dict(row)
        tracks = json.loads(record.pop('track_options', '{}'))
        record['live_record_minutes']=tracks.get('live_record_minutes')
        record['video_container']=tracks.get('video_container','mp4')
        record['quality_summary']=tracks.get('quality_summary',{})
        record['workflow_summary']=tracks.get('workflow_summary',{})
        record['recording_parts_count']=sum(1 for p in tracks.get('recording_parts',[]) if isinstance(p,dict) and p.get('state') in ('recording','interrupted','captured') and isinstance(p.get('bytes'),(int,float)) and p['bytes']>0)
        record['recording_archive']=bool(tracks.get('recording_archive'))
        record.update(audio_language=tracks.get('audio_language', 'auto'), subtitle_language=tracks.get('subtitle_language', 'all'))
        record['file_exists'] = not record['recording_archive'] and Path(record['path']).is_file()
        record['embed_subs'] = bool(record['embed_subs'])
        return record

    def duplicates(self, key, url, options):
        if options.get('live_record_minutes'):return []
        if not self.path.exists():
            return []
        with self.connection() as connection:
            rows = connection.execute('''SELECT * FROM history WHERE (media_key=? OR url=?)
                AND format=? AND quality=? AND embed_subs=? ORDER BY completed_at DESC''',
                (key, url, options['format'], options['quality'], bool(options.get('embed_subs')))).fetchall()
            return [self._public(row) for row in rows if Path(row['path']).is_file() and not self._public(row)['recording_archive']
                    and all(self._public(row)[key] == options.get(key, default)
                            for key, default in [('audio_language', 'auto'), ('subtitle_language', 'all'),('video_container','mp4')])]


def completion_record(job):
    path = Path(job.output_path)
    return {'id': job.id, 'media_key': job.media_key or media_key(job.url), 'url': job.url,
            'title': job.title, 'thumbnail': job.thumbnail, 'format': job.options['format'],
            'quality': job.options['quality'], 'embed_subs': bool(job.options.get('embed_subs')),
            'path': str(path.resolve()), 'size': path.stat().st_size,
            'track_options': json.dumps(dict({key: job.options.get(key, default) for key, default in [('audio_language', 'auto'), ('subtitle_language', 'all'),('video_container','mp4')]},live_record_minutes=job.options.get('live_record_minutes') if getattr(job,'is_live',False) else None,quality_summary=getattr(job,'quality_summary',{}),workflow_summary=getattr(job,'workflow',{}),recording_parts=getattr(job,'recording_parts',[]),session_exports=getattr(job,'session_exports',{}))),
            'completed_at': datetime.now(timezone.utc).isoformat()}


def recording_archive_record(job):
    from services.recording_sessions import recoverable_parts
    from services.ui_messages import message
    parts=recoverable_parts(job)
    return {'id':job.id,'media_key':job.media_key or media_key(job.url),'url':job.url,
        'title':job.title+' ['+message('session.parts',count=len(parts))+']','thumbnail':job.thumbnail,
        'format':'video','quality':job.options.get('quality','max'),'embed_subs':False,
        'path':str((Path(job.path)/('recording-archive-'+job.id+'.mkv')).resolve()),'size':sum(p.get('bytes',0) for p in parts),
        'completed_at':datetime.now(timezone.utc).isoformat(),
        'track_options':json.dumps({'recording_archive':True,'recording_parts':job.recording_parts,'session_exports':job.session_exports,'video_container':'mkv',
                                   'live_record_minutes':job.options.get('live_record_minutes'),'quality_summary':job.quality_summary})}
