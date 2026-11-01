"""Bounded media response classification and player-correlated selection."""
from urllib.parse import urlsplit

HLS = {'application/vnd.apple.mpegurl','application/x-mpegurl','application/mpegurl','audio/mpegurl','audio/x-mpegurl'}


def media_kind(url, mime, status):
    if status not in (200,206): return None
    mime = (mime or '').split(';')[0].strip().lower()
    if mime in ('text/html','application/xhtml+xml','application/json'): return None
    try: path = urlsplit(url).path.lower()
    except ValueError: return None
    if mime in HLS:return 'hls'
    if path.endswith(('.ts','.m4s','.aac','.vtt','.jpg','.png')): return None
    if mime in HLS or path.endswith('.m3u8'): return 'hls'
    if mime == 'application/dash+xml' or path.endswith('.mpd'): return 'dash'
    filename = path.rsplit('/',1)[-1]
    if filename.startswith(('init.','init_','initialization')): return None
    if mime in ('video/mp4','video/webm','video/ogg','video/quicktime','video/x-matroska','video/x-flv') or path.endswith(('.mp4','.webm','.mov','.mkv','.ogv','.flv')): return 'file'
    return None


def document_key(url):
    return (url or '').split('#')[0]


def select_network_media(snapshot, network):
    from services.media_discovery import public_url
    if snapshot.get('drm') or snapshot.get('verification'): return None
    contexts = []
    for record in [*(snapshot.get('media') or []), *(snapshot.get('players') or [])][:72]:
        document = record.get('document') or snapshot.get('url')
        if not public_url(document): continue
        contexts.append({'document':document,'area':float(record.get('area') or 0),
                         'duration':float(record.get('duration') or 0), 'preview':bool(record.get('preview')),
                         'sources':{url for url in record.get('sources',[]) if public_url(url)}})
    candidates = {}
    for response in network[-80:]:
        source = response.get('url')
        if not public_url(source): continue
        kind = media_kind(source,response.get('mime'),response.get('status'))
        if not kind: continue
        documents=[document_key(response.get('document'))]
        if not response.get('document') or response.get('worker'):
            documents.append(document_key(response.get('headers',{}).get('Referer')))
        document=next((doc for doc in documents if any(document_key(context['document'])==doc and context['area']>=6000 for context in contexts)),None)
        if document is None:continue
        candidates.setdefault(document,{})[source] = dict(response,kind=kind)
    choices = []
    for context in contexts:
        sources=candidates.get(document_key(context['document']),{})
        if not sources or context['area']<6000:continue
        # Actual requests corroborating DOM player URLs are the strongest signal.
        exact = [source for source in sources if source in context['sources']]
        aliases=set()
        if exact:
            # Preserve a corroborated player's other configured quality variants.
            selected = [*exact,*sorted(context['sources']-set(exact))][:8]
        else:
            if context['sources']:continue
            known_elsewhere={source for other in contexts if other['sources'] and document_key(other['document'])==document_key(context['document']) for source in other['sources']}
            sources={source:item for source,item in sources.items() if source not in known_elsewhere}
            selected = list(sources)
            # Do not guess between pre-rolls, titles or unlinked rendition manifests.
            if len(selected) != 1:
                from services.manifest_relations import verified_hls_root
                root=verified_hls_root(sources)
                if not root:continue
                aliases=set(selected);selected=[root]
        choices.append((context['area'],context['duration'],context,selected,sources,aliases or set(selected)))
    choices.sort(key=lambda item:(item[0],item[1]),reverse=True)
    if not choices: return None
    area,_,context,selected,sources,aliases = choices[0]
    if any(other[0]>=area*.8 and other[5].isdisjoint(aliases) for other in choices[1:]): return None
    if any(other['area']>=area*.8 and other['sources'] and other['sources'].isdisjoint(aliases) for other in contexts):return None
    if any(other['area']>area*1.25 and not other['sources'].intersection(aliases) for other in contexts):return None
    if any(frame.get('url')!=context['document'] and float(frame.get('area') or 0)>area*1.25
           for frame in (snapshot.get('embeds') or [])): return None
    for other in choices[1:]:
        if document_key(other[2]['document'])==document_key(context['document']) and other[0]>=area*.8 and not other[5].isdisjoint(aliases):
            selected=list(dict.fromkeys([*selected,*(source for source in other[3] if source not in aliases)]))[:8]
            aliases.update(other[5])
            sources.update(other[4])
    headers={}
    for source in selected:
        headers[source]=dict(sources.get(source,{}).get('headers') or {})
        headers[source].setdefault('Referer',context['document'])
        headers[source].setdefault('User-Agent',snapshot.get('user_agent') or '')
    return {'content_scope':'preview' if context.get('preview') else 'unknown','sources':selected,'document':context['document'],'discovery_method':'network','source_headers':headers,'source_types':{source:'hls' for source in selected if sources.get(source,{}).get('body_hls')}}
