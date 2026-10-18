"""Bounded, muted playback through known player controls; no verification clicks."""
import json
from services.media_discovery import DISCOVERY_SNAPSHOT, public_url
from services.player_controls import LAZY_PLAYER_GATES


def activation_document(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('verification') or snapshot.get('drm'):
        return None
    candidates = {}
    for player in (snapshot.get('players') or [])[:48]:
        document = player.get('document')
        area = float(player.get('area') or 0)
        if public_url(document) and area >= 6000:
            candidates[document] = max(area, candidates.get(document, 0))
    ranked = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    if not ranked or (len(ranked) > 1 and ranked[1][1] >= ranked[0][1] * .8):
        return None
    document, area = ranked[0]
    # Wait for a larger embedded player instead of starting a small parent ad.
    if any(frame.get('url') != document and float(frame.get('area') or 0) > area * 1.25
           for frame in (snapshot.get('embeds') or [])[:24]):
        return None
    return document


START_PLAYER = r"""(target => {
 const visited=new Set();
 const lazyGates=__LAZY_PLAYER_GATES__;
 function scan(win,depth=0) {
   if(depth>3 || visited.has(win)) return;
   visited.add(win);
   try {
     const doc=win.document;
     if(win.location.href===target) {
       const visible=e=>{const r=e.getBoundingClientRect();const s=win.getComputedStyle(e);return r.width>=100 && r.height>=60 && s.display!=='none' && s.visibility!=='hidden'};
       if(/just a moment|checking your browser|verify you are human|security verification/i.test(doc.title) ||
         [...doc.querySelectorAll('iframe[src*="captcha"],iframe[src*="challenges.cloudflare"],.g-recaptcha,.h-captcha,.cf-turnstile,input[type="password"]')].some(e=>{const r=e.getBoundingClientRect(),s=win.getComputedStyle(e);return r.width>0 && r.height>0 && s.display!=='none' && s.visibility!=='hidden'})) return;
       const containers=[...doc.querySelectorAll('video,.jwplayer,.video-js')].filter(visible);
       containers.sort((a,b)=>{const x=a.getBoundingClientRect(),y=b.getBoundingClientRect();return y.width*y.height-x.width*x.height});
       const container=containers[0];
       if(!container) {
         const gates=lazyGates(win);
         if(gates.length===1 && !gates[0].hasAttribute('data-vdp-started')) {
           gates[0].setAttribute('data-vdp-started','true');gates[0].click();
         }
         return;
       }
       if(containers.some(e=>e!==container && !container.contains(e) && !e.contains(container) &&
           e.getBoundingClientRect().width*e.getBoundingClientRect().height>=container.getBoundingClientRect().width*container.getBoundingClientRect().height*.8)) return;
       if(container.matches('.jwplayer')) {
         const p=win.jwplayer(container.id),item=p.getPlaylist()?.[0];
         if(item?.drm || item?.sources?.some(s=>s.drm)) return;
         p.setMute(true);p.play(true);return;
       }
       if(container.matches('.video-js') && win.videojs) {
         const p=win.videojs.getPlayer?.(container.id);if(!p || p.currentSource()?.keySystems) return;
         p.muted(true);Promise.resolve(p.play()).catch(()=>{});return;
       }
       if(container.matches('video') && !container.mediaKeys) {
         container.muted=true;Promise.resolve(container.play()).catch(()=>{});
       }
       return;
     }
     for(const frame of [...doc.querySelectorAll('iframe')].slice(0,12)) scan(frame.contentWindow,depth+1);
   } catch(_) {}
 }
 scan(window);
})""".replace('__LAZY_PLAYER_GATES__', LAZY_PLAYER_GATES)


def inspection_script(document=None):
    if not document:
        return DISCOVERY_SNAPSHOT
    return '(() => {' + START_PLAYER + '(' + json.dumps(document) + ');return ' + DISCOVERY_SNAPSHOT + ';})()'


PAUSE_PLAYBACK = r"""(() => {
 const visited=new Set();
 function pause(win,depth=0) {
   if(depth>3 || visited.has(win))return;visited.add(win);
   try {
     for(const video of [...win.document.querySelectorAll('video')].slice(0,8)) {video.muted=true;video.pause();}
     try {if(typeof win.jwplayer==='function')win.jwplayer().pause(true);}catch(_){}
     try {for(const p of win.videojs?.getAllPlayers?.()||[])p.pause();}catch(_){}
     for(const f of [...win.document.querySelectorAll('iframe')].slice(0,12))pause(f.contentWindow,depth+1);
   }catch(_){}
 }
 pause(window);return true;
})()"""
