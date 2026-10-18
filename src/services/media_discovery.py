"""Site-independent media observations. No downloaded JavaScript is evaluated here."""
import ipaddress
import socket
from urllib.parse import urlsplit
from services.player_controls import LAZY_PLAYER_GATES


def public_url(url, resolve=False):
    if not isinstance(url, str) or len(url) > 8192 or any(c.isspace() for c in url):
        return False
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or '').lower().rstrip('.')
        if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
            return False
        if parsed.port not in (None, 80, 443) or '.' not in host:
            return False
        if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            if not resolve:
                return True
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)
    except (ValueError, TypeError, OSError):
        return False


# Read normal player APIs and the DOM, including accessible same-origin frames.
# Cross-origin frames are returned as a bounded traversal frontier, never bypassed.
DISCOVERY_SNAPSHOT = r"""(() => {
 const media=[], embeds=[], players=[]; let drm=false,verification=false; const visited=new Set();
 const lazyGates=__LAZY_PLAYER_GATES__;
 const absolute=(value,base)=>{try{return new URL(value,base).href}catch(_){return ''}};
 function scan(win,depth=0) {
   if(depth>3 || visited.has(win)) return;
   visited.add(win);
   try {
     const doc=win.document, base=doc.baseURI;
     const visible=e=>{const r=e.getBoundingClientRect();const s=win.getComputedStyle(e);return r.width>=100 && r.height>=60 && s.display!=='none' && s.visibility!=='hidden'};
     verification ||= /just a moment|checking your browser|verify you are human|security verification/i.test(doc.title) ||
       [...doc.querySelectorAll('iframe[src*="captcha"],iframe[src*="challenges.cloudflare"],.g-recaptcha,.h-captcha,.cf-turnstile,input[type="password"]')].some(e=>{const r=e.getBoundingClientRect(),s=win.getComputedStyle(e);return r.width>0 && r.height>0 && s.display!=='none' && s.visibility!=='hidden'});
     for(const e of [...doc.querySelectorAll('video,.jwplayer,.video-js')].slice(0,12)) {
       if(visible(e)) {const r=e.getBoundingClientRect();players.push({document:win.location.href,area:r.width*r.height});}
     }
     for(const e of lazyGates(win)) {const r=e.getBoundingClientRect();players.push({document:win.location.href,area:r.width*r.height,kind:'lazy-frame'});}
     for(const e of [...doc.querySelectorAll('canvas')].slice(0,8)) {
       if(visible(e)) {const r=e.getBoundingClientRect();players.push({document:win.location.href,area:r.width*r.height,kind:'canvas'});}
     }
     const add=(sources,group,area,duration,protectedMedia=false)=>{
       if(protectedMedia) drm=true;
       const urls=[...new Set(sources.map(v=>absolute(v,base)).filter(v=>/^https?:\/\//i.test(v)))];
       if(urls.length || protectedMedia) media.push({sources:urls.slice(0,12),group,area,duration:Number.isFinite(duration)?duration:0,drm:protectedMedia,document:win.location.href});
     };
     [...doc.querySelectorAll('video')].slice(0,8).forEach((video,i)=>{
       const rect=video.getBoundingClientRect();
       const area=Math.max(0,rect.width)*Math.max(0,rect.height);
       add([video.currentSrc || video.src,...[...video.querySelectorAll('source')].map(s=>s.src)].filter(Boolean),`video:${i}`,area,video.duration,Boolean(video.mediaKeys));
       if(!media.some(m=>m.document===win.location.href && m.group===`video:${i}`) && /^(blob:)/.test(video.currentSrc || ''))
         media.push({sources:[],group:`video:${i}`,area,duration:Number.isFinite(video.duration)?video.duration:0,document:win.location.href,blob:true});
     });
     try {
       if(typeof win.jwplayer==='function') {
         const player=win.jwplayer(),item=player.getPlaylist()?.[0],rect=player.getContainer()?.getBoundingClientRect();
         if(item) add([item.file,...(item.sources||[]).map(s=>s.file)].filter(Boolean),'jwplayer',Math.max(0,rect?.width||0)*Math.max(0,rect?.height||0),item.duration,Boolean(item.drm || (item.sources||[]).some(s=>s.drm)));
       }
     } catch(_) {}
     try {
       if(win.videojs?.getAllPlayers) for(const p of win.videojs.getAllPlayers().slice(0,8)) {
         const r=p.el().getBoundingClientRect();
         add((p.currentSources()||[]).map(s=>s.src),'videojs:'+p.id(),r.width*r.height,p.duration(),Boolean(p.currentSource()?.keySystems));
       }
     } catch(_) {}
     for(const frame of [...doc.querySelectorAll('iframe')].slice(0,12)) {
       const rect=frame.getBoundingClientRect(),src=absolute(frame.getAttribute('data-src') || frame.getAttribute('src') || '',base);
       if(!frame.getAttribute('data-src') && !frame.getAttribute('src')) continue;
       if(rect.width<100 || rect.height<60 || /(?:doubleclick|googlesyndication|recaptcha|hcaptcha)/i.test(src)) continue;
       try {if(frame.contentWindow.document) scan(frame.contentWindow,depth+1)} catch(_) {}
       embeds.push({url:src,parent:win.location.href,area:rect.width*rect.height});
     }
   } catch(_) {}
 }
 scan(window);
 return {title:document.querySelector('h1')?.textContent || document.title,
   thumbnail:document.querySelector('meta[property="og:image"]')?.content || '',
   url:location.href,media,embeds,players,verification,drm,user_agent:navigator.userAgent,
   interaction:media.length>0 || Boolean(document.querySelector('[class*="jwplayer"],iframe[src*="captcha"],input[type="password"]')) ||
     [...document.querySelectorAll('button,[role="button"]')].slice(0,80).some(e=>/play|oynat|verify|doğrula/i.test(e.textContent+' '+e.getAttribute('aria-label'))) ||
     /just a moment|checking your browser|verify you are human/i.test(document.title)};
})()""".replace('__LAZY_PLAYER_GATES__', LAZY_PLAYER_GATES)


