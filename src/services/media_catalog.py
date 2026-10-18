"""Bounded playlist previews and single-use, server-owned download plans."""
import copy
import threading
import time
import uuid
from urllib.parse import urlsplit

from services.download_store import media_key
from services.source_quality import source_qualities


def estimate_size(info):
    formats = info.get('requested_formats') or [info]
    values = [item.get('filesize') or item.get('filesize_approx') for item in formats]
    return int(sum(values)) if values and all(isinstance(value, (int, float)) and value > 0 for value in values) else None


class MediaCatalog:
    def __init__(self):
        self.lock = threading.RLock()
        self.cache = {}
        self.previews = {}
        self.plans = {}

    def remember(self, url, info):
        with self.lock:
            self._prune()
            if len(self.cache) >= 1000:
                self.cache.pop(next(iter(self.cache)))
            self.cache[url] = (time.monotonic(), {'url': url, 'title': info.get('title') or 'Video',
                'thumbnail': info.get('thumbnail') or '', 'media_key': media_key(url, info),
                'total_bytes': estimate_size(info), 'duration': info.get('duration'),
                'is_playlist': info.get('entries') is not None,
                'video_qualities': source_qualities(info) if info.get('entries') is None else []})

    def lookup(self, url):
        with self.lock:
            entry = self.cache.get(url)
            if entry and time.monotonic() - entry[0] < 900:
                return copy.deepcopy(entry[1])
        return {'url': url, 'media_key': media_key(url)}

    def _prune(self):
        now = time.monotonic()
        self.previews = {key: value for key, value in self.previews.items() if now - value['created'] < 900}
        self.plans = {key: value for key, value in self.plans.items() if now - value['created'] < 300}
        self.cache = {key: value for key, value in self.cache.items() if now - value[0] < 900}

    def preview(self, urls):
        with self.lock:
            self._prune()
            if any(item['status'] == 'checking' for item in self.previews.values()):
                raise ValueError('Önceki liste taramasının bitmesini bekleyin.')
            token = uuid.uuid4().hex
            self.previews[token] = {'created': time.monotonic(), 'status': 'checking', 'source_urls': urls[:], 'entries': []}
            threading.Thread(target=self._preview, args=(token, urls[:]), daemon=True).start()
            return token

    def _preview(self, token, urls):
        try:
            from yt_dlp import YoutubeDL
            entries, truncated = [], False
            with YoutubeDL({'quiet': True, 'extract_flat': 'in_playlist', 'noplaylist': False,
                            'lazy_playlist': True, 'playlistend': 2001,
                            'socket_timeout': 15, 'extractor_retries': 2}) as ydl:
                for url in urls:
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        raise ValueError('Liste bilgisi alınamadı.')
                    group = info.get('title') or 'Playlist'
                    raw_entries = info.get('entries')
                    is_playlist = raw_entries is not None
                    for entry in raw_entries if is_playlist else [info]:
                        if len(entries) >= 2000:
                            truncated = True
                            break
                        if not entry:
                            continue
                        target = entry.get('webpage_url') or entry.get('url') or (url if not is_playlist else '')
                        if target and not urlsplit(target).scheme and (entry.get('ie_key') or '').lower() == 'youtube':
                            target = 'https://www.youtube.com/watch?v=' + target
                        available = bool(target and urlsplit(target).scheme in ('http', 'https')
                                         and entry.get('availability') != 'private'
                                         and entry.get('title') not in ('[Deleted video]', '[Private video]'))
                        thumb = entry.get('thumbnail') or ''
                        if not thumb and entry.get('thumbnails'):
                            thumb = entry['thumbnails'][-1].get('url') or ''
                        entries.append({'id': uuid.uuid4().hex, 'url': target, 'title': entry.get('title') or 'Video',
                                        'thumbnail': thumb, 'group': group if is_playlist else '', 'available': available,
                                        'media_key': media_key(target, entry) if available else '',
                                        'total_bytes': estimate_size(entry), 'duration': entry.get('duration')})
            with self.lock:
                if token in self.previews:
                    self.previews[token].update(status='ready', entries=entries, truncated=truncated)
        except Exception as exc:
            with self.lock:
                if token in self.previews:
                    self.previews[token].update(status='error', message=str(exc))

    def preview_status(self, token):
        with self.lock:
            self._prune()
            if token not in self.previews:
                raise ValueError('Liste önizlemesi süresi dolmuş. Tekrar tarayın.')
            result = copy.deepcopy(self.previews[token])
            result.pop('created', None)
            return result

    def selected(self, token, identities, urls):
        preview = self.preview_status(token)
        if preview['status'] != 'ready' or preview['source_urls'] != urls:
            raise ValueError('Geçersiz liste önizlemesi.')
        if not isinstance(identities, list) or not identities or len(identities) != len(set(identities)):
            raise ValueError('En az bir video seçin.')
        allowed = {entry['id']: entry for entry in preview['entries'] if entry['available']}
        if any(identity not in allowed for identity in identities):
            raise ValueError('Seçilen öğe kullanılamıyor.')
        return [allowed[identity] for identity in identities]

    def plan(self, specs, options, source_urls=()):
        with self.lock:
            self._prune()
            if len(self.plans) >= 20:
                raise ValueError('Çok fazla bekleyen onay var. Birkaç dakika sonra tekrar deneyin.')
            token = uuid.uuid4().hex
            self.plans[token] = {'created': time.monotonic(), 'specs': copy.deepcopy(specs), 'options': copy.deepcopy(options), 'source_urls': list(source_urls)}
            return token

    def consume_plan(self, token):
        with self.lock:
            self._prune()
            if token not in self.plans:
                raise ValueError('İndirme onayının süresi dolmuş. Tekrar deneyin.')
            return self.plans.pop(token)
