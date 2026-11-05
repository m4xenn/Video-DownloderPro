"""Bounded DASH manifest parsing and protection classification before transfer."""
from services.safe_xml import parse_manifest
from urllib.parse import urljoin
from yt_dlp.networking import Request
from yt_dlp.extractor.generic import GenericIE
from services.hls_metadata import MAX_MANIFEST_BYTES, SYSTEMS, ProtectedMediaError, UnsupportedEncryptionError


def inspect_dash(body):
    if not isinstance(body, bytes) or len(body) > MAX_MANIFEST_BYTES:
        raise ValueError('DASH manifest exceeds metadata budget')
    if b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
        raise ValueError('DASH document declarations are not supported')
    root = parse_manifest(body)
    if root.tag.split('}')[-1] != 'MPD': raise ValueError('Invalid DASH manifest')
    systems = set(); unknown = False
    for item in root.iter():
        if item.tag.split('}')[-1] != 'ContentProtection': continue
        scheme = item.get('schemeIdUri','').lower()
        if scheme in SYSTEMS: systems.add(SYSTEMS[scheme])
        else: unknown = True
    return root, {'protection':'drm' if systems else 'unknown' if unknown else 'clear',
                  'systems':sorted(systems), 'is_live':root.get('type') == 'dynamic'}


def extract_dash(ydl, url, identity, title):
    from services.media_discovery import public_url
    if not public_url(url,resolve=True): raise ValueError('Non-public DASH source')
    headers = dict(ydl.params.get('http_headers') or {})
    with ydl.urlopen(Request(url,headers=headers)) as response:
        if not public_url(response.url,resolve=True): raise ValueError('Non-public DASH redirect')
        body=response.read(MAX_MANIFEST_BYTES+1); final=response.url
    root, evidence=inspect_dash(body)
    if evidence['protection']=='drm': raise ProtectedMediaError(evidence['systems'])
    if evidence['protection']=='unknown': raise UnsupportedEncryptionError()
    formats, subtitles=GenericIE(ydl)._parse_mpd_formats_and_subtitles(root,mpd_url=final,mpd_base_url=urljoin(final,'.'),mpd_id='dash')
    return {'id':identity,'title':title,'formats':formats,'subtitles':subtitles,
            'is_live':evidence['is_live'],'_dash_evidence':evidence}
