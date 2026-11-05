"""Verified YouTube DVR fragments, bounded parallel fetch, and one live HLS view.

No fragment is skipped. Only complete MP4 fragments reach the recorder. Source
URLs stay in memory and a tokenized loopback view preserves the existing FFmpeg
recording, stop, recovery and validation path.
"""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, urljoin
import math
import re
import secrets
import threading
import time

import requests
from core.bandwidth import DownloadPaused
from services.live_catchup import CatchupPlan

MAX_FRAGMENT_BYTES = 16 * 1024 * 1024
MAX_SEQUENCE = 100000
END_CHECK_SECONDS = 30


class DVRUnavailable(ValueError):
    """No bytes have reached an output: the normal source can still be used."""


class DVRFragmentError(ValueError):
    code = 'fragment_failed'
    def __init__(self):
        super().__init__('[fragment_failed] DVR fragment unavailable; temporary recording preserved.')


class _SourceError(ValueError):
    def __init__(self, status=0, retry_after=0):
        self.status = status
        self.retry_after = retry_after


def _fragment_url(base, sequence):
    parts = urlsplit(base)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query['sq'] = str(sequence)
    return urlunsplit(parts._replace(query=urlencode(query)))


def _mp4_fragment(body):
    """Each adaptive YouTube MP4 fragment must carry its own initialization."""
    boxes = set()
    position = 0
    while position + 8 <= len(body):
        size = int.from_bytes(body[position:position + 4], 'big')
        boxes.add(bytes(body[position + 4:position + 8]))
        if size == 0:
            position = len(body)
            break
        if size < 8 or position + size > len(body):
            return False
        position += size
    return position == len(body) and {b'ftyp', b'moov', b'moof', b'mdat'} <= boxes


def _selected(info):
    return info.get('requested_formats') or [info]


def prepare_youtube_dvr(ydl, info, url, cancelled=lambda: False):
    """Try an identity/quality-preserving from-start source before opening output."""
    if not info.get('is_live') or info.get('extractor_key') != 'Youtube':
        return info, None
    missing = object()
    def extract():
        saved = {key: ydl.params.get(key, missing) for key in ('live_from_start', 'format')}
        selector = ydl.format_selector
        try:
            ydl.params['live_from_start'] = True
            expression = saved['format'] if isinstance(saved['format'], str) else 'bestvideo+bestaudio/best'
            # Self-initialized MP4 fragments can share the existing native muxer.
            ydl.params['format'] = re.sub(
                r'\b(bestvideo|bestaudio)\b',
                lambda m: m[0] + ('[ext=mp4]' if m[0] == 'bestvideo' else '[ext=m4a]') +
                          '[protocol=http_dash_segments_generator]', expression)
            ydl.format_selector = ydl.build_format_selector(ydl.params['format'])
            candidate = ydl.extract_info(url, download=False)
            if not candidate or candidate.get('id') != info.get('id') or not candidate.get('is_live'):
                raise DVRUnavailable()
            formats = _selected(candidate)
            if len(formats) != 2 or any(f.get('protocol') != 'http_dash_segments_generator'
                    or f.get('ext') not in ('mp4', 'm4a') or f.get('has_drm') for f in formats):
                raise DVRUnavailable()
            old_video = next((f for f in _selected(info) if f.get('vcodec') not in (None, 'none')), {})
            new_video = next((f for f in formats if f.get('vcodec') not in (None, 'none')), {})
            if old_video.get('height') and old_video['height'] != new_video.get('height'):
                raise DVRUnavailable()
            if old_video.get('fps') and abs(float(old_video['fps']) - float(new_video.get('fps') or 0)) > .05:
                raise DVRUnavailable()
            return candidate
        finally:
            ydl.format_selector = selector
            for key, value in saved.items():
                if value is missing:
                    ydl.params.pop(key, None)
                else:
                    ydl.params[key] = value
    proxy = None
    try:
        if cancelled():
            raise DownloadPaused('DOWNLOAD_PAUSED')
        candidate = extract()
        formats = _selected(candidate)
        contexts = [{k: v for k, v in (f.get('http_headers') or candidate.get('http_headers') or {}).items()
                     if k in ('User-Agent', 'Referer', 'Origin')} for f in formats]
        proxy = DVRHistoryProxy(formats, contexts, cancelled,
                                refresh=lambda: _selected(extract()),
                                stream_status=lambda: _stream_status(ydl, info, url))
        proxy.prepare()
        return candidate, proxy
    except DownloadPaused:
        if proxy:
            proxy.close()
        raise
    except Exception:
        if proxy:
            proxy.close()
        # Only preparation failures fall back. An active DVR recording never
        # switches to the short HLS window or silently drops inaccessible pieces.
        return info, None


