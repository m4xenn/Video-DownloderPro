"""Same-title cover links may open a separate watch state of the same page."""
WATCH_PAGE_LINKS = r"""(win => {
 const doc=win.document,current=new URL(win.location.href),links=[];
 const title=(doc.querySelector('h1')?.textContent||'').trim().toLowerCase().replace(/\s+/g,' ');
 if(title.length<8 || doc.querySelector('video,.jwplayer,.video-js')) return [];
 for(const a of [...doc.querySelectorAll('a[href]')].slice(0,200)) {
   if(a.closest('form,[role="advertisement"],[aria-label="Advertisement"],[aria-label="Reklam"]') || /sponsored|nofollow/i.test(a.rel||''))continue;
   const image=a.querySelector('img');if(!image)continue;
   const label=(image.alt||'').trim().toLowerCase().replace(/\s+/g,' ');
   if(!label.startsWith(title) || /trailer|download/i.test(a.textContent||''))continue;
   const r=a.getBoundingClientRect(),s=win.getComputedStyle(a);
   if(r.width<240 || r.height<120 || r.width/r.height>4 || s.display==='none' || s.visibility==='hidden')continue;
   try {
     const u=new URL(a.href,doc.baseURI);
     if(u.origin!==current.origin || u.pathname!==current.pathname || !u.search || u.search===current.search || u.username || u.password)continue;
     if(!links.includes(u.href))links.push(u.href);
   }catch(_){}
 }
 return links.length===1?links:[];
})"""
