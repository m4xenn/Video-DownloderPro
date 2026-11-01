"""Shared DOM rules for a labelled play gate guarding a lazy video iframe."""
AD_MEDIA_REGION = r"""(e => Boolean(e?.closest?.('[role="advertisement"],[aria-label="Advertisement"],[aria-label="Reklam"],.ad-container,.jw-flag-ads')))"""

LAZY_PLAYER_GATES = r"""(win => {
 const result=[],doc=win.document;
 const isAd=__AD_MEDIA_REGION__;
 const visible=e=>{const r=e.getBoundingClientRect(),s=win.getComputedStyle(e);return r.width>=100 && r.height>=60 && s.display!=='none' && s.visibility!=='hidden'};
 for(const e of [...doc.querySelectorAll('[aria-label]')].slice(0,160)) {
   const label=(e.getAttribute('aria-label')||'').trim();
   if(!/^(?:play(?: (?:video|movie|film))?|oynat|videoyu oynat|filmi oynat|watch(?: (?:video|movie))?|filmi izle)$/i.test(label)) continue;
   if(isAd(e) || !visible(e) || e.closest('a[href],form') || e.matches('input,button[type="submit"]')) continue;
   const r=e.getBoundingClientRect();if(r.width/r.height<.8 || r.width/r.height>3) continue;
   let parent=e.parentElement;
   for(let depth=0;parent && depth<3;depth++,parent=parent.parentElement) {
     const p=parent.getBoundingClientRect();if(p.width*p.height>r.width*r.height*4) break;
     const frames=[...parent.querySelectorAll('iframe[data-src]')].filter(f=>{
       const src=f.getAttribute('src')||'';
       const target=f.getAttribute('data-src')||'';
       try {const u=new URL(target,doc.baseURI);return (!src || src==='about:blank') && /^https?:$/.test(u.protocol) && !/captcha|doubleclick|googlesyndication/i.test(u.hostname)} catch(_) {return false}
     });
     if(frames.length===1) {result.push(e);break;}
   }
 }

 // Modern players may create their iframe only after a labelled poster button.
 // Require a single empty iframe in the same bounded player region; never click links.
 for(const e of [...doc.querySelectorAll('button,[role="button"]')].slice(0,100)) {
   if(isAd(e) || result.includes(e) || e.closest('a[href],form') || e.matches('input,button[type="submit"]')) continue;
   const label=(e.getAttribute('aria-label')||e.textContent||'').trim().replace(/\s+/g,' ');
   const exact=/^(?:play(?: (?:video|movie|film))?|oynat|videoyu oynat|filmi oynat|watch(?: (?:video|movie))?|filmi izle)$/i.test(label);
   const named=label.match(/^(?:play|watch)\s+(.+?)\s+(?:episode|movie|film|video)\s*\d*$/i);
   if(!exact && !(named && named[1].length>=3 && doc.title.toLowerCase().includes(named[1].toLowerCase()))) continue;
   const r=e.getBoundingClientRect(),style=win.getComputedStyle(e);
   if(r.width<32 || r.height<32 || style.display==='none' || style.visibility==='hidden') continue;
   let parent=e.parentElement;
   for(let depth=0;parent && depth<4;depth++,parent=parent.parentElement) {
     if(/^(?:BODY|HTML|MAIN|FORM)$/.test(parent.tagName||'')) break;
     const p=parent.getBoundingClientRect(),area=p.width*p.height;
     if(p.width<200 || p.height<120 || area>1200000) continue;
     const frames=[...parent.querySelectorAll('iframe')];if(frames.length!==1) continue;
     const frame=frames[0],src=(frame.getAttribute('src')||'').trim();
     if(src && src!=='about:blank') continue;
     const target=frame.getAttribute('data-src');
     if(target) {try {const u=new URL(target,doc.baseURI);if(!/^https?:$/.test(u.protocol)||/captcha|doubleclick|googlesyndication/i.test(u.hostname))continue;} catch(_){continue;}}
     else if(e.tagName!=='BUTTON') continue;
     const x=r.left+r.width/2,y=r.top+r.height/2;
     if(x<p.left+p.width*.2 || x>p.left+p.width*.8 || y<p.top+p.height*.15 || y>p.top+p.height*.85) continue;
     e.__vdpPlayerArea=area;result.push(e);break;
   }
 }

 // Some lazy iframe posters expose their play symbol visually rather than by aria-label.
 // Match a direct image + SVG poster to the page title and a sole explicit lazy iframe.
 const heading=(doc.querySelector?.('h1')?.textContent||doc.title||'').toLowerCase().replace(/\s+/g,' ').trim();
 for(const e of [...doc.querySelectorAll('div')].slice(0,240)) {
   if(isAd(e) || result.includes(e) || !visible(e) || e.closest('a[href],form,[role="advertisement"],[aria-label="Reklam"]'))continue;
   const children=[...e.children],image=children.find(c=>c.tagName==='IMG')||children.find(c=>c.tagName==='PICTURE')?.querySelector('img');
   if(!image || !children.some(c=>c.tagName.toLowerCase()==='svg'))continue;
   const label=(image.alt||'').trim().toLowerCase().replace(/\s+/g,' ');
   if(label.length<5 || !heading.includes(label) || win.getComputedStyle(e).cursor!=='pointer')continue;
   const r=e.getBoundingClientRect();if(r.width/r.height<.8 || r.width/r.height>3)continue;
   const parent=e.parentElement;if(!parent || /^(BODY|HTML|MAIN)$/.test(parent.tagName))continue;
   const p=parent.getBoundingClientRect();if(p.width*p.height>r.width*r.height*2)continue;
   const frames=[...parent.querySelectorAll('iframe')];if(frames.length!==1)continue;
   const frame=frames[0],src=frame.getAttribute('src')||'',target=frame.getAttribute('data-src')||'';
   if(src && src!=='about:blank')continue;
   try{const u=new URL(target,doc.baseURI);if(!target||!/^https?:$/.test(u.protocol)||/captcha|doubleclick|googlesyndication/i.test(u.hostname))continue;}catch(_){continue;}
   result.push(e);
 }
 return result;
})""".replace('__AD_MEDIA_REGION__', AD_MEDIA_REGION)