def _stream_status(ydl, original, url):
    """Metadata-only confirmation; a stalled connection is never proof of EOF."""
    try:
        info = ydl.extract_info(url, download=False, process=False)
        if not info or info.get('id') != original.get('id'):
            return None
        if info.get('live_status') in ('post_live', 'was_live'):
            return False
        if info.get('is_live') is True or info.get('live_status') == 'is_live':
            return True
    except Exception:
        pass
    return None


class DVRHistoryProxy:
    def __init__(self, formats, headers, cancelled=lambda: False, refresh=None, stream_status=None):
        self.formats = [dict(f) for f in formats]
        self.headers = headers
        self.cancelled = cancelled
        self.refresh = refresh
        self.stream_status = stream_status
        self.stop = threading.Event()
        self.lock = threading.RLock()
        self.refresh_lock = threading.Lock()
        self.local = threading.local()
        # Manifest handlers are short-lived threads. Their HTTP sessions must
        # be shared per rendition rather than retained once per reload forever.
        from services.secure_transport import pin_requests_session
        self.head_sessions = [pin_requests_session(requests.Session()) for _ in formats]
        self.head_locks = [threading.Lock() for _ in formats]
        self.sessions = list(self.head_sessions)
        self.heads = [-1] * len(formats)
        self.updated = [0.] * len(formats)
        self.changed = [time.monotonic()] * len(formats)
        self.delivered = [-1] * len(formats)
        self.pending_delivery = [set() for _ in formats]
        self.cache = [{} for _ in formats]
        self.pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix='youtube-dvr')
        self.server = None
        self.error = False
        self.refreshed = 0.
        self.checked_end = 0.
        self.ended = False

    def _check(self):
        if self.stop.is_set() or self.cancelled():
            raise DownloadPaused('DOWNLOAD_PAUSED')

    def _request(self, index, sequence=None):
        self._check()
        if sequence is None:
            with self.head_locks[index]:
                return self._read(index, sequence, self.head_sessions[index])
        if not hasattr(self.local, 'session'):
            from services.secure_transport import pin_requests_session
            self.local.session = pin_requests_session(requests.Session())
            with self.lock:
                self.sessions.append(self.local.session)
        return self._read(index, sequence, self.local.session)

    def _read(self, index, sequence, session):
        from services.media_discovery import public_url
        self._check()
        with self.lock:
            base = self.formats[index]['url']
            headers = dict(self.headers[index])
        if any('\r' in str(v) or '\n' in str(v) for v in headers.values()):
            raise _SourceError()
        original = base if sequence is None else _fragment_url(base, sequence)
        for attempt in range(3):
            self._check()
            url = original
            deadline = time.monotonic() + 12
            try:
                for _ in range(4):
                    self._check()
                    if not public_url(url, resolve=True):
                        raise _SourceError()
                    with session.request('HEAD' if sequence is None else 'GET', url,
                            headers=headers, stream=True, allow_redirects=False, timeout=(3, 3)) as response:
                        if response.status_code in (301, 302, 303, 307, 308):
                            url = urljoin(url, response.headers.get('Location', ''))
                            continue
                        if response.status_code != 200:
                            delay = 0
                            if response.status_code == 429:
                                try:
                                    delay = float(response.headers.get('Retry-After', '1'))
                                except ValueError:
                                    delay = 1
                                delay = min(5, max(1, delay)) if math.isfinite(delay) else 1
                            raise _SourceError(response.status_code, delay)
                        try:
                            head = int(response.headers['X-Head-Seqnum'])
                            if not 0 <= head <= MAX_SEQUENCE:
                                raise ValueError()
                        except (KeyError, ValueError):
                            raise _SourceError()
                        body = bytearray()
                        if sequence is not None:
                            for chunk in response.iter_content(65536):
                                self._check()
                                if time.monotonic() > deadline:
                                    raise _SourceError()
                                body.extend(chunk)
                                if len(body) > MAX_FRAGMENT_BYTES:
                                    raise _SourceError()
                            if not _mp4_fragment(body):
                                raise _SourceError()
                        with self.lock:
                            if head > self.heads[index]:
                                self.changed[index] = time.monotonic()
                            self.heads[index] = max(self.heads[index], head)
                            self.updated[index] = time.monotonic()
                        return bytes(body)
                raise _SourceError()
            except (requests.RequestException, _SourceError) as error:
                if isinstance(error, _SourceError) and error.status in (401, 403, 404, 410):
                    raise
                if attempt == 2:
                    raise _SourceError() from None
                delay = error.retry_after if isinstance(error, _SourceError) and error.status == 429 else .25 * (attempt + 1)
                if self.stop.wait(delay):
                    self._check()

    def _renewing_request(self, index, sequence=None):
        try:
            return self._request(index, sequence)
        except _SourceError as error:
            if error.status != 403 or not self.refresh:
                raise
            with self.refresh_lock:
                self._check()
                if time.monotonic() - self.refreshed > 30:
                    formats = self.refresh()
                    if [f.get('format_id') for f in formats] != [f.get('format_id') for f in self.formats]:
                        raise _SourceError()
                    with self.lock:
                        self.formats = [dict(f) for f in formats]
                    self.refreshed = time.monotonic()
            return self._request(index, sequence)

    def _fetch(self, index, sequence):
        return self._renewing_request(index, sequence)

    def _maybe_end(self):
        now = time.monotonic()
        with self.lock:
            if self.ended or not self.stream_status or now - max(self.changed) < END_CHECK_SECONDS:
                return
            if now - self.checked_end < END_CHECK_SECONDS:
                return
            self.checked_end = now
        # Serialize metadata extraction with URL renewal; yt-dlp has mutable
        # format-selection state. Unknown/error means keep waiting, never EOF.
        with self.refresh_lock:
            self._check()
            ended = self.stream_status() is False
            if ended:
                # Confirm the final head before freezing the playlist. The last
                # cached head can predate the actual end by many segments.
                for index in range(len(self.formats)):
                    self._request(index)
        if ended:
            with self.lock:
                self.ended = True

    def _delivered(self, index, sequence):
        with self.lock:
            if sequence <= self.delivered[index]:
                return
            pending = self.pending_delivery[index]
            pending.add(sequence)
            while self.delivered[index] + 1 in pending:
                self.delivered[index] += 1
                pending.remove(self.delivered[index])

    def remaining_seconds(self, now=None):
        # Presentation timestamps can jump inside a broadcast. Confirm catch-up
        # against actually delivered contiguous fragments, not just output time.
        with self.lock:
            return max(0, min(self.heads) - min(self.delivered)) * self.duration

    def prepare(self):
        observed = time.monotonic()
        durations = [float(f.get('target_duration') or 0) for f in self.formats]
        if len(durations) != 2 or any(not math.isfinite(d) or not 0 < d <= 30 for d in durations):
            raise DVRUnavailable()
        if abs(durations[0] - durations[1]) > .01:
            raise DVRUnavailable()
        self.duration = max(durations)
        # Verify sequence zero in both tracks. Do not assume an advertised DVR
        # generator means the beginning is actually retained or accessible.
        for index in range(len(self.formats)):
            body = self._request(index, 0)
            from concurrent.futures import Future
            future = Future()
            future.set_result(body)
            self.cache[index][0] = future
        self.plan = CatchupPlan((0, 0), (min(self.heads) + 1) * self.duration,
                                self.duration * 2, observed)
        return self.plan

    def _segment(self, index, sequence):
        self._check()
        with self.lock:
            if not 0 <= sequence <= min(self.heads):
                raise _SourceError()
            cache = self.cache[index]
            # Keep a small rewind window for FFmpeg probing and at most three
            # future pieces per input. One shared pool caps network concurrency.
            for old in list(cache):
                if old < sequence - 2 and cache[old].done():
                    del cache[old]
            for number in range(sequence, min(sequence + 3, min(self.heads) + 1)):
                if number not in cache:
                    cache[number] = self.pool.submit(self._fetch, index, number)
            future = cache[sequence]
        return future.result(timeout=45)

    def start(self):
        owner = self
        token = secrets.token_urlsafe(24)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                match = re.fullmatch('/' + token + r'/([01])(?:\.m3u8|/(\d+)\.mp4)', self.path)
                if not match or self.headers.get('Origin') or self.headers.get('Sec-Fetch-Site') is not None:
                    self.send_error(404)
                    return
                index = int(match[1])
                try:
                    owner._check()
                    if match[2] is None:
                        owner._maybe_end()
                        if not owner.ended and time.monotonic() - owner.updated[index] >= 2:
                            owner._renewing_request(index)
                        with owner.lock:
                            head = min(owner.heads)
                        rows = ['#EXTM3U', '#EXT-X-VERSION:7',
                                '#EXT-X-TARGETDURATION:' + str(math.ceil(owner.duration)),
                                '#EXT-X-MEDIA-SEQUENCE:0']
                        for sequence in range(head + 1):
                            rows.extend(('#EXTINF:' + str(owner.duration) + ',',
                                         f'/{token}/{index}/{sequence}.mp4'))
                        if owner.ended:
                            rows.append('#EXT-X-ENDLIST')
                        body = ('\n'.join(rows) + '\n').encode()
                        kind = 'application/vnd.apple.mpegurl'
                    else:
                        body = owner._segment(index, int(match[2]))
                        kind = 'video/mp4'
                    self.send_response(200)
                    self.send_header('Content-Type', kind)
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    if match[2] is not None:
                        owner._delivered(index, int(match[2]))
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception:
                    if not owner.stop.is_set():
                        owner.error = True
                    try:
                        self.send_error(502)
                    except OSError:
                        pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        return [f'http://127.0.0.1:{self.server.server_port}/{token}/{i}.m3u8'
                for i in range(len(self.formats))]

    def close(self):
        self.stop.set()
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.worker.join(2)
            self.server = None
        self.pool.shutdown(wait=False, cancel_futures=True)
        for session in self.sessions:
            session.close()
