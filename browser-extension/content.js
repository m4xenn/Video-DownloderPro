const encryptedVideos=new WeakSet();
document.addEventListener('encrypted',event=>{if(event.target instanceof HTMLMediaElement)encryptedVideos.add(event.target);},true);
// Inspect media only after the background worker confirms this is an app-owned tab.
setInterval(async()=>{
 try {
  const active=await chrome.runtime.sendMessage({type:'tracked'});if(!active)return;
  for(const v of document.querySelectorAll('video')){
   const r=v.getBoundingClientRect(),style=getComputedStyle(v);
   if(style.visibility==='hidden'||style.display==='none'||r.width<240||r.height<120||v.paused||(!Number.isFinite(v.duration)&&v.duration!==Infinity)||v.duration<60||v.closest('[role="advertisement"],[aria-label="Advertisement"],[aria-label="Reklam"],.ad-container,.jw-flag-ads'))continue;
   await chrome.runtime.sendMessage({type:'video',source:v.currentSrc,duration:Number.isFinite(v.duration)?v.duration:null,live:v.duration===Infinity,preview:!!v.closest('.alt-teaser-player,.teaser-player,[data-content-type="preview"]'),drm:encryptedVideos.has(v)&&!!v.mediaKeys,title:document.title});
  }
 }catch(_){}
},1500);
