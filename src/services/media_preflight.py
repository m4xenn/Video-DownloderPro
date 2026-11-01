"""Bounded public MP4 structural checks; never equate a header with full playback."""
import hashlib
import re
import struct
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from yt_dlp.networking import Request

def public_url(*args,**kwargs):
    from services.media_discovery import public_url as check
    return check(*args,**kwargs)


class NonPublicMediaError(ValueError):
    code='invalid_media'
    def __init__(self):super().__init__('[invalid_media] Non-public media source or redirect; transfer stopped.')


class PartialSourceError(ValueError):
    code = 'partial_source'
    def __init__(self):
        super().__init__('[partial_source] Source exposes only a truncated recording or preview; full download stopped.')


def inspect_mp4(read, total, max_boxes=24):
    """read(offset, count) is bounded and must return bytes at exactly offset."""
    first = read(0, min(32768, total))
    if len(first) < 8 or first[4:8] != b'ftyp':
        return {'status': 'unknown'}
    def get(offset, count):
        return first[offset:offset+count] if offset+count <= len(first) else read(offset, count)
    offset = 0
    duration = None
    for _ in range(max_boxes):
        if offset == total:
            return {'status': 'container_checked', 'available_bytes': total, 'duration': duration}
        if total-offset < 8:
            return {'status': 'partial', 'available_bytes': total}
        header = get(offset, min(16, total-offset))
        if len(header) < 8:
            raise ValueError('Short range response')
        size, kind = struct.unpack('>I4s', header[:8]); minimum = 8
        if size == 1:
            if len(header) < 16:
                return {'status': 'partial', 'available_bytes': total}
            size = struct.unpack('>Q', header[8:16])[0]; minimum = 16
        elif size == 0:
            size = total-offset
        if size < minimum:
            raise ValueError('Invalid MP4 box')
        if offset+size > total:
            return {'status': 'partial', 'available_bytes': total, 'declared_bytes': offset+size, 'duration': duration}
        if kind == b'moov' and duration is None:
            # mvhd is normally first, but do not depend on child ordering.
            child = offset+minimum
            for _ in range(16):
                if child+8 > offset+size: break
                raw = get(child, min(40, offset+size-child))
                length, tag = struct.unpack('>I4s', raw[:8])
                if length < 8 or child+length > offset+size: break
                if tag == b'mvhd' and len(raw) >= 28:
                    version = raw[8]
                    if version == 0:
                        scale, ticks = struct.unpack('>II', raw[20:28])
                    elif version == 1 and len(raw) >= 40:
                        scale = struct.unpack('>I', raw[28:32])[0]
                        ticks = struct.unpack('>Q', raw[32:40])[0]
                    else: break
                    duration = ticks/scale if scale else None
                    break
                child += length
        offset += size
    return {'status': 'unknown', 'available_bytes': total, 'duration': duration}


def probe_mp4(ydl, fmt, fallback_headers=None):
    url = fmt.get('url', '')
    if not public_url(url, resolve=True): raise NonPublicMediaError()
    headers = {k:v for k,v in (fmt.get('http_headers') or fallback_headers or {}).items() if k.lower() != 'range'}
    requests = 0
    total = None
    etag = None
    final_url = None
    def read(offset, count):
        nonlocal requests, total, etag, final_url
        from services.source_operation import current_operation
        operation=current_operation()
        if operation and operation.cancelled():
            from core.bandwidth import DownloadPaused
            raise DownloadPaused('DOWNLOAD_PAUSED')
        requests += 1
        if requests > 48 or not 0 < count <= 32768: raise ValueError('Preflight budget exceeded')
        with ydl.urlopen(Request(url, headers=dict(headers, Range=f'bytes={offset}-{offset+count-1}'))) as response:
            if not public_url(response.url, resolve=True): raise NonPublicMediaError()
            match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
            if response.status != 206 or not match or int(match[1]) != offset:
                raise ValueError('Server does not support verified range reads')
            length = int(match[3])
            if total is not None and length != total: raise ValueError('Source changed during inspection')
            total = length
            tag = response.headers.get('ETag')
            if final_url is not None and (response.url != final_url or tag != etag):
                raise ValueError('Representation changed during inspection')
            final_url, etag = response.url, tag
            return response.read(min(count, max(0, total-offset)))
    prefix = read(0, 32768)
    # Reuse the first response rather than requesting the same bytes twice.
    result = inspect_mp4(lambda start,count: prefix[start:start+count] if start+count <= len(prefix) else read(start,count), total)
    if etag and re.fullmatch(r'"[^"\r\n]+"', etag) and result['status'] == 'container_checked':
        parsed = urlsplit(final_url)
        volatile={'token','sig','signature','expires','expiry','exp','policy','key-pair-id'}
        query=[(k,v) for k,v in parse_qsl(parsed.query,keep_blank_values=True) if k.lower() not in volatile and not k.lower().startswith(('x-amz-','x-goog-'))]
        resource = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ''))
        result['representation'] = {'resource': hashlib.sha256(resource.encode()).hexdigest(),
                                    'etag': hashlib.sha256(etag.encode()).hexdigest(), 'size': total}
    return result


def preflight_media(ydl, info):
    if info.get('is_live'): return info
    formats = info.get('requested_formats') or [info]
    results = []
    for fmt in formats[:2]:
        if fmt.get('ext') not in ('mp4','m4a') or fmt.get('protocol', 'https') not in ('http','https') or not fmt.get('url'):
            continue
        try:
            result = probe_mp4(ydl, fmt, info.get('http_headers'))
        except Exception as error:
            from core.bandwidth import DownloadPaused
            if isinstance(error,(DownloadPaused,NonPublicMediaError)):raise
            result = {'status':'unknown'}
        fmt['_representation'] = result.get('representation')
        results.append(result)
        if result.get('duration') and not info.get('duration'): info['duration'] = result['duration']
    info['source_status'] = 'partial' if any(r['status']=='partial' for r in results) else 'container_checked' if results and all(r['status']=='container_checked' for r in results) else 'unknown'
    if info['source_status'] == 'partial': info['content_scope'] = 'preview'
    partial = next((r for r in results if r['status']=='partial'), {})
    info['source_available_bytes'] = partial.get('available_bytes')
    info['source_declared_bytes'] = partial.get('declared_bytes')
    return info