def choose_media(snapshot, network=()):
    """Choose one player, not a union of unrelated videos/advertisements.

    Network-only candidates need a matching blob video and matching Referer.
    Ambiguous candidates are left for the user to start the intended player.
    """
    if snapshot.get('drm'):
        raise ValueError('Bu oynatıcının kaynağı DRM korumalı.')
    from services.network_media import select_network_media
    selected=select_network_media(snapshot,list(network))
    if selected:return selected
    groups = []
    for record in (snapshot.get('media') or [])[:24]:
        if not isinstance(record, dict) or record.get('drm'):
            continue
        sources = list(dict.fromkeys(s for s in record.get('sources', []) if public_url(s)))[:8]
        if not sources and record.get('blob'):
            matching = [item for item in network if item.get('headers', {}).get('Referer', '').split('#')[0] == record.get('document', '').split('#')[0]]
            # Multiple network manifests may be pre-rolls or separate titles.
            urls = list(dict.fromkeys(item['url'] for item in matching if public_url(item.get('url'))))
            if len(urls) == 1:
                sources = urls
        if sources:
            groups.append((float(record.get('area') or 0), float(record.get('duration') or 0), sources, record))
    groups.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if not groups:
        return None
    best = groups[0]
    # A small pre-roll/advertisement on the parent document must not outrank a
    # larger embedded player whose video has not loaded yet.
    for frame in (snapshot.get('embeds') or [])[:24]:
        if isinstance(frame,dict) and public_url(frame.get('url')) and frame.get('url') != best[3].get('document') and float(frame.get('area') or 0)>best[0]*1.25:
            return None
    for other in groups[1:]:
        if set(best[2]).isdisjoint(other[2]) and other[0] >= best[0] * .8:
            return None
    headers = {}
    for source in best[2]:
        observed = next((item for item in reversed(network) if item.get('url') == source), {})
        headers[source] = dict(observed.get('headers') or {})
        headers[source].setdefault('Referer', best[3].get('document') or snapshot.get('url') or '')
        headers[source].setdefault('User-Agent', snapshot.get('user_agent') or '')
    return {'sources': best[2], 'source_headers': headers, 'document':best[3].get('document') or snapshot.get('url')}
