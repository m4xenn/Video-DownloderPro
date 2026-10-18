"""Check embedded metadata before presenting quality choices or downloading."""
import math
from urllib.parse import urlsplit


def validate_media_sample(body, content_type=''):
    """A bounded sample must not be an HTML/JSON access-error response."""
    mime = content_type.split(';')[0].strip().lower()
    prefix = body.lstrip(b'\xef\xbb\xbf \r\n\t').lower()
    if not body or mime in ('text/html','application/xhtml+xml','application/json') or prefix.startswith((b'<!doctype html',b'<html',b'<?xml')):
        raise ValueError('Medya parçası yerine boş veya medya dışı yanıt alındı; kaynak doğrulanamadı.')
    return len(body)


def validate_embedded_info(info):
    if not isinstance(info, dict) or info.get('_type') in ('playlist', 'multi_video'):
        raise ValueError('Oynatıcı geçerli bir tekil medya kaynağı vermedi.')
    if info.get('has_drm'):
        raise ValueError('Bu oynatıcının kaynağı DRM korumalı.')
    formats = info.get('formats') or info.get('requested_formats') or [info]
    playable = []
    for item in formats:
        if not isinstance(item, dict) or item.get('has_drm'):
            continue
        if item.get('vcodec') == item.get('acodec') == 'none':
            continue
        if item.get('ext') in ('jpg','jpeg','png','webp','gif','avif','svg','bmp','ico','mhtml') or item.get('protocol') == 'mhtml':
            continue
        try:
            parsed = urlsplit(item.get('url') or '')
            if parsed.scheme in ('http','https') and parsed.hostname:
                playable.append(item)
        except (ValueError, TypeError):
            continue
    if not playable:
        if formats and all(isinstance(item,dict) and item.get('has_drm') for item in formats):
            raise ValueError('Bu oynatıcının kaynağı DRM korumalı.')
        raise ValueError('Oynatıcıda kullanılabilir ses veya video formatı doğrulanamadı.')
    duration = info.get('duration')
    if duration is not None and not info.get('is_live'):
        if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration <= 0:
            raise ValueError('Oynatıcının medya süresi geçersiz; kaynak doğrulanamadı.')
    return info
