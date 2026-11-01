importScripts('locales.js','source-labels.js');
const HOST='com.videodownloaderpro.bridge';
let port=null, busy=false, connected=false;
let language=VDPI18n.normalize(chrome.i18n?.getUILanguage?.())||'en';
const legacyStates={'Videoyu oynatın / Play the video':'play','Uygulamaya gönderildi / Sent to app':'sent','Bağlantı bekleniyor / Waiting for app':'waiting','Şifreli oynatma; lisans gerekebilir / Encrypted playback; license may be required':'encryptedState','Kaynak aranıyor; gerekirse eklentiden seçin / Inspecting source':'inspecting','Kaynak seçin / Choose source':'choose'};
const jobs=new Map();
const publicUrl=s=>{try{const u=new URL(s);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password&&!['localhost','127.0.0.1','[::1]'].includes(u.hostname);}catch{return false;}};
async function persist(){await chrome.storage.session.set({jobs:[...jobs],language});}
const ready=chrome.storage.session.get(['jobs','language']).then(s=>{language=VDPI18n.normalize(s.language)||language;for(const [k,v] of s.jobs||[])jobs.set(k,{...v,state:legacyStates[v.state]||v.state,autoPending:false});});
function exchange(message={type:'poll',extension_id:chrome.runtime.id,version:chrome.runtime.getManifest?.().version||''}){
 if(!port){
  port=chrome.runtime.connectNative(HOST);
  port.onDisconnect.addListener(()=>{void chrome.runtime.lastError;port=null;busy=false;connected=false;});
  port.onMessage.addListener(async reply=>{
   busy=false;await ready;
   if(reply.error){connected=false;return;}
   if(!Array.isArray(reply.jobs))return;
   connected=true;
   language=VDPI18n.normalize(reply.language)||language;
   const active=new Set(reply.jobs.map(j=>j.id));
   for(const [id,j] of jobs)if(!active.has(id)){jobs.delete(id);}
   for(const j of reply.jobs){
    if(jobs.has(j.id)){
     const tracked=jobs.get(j.id);tracked.sent=false;
     if((j.focus_seq||0)>(tracked.focus_seq||0)){
      tracked.focus_seq=j.focus_seq;
      try{await chrome.tabs.update(tracked.tab,{active:true});const tab=await chrome.tabs.get(tracked.tab);await chrome.windows.update(tab.windowId,{focused:true});}catch(_){}
     }
     continue;
    }
    if(!publicUrl(j.url))continue;
    const tab=await chrome.tabs.create({url:j.url,active:false});
    jobs.set(j.id,{...j,tab:tab.id,candidates:[],state:'play'});
   }
   await persist();
  });
 }
 busy=true;port.postMessage(message);
}
async function poll(){await ready;if(!busy)try{exchange();}catch{busy=false;port=null;connected=false;}}
setInterval(poll,1500);chrome.alarms.create('bridge',{periodInMinutes:.5});chrome.alarms.onAlarm.addListener(poll);poll();
chrome.webRequest.onHeadersReceived.addListener(async d=>{
 await ready;const j=[...jobs.values()].find(j=>j.tab===d.tabId);if(!j||d.statusCode<200||d.statusCode>=300||!publicUrl(d.url))return;
 const mime=(d.responseHeaders||[]).find(h=>h.name.toLowerCase()==='content-type')?.value||'';
 if(!/mpegurl|dash\+xml/i.test(mime))return;
 if(!j.candidates.some(c=>c.url===d.url)&&j.candidates.length<12){
  const candidate={url:d.url,kind:/dash\+xml/i.test(mime)?'dash':'hls',frame:d.frameId};
  j.candidates.push(candidate);
  for(const c of j.candidates)if(c.manifest)VDPSourceLabels.apply(j.candidates,c.url,c.manifest);
  void inspectManifest(j,candidate);
 }
 await persist();
},{urls:['http://*/*','https://*/*']},['responseHeaders']);
async function inspectManifest(j,c){
 if(typeof fetch!=='function')return;
 j.labelRequests=(j.labelRequests||0)+1;if(j.labelRequests>6)return;
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),4000);
 let reader;
 try{
  const r=await fetch(c.url,{credentials:'omit',redirect:'error',cache:'no-store',signal:controller.signal,referrerPolicy:'no-referrer'});
  if(!r.ok||!r.body){if(r.body)await r.body.cancel();return;}
  reader=r.body.getReader();const chunks=[];let bytes=0;
  while(true){const part=await reader.read();if(part.done)break;bytes+=part.value.byteLength;if(bytes>65536)return;chunks.push(part.value);}
  const buffer=new Uint8Array(bytes);let offset=0;for(const chunk of chunks){buffer.set(chunk,offset);offset+=chunk.length;}
  const manifest=VDPSourceLabels.parse(new TextDecoder().decode(buffer),r.url||c.url);
  if(manifest&&jobs.get(j.id)===j){c.manifest=manifest;VDPSourceLabels.apply(j.candidates,c.url,manifest);await persist();}
 }catch(_){}finally{clearTimeout(timer);if(reader)try{await reader.cancel();}catch(_){}}
}
async function send(j,c,title){
 if(j.sent||['drm','unknown'].includes(c.manifest?.protection))return;j.sent=true;j.state='sent';await persist();
 try{exchange({type:'result',id:j.id,page:j.url,source:c.url,kind:c.kind,preview:j.preview===true,title:title||'Video'});}catch{j.sent=false;busy=false;port=null;j.state='waiting';await persist();}
}
chrome.runtime.onMessage.addListener((m,s,reply)=>{
 (async()=>{await ready;const j=[...jobs.values()].find(j=>j.tab===s.tab?.id);
 const popup=!s.tab&&s.url===chrome.runtime.getURL('popup.html');
 if(['status','popup-status','focus','select'].includes(m.type)&&!popup){reply(false);return;}
 if(m.type==='tracked'){reply(!!j);return;}
 if(m.type==='status'||m.type==='popup-status'){
  const statuses=[...jobs.values()].map(j=>({id:j.id,state:VDPI18n.text(j.state,language)||VDPI18n.text('play',language),candidates:(j.playable&&!j.blocked?j.candidates:[]).map((c,i)=>VDPSourceLabels.describe(c,i,language))}));
  reply(m.type==='status'?statuses:{jobs:statuses,language,connected});return;
 }
 if(m.type==='focus'){const target=jobs.get(m.id);if(target){await chrome.tabs.update(target.tab,{active:true});const t=await chrome.tabs.get(target.tab);await chrome.windows.update(t.windowId,{focused:true});}reply(true);return;}
 if(m.type==='select'){const target=jobs.get(m.id);if(target?.playable&&!target.blocked&&target.candidates[m.index])await send(target,target.candidates[m.index]);reply(true);return;}
 if(m.type==='video'&&j){
  if(j.blocked){reply(false);return;}
  j.playable=true;j.preview=m.preview===true;
  if(m.drm){j.candidates=[];j.blocked=true;j.state='encryptedState';await persist();reply(false);return;}
  if(publicUrl(m.source)){await send(j,{url:m.source,kind:/\.m3u8(?:[?]|$)/i.test(m.source)?'hls':/\.mpd(?:[?]|$)/i.test(m.source)?'dash':'file'},m.title);}
  else {
   j.state='inspecting';await persist();
   if(!j.autoPending){j.autoPending=true;setTimeout(async()=>{
    j.autoPending=false;
    if(!jobs.has(j.id)||j.sent||j.blocked)return;
    const matches=j.candidates.filter(c=>c.frame===s.frameId);
    const canonical=VDPSourceLabels.canonical(matches);
    if(matches.length===1)await send(j,matches[0],m.title);
    else if(canonical)await send(j,canonical,m.title);
    else {j.state='choose';await persist();}
   },2500);}
  } // Only one observed HLS URL in the playing video's exact frame can be automatic.
 }
 reply(false);
 })().catch(()=>reply(false));return true;
});
