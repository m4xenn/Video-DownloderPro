"""Bounded diagnostic sampling of yt-dlp formats; never writes media to disk."""
from urllib.parse import urljoin
from yt_dlp.networking import Request
from services.media_discovery import public_url
from services.source_validation import validate_media_sample


def sample_media(ydl, info, allowed=public_url):
    candidates=info.get('requested_formats') or info.get('formats') or [info]
    candidates=[f for f in candidates if f.get('url') and not f.get('has_drm') and f.get('vcodec')!='none']
    if not candidates:raise ValueError('No unprotected video format to sample')
    selected=candidates[-1]
    headers=selected.get('http_headers') or info.get('http_headers') or {}
    target=selected['url'];kind='direct'
    fragments=selected.get('fragments') or []
    if fragments:
        fragment=next((f for f in fragments if f.get('url') and f.get('duration')),None)
        fragment=fragment or next((f for f in fragments if f.get('url')),None)
        if fragment is None:raise ValueError('No fragment URL to sample')
        target=urljoin(selected.get('fragment_base_url') or target,fragment['url']);kind='dash-fragment'
    elif 'm3u8' in selected.get('protocol','') or '.m3u8' in target.split('?',1)[0]:
        kind='hls-segment'
        for level in range(4):
            if not allowed(target,resolve=True):raise ValueError('Non-public manifest URL')
            with ydl.urlopen(Request(target,headers=headers)) as response:
                if not allowed(response.url,resolve=True):raise ValueError('Non-public manifest redirect')
                body=response.read(256*1024+1);final=response.url
            if len(body)>256*1024:raise ValueError('Manifest exceeds diagnostic budget')
            if not body.lstrip(b'\xef\xbb\xbf \r\n\t').startswith(b'#EXTM3U'):raise ValueError('Invalid HLS manifest')
            text=body.decode('utf-8-sig')
            if '#EXT-X-KEY:' in text and 'METHOD=NONE' not in text:raise ValueError('Encrypted sample not inspected')
            uri=next((line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')),None)
            if not uri:raise ValueError('No HLS variant or segment')
            target=urljoin(final,uri)
            if '#EXT-X-STREAM-INF' not in text:break
        else:raise ValueError('Manifest nesting exceeds diagnostic budget')
    elif '.mpd' in target.split('?',1)[0]:
        raise ValueError('DASH format has no parsed fragments')
    if not allowed(target,resolve=True):raise ValueError('Non-public media sample URL')
    with ydl.urlopen(Request(target,headers=dict(headers,Range='bytes=0-16383'))) as response:
        if not allowed(response.url,resolve=True):raise ValueError('Non-public media redirect')
        sample=response.read(16384)
        validate_media_sample(sample,response.headers.get('Content-Type',''))
        return {'sample_bytes':len(sample),'sample_http_status':response.status,'sample_kind':kind,'sample_status':'passed'}
