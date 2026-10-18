"""Refresh at most once, before any partial media can be appended."""
from pathlib import Path
import re
import json
import math
import hashlib

EMBEDDED={'EmbeddedMedia','FullHDFilmizlesene'}


def forbidden(error):return bool(re.search(r'\b403\b',str(error)))


def same_media(before,after):
    if before.get('is_live') or after.get('is_live'):return False
    if not before.get('id') or before.get('id')!=after.get('id'):return False
    a,b=before.get('duration'),after.get('duration')
    if isinstance(a,bool) or isinstance(b,bool) or not isinstance(a,(int,float)) or not isinstance(b,(int,float)) or not math.isfinite(a) or not math.isfinite(b) or a<=0 or abs(a-b)>1:return False
    def signature(info):
        parts=info.get('requested_formats') or [info]
        return tuple(tuple(p.get(key) for key in ('height','width','fps','vcodec','acodec','ext','protocol','language','audio_channels','asr')) for p in parts)
    return before.get('extractor_key')==after.get('extractor_key') and signature(before)==signature(after)


def source_checkpoint(info):
    keys=('height','width','fps','vcodec','acodec','ext','protocol','language','audio_channels','asr')
    parts=info.get('requested_formats') or [info]
    return {'id':info.get('id'),'duration':info.get('duration'),'is_live':info.get('is_live',False),
        'extractor_key':info.get('extractor_key'),
        'requested_formats':[{key:part.get(key) for key in keys} for part in parts],
        '_source_urls':[hashlib.sha256(part['url'].encode()).hexdigest() for part in parts if part.get('url')]}


def can_resume_embedded(previous,info):
    current=source_checkpoint(info)
    return bool(previous and previous.get('_source_urls') and previous['_source_urls']==current['_source_urls'] and same_media(previous,info))


def template_has_partial(template):
    if isinstance(template,dict):template=template.get('default','')
    if not isinstance(template,str) or not template:return True
    path=template.replace('%(ext)s','mp4').replace('%%','%')
    return True if '%(' in path else has_partial(path)


def has_partial(filename):
    path=Path(filename);stem=path.stem
    for p in path.parent.iterdir():
        if not p.name.startswith(stem):continue
        if p.suffix=='.ytdl':
            try:
                if p.stat().st_size>32768:return True
                index=json.loads(p.read_text(encoding='utf-8'))['downloader']['current_fragment']['index']
                if type(index) is not int or index!=0:return True
            except (OSError,ValueError,KeyError,TypeError):return True
        elif ('.part' in p.name or p.name[len(stem):].startswith(('.f','.temp'))) and p.stat().st_size>0:return True
    return False


def refresh_source(ydl,url,extractor_key):
    from services.site_resolver import site_resolver
    from services.generic_resolver import generic_resolver
    resolver=site_resolver if extractor_key=='FullHDFilmizlesene' else generic_resolver
    with resolver.lock:
        resolver.cache.pop(url,None)
        resolver.pages.pop(url,None)
        if hasattr(resolver,'jobs'):resolver.jobs.pop(url,None)
    return resolver.extract(ydl,url,fresh=True)
