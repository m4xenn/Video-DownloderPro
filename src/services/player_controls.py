"""Shared DOM rules for a labelled play gate guarding a lazy video iframe."""
LAZY_PLAYER_GATES = r"""(win => {
 const result=[],doc=win.document;
 const visible=e=>{const r=e.getBoundingClientRect(),s=win.getComputedStyle(e);return r.width>=100 && r.height>=60 && s.display!=='none' && s.visibility!=='hidden'};
 for(const e of [...doc.querySelectorAll('[aria-label]')].slice(0,160)) {
   const label=(e.getAttribute('aria-label')||'').trim();
   if(!/^(?:play(?: (?:video|movie|film))?|oynat|videoyu oynat|filmi oynat|watch(?: (?:video|movie))?|filmi izle)$/i.test(label)) continue;
   if(!visible(e) || e.closest('a[href],form') || e.matches('input,button[type="submit"]')) continue;
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
 return result;
})"""
