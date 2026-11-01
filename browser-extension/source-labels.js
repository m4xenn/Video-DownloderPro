// Only actual HLS manifest declarations establish quality/track labels.
(() => {
 const keySystems={'com.apple.streamingkeydelivery':'FairPlay','com.widevine':'Widevine','com.widevine.alpha':'Widevine','urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed':'Widevine','com.microsoft.playready':'PlayReady','urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95':'PlayReady'};
 const attrs=line=>Object.fromEntries([...line.matchAll(/([A-Z0-9-]+)=("[^"]*"|[^,]*)/g)].map(m=>[m[1],m[2].replace(/^"|"$/g,'')]));
 function parse(text,base){
  if(typeof text!=='string'||text.length>65536)return null;
  const lines=text.replace(/^\uFEFF/,'').trim().split(/\r?\n/),tracks=[];let pending=null,duration=0,segments=0,ended=false,unknown=false,aes=false;const systems=new Set();
  if(lines[0].trim()!=='#EXTM3U')return null;
  const absolute=value=>{try{const u=new URL(value,base);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password?u.href:null;}catch{return null;}};
  for(const raw of lines){
   const line=raw.trim();if(tracks.length>=128)break;
   if(line.startsWith('#EXT-X-KEY:')||line.startsWith('#EXT-X-SESSION-KEY:')){
    const a=attrs(line),method=(a.METHOD||'').toUpperCase(),format=(a.KEYFORMAT||'identity').toLowerCase();
    if(method!=='NONE'){
     if(keySystems[format])systems.add(keySystems[format]);
     else if((a.URI||'').toLowerCase().startsWith('skd:'))systems.add('FairPlay');
     else if(method==='AES-128'&&format==='identity')aes=true;
     else unknown=true;
    }
   }
   if(line.startsWith('#EXT-X-STREAM-INF:')){pending=attrs(line);continue;}
   if(line.startsWith('#EXT-X-MEDIA:')){
    const a=attrs(line);if(['AUDIO','SUBTITLES'].includes(a.TYPE)&&a.URI){const url=absolute(a.URI);if(url&&url!==base)tracks.push({url,role:a.TYPE==='AUDIO'?'audio':'subtitles',language:(a.LANGUAGE||a.NAME||'').slice(0,40)});}continue;
   }
   if(line.startsWith('#EXTINF:')){const n=Number.parseFloat(line.slice(8));if(Number.isFinite(n)&&n>0)duration+=n;segments++;}
   if(line==='#EXT-X-ENDLIST')ended=true;
   if(pending&&line.trim()&&!line.startsWith('#')){
    const url=absolute(line.trim()),m=/^(\d{1,5})x(\d{1,5})$/.exec(pending.RESOLUTION||'');
    if(url&&url!==base)tracks.push({url,role:m?'video':'variant',height:m?Number(m[2]):null,bandwidth:Number(pending['AVERAGE-BANDWIDTH']||pending.BANDWIDTH)||null});
    pending=null;
   }
  }
  const video=tracks.filter(t=>!['audio','subtitles'].includes(t.role));
  return {protection:systems.size?'drm':unknown?'unknown':aes?'aes128':'clear',systems:[...systems],role:video.length?'master':segments?'media':'unknown',variantCount:video.length,tracks,duration:ended&&duration>0?Math.round(duration):null};
 }
 function describe(c,index,language='en'){
  const t=(key,values)=>VDPI18n.text(key,language,values);
  const host=new URL(c.url).hostname;
  if(c.manifest?.protection==='drm')return {index,host,label:'DRM · '+c.manifest.systems.join(', '),detail:t('protected'),disabled:true};
  if(c.manifest?.protection==='unknown')return {index,host,label:t('encrypted'),detail:t('encryptionUnknown'),disabled:true};
  if(c.role==='master')return {index,host,label:t('master'),detail:t('masterDetail',{count:c.variantCount}),recommended:true};
  if(c.role==='subtitles')return {index,host,label:t('subtitles'),detail:c.language||t('languageUnknown'),disabled:true};
  if(c.role==='audio')return {index,host,label:t('audio'),detail:c.language||t('languageUnknown'),recommended:false};
  const quality=c.height?`${c.height}p`:t('qualityUnknown');
  const duration=c.duration?` · ${Math.floor(c.duration/60)}:${String(c.duration%60).padStart(2,'0')}`:'';
  const rate=c.bandwidth?` · ${(c.bandwidth/1000000).toFixed(1)} Mbps`:'';
  const kind=c.kind==='dash'?'DASH':c.kind==='file'?t('video'):'HLS';
  return {index,host,label:c.height?`${quality} · ${t('video')}`:t('source',{kind,index:index+1}),detail:quality+rate+duration,recommended:false};
 }
 function canonical(candidates){
  if(candidates.length<2)return null;
  const nodes=new Map(candidates.map(c=>[c.url,c])),edges=new Map(candidates.map(c=>[c.url,(c.manifest?.tracks||[]).map(t=>t.url).filter(u=>nodes.has(u))]));
  const indegree=new Map([...nodes.keys()].map(u=>[u,0]));
  for(const children of edges.values())for(const child of new Set(children))indegree.set(child,indegree.get(child)+1);
  const ready=[...nodes.keys()].filter(u=>!indegree.get(u)),roots=[...ready];let visited=0;
  while(ready.length){const u=ready.pop();visited++;for(const child of new Set(edges.get(u)))if(indegree.set(child,indegree.get(child)-1).get(child)===0)ready.push(child);}
  if(visited!==nodes.size||roots.length!==1)return null;
  const root=nodes.get(roots[0]);return root.role==='master'&&!['drm','unknown'].includes(root.manifest?.protection)?root:null;
 }
 function apply(candidates,url,manifest){
  const own=candidates.find(c=>c.url===url);if(!own||!manifest)return;
  if(manifest.role==='master')Object.assign(own,{role:'master',variantCount:manifest.variantCount});
  if(manifest.duration)own.duration=manifest.duration;
  for(const track of manifest.tracks){const child=candidates.find(c=>c.url===track.url);if(child)Object.assign(child,track);}
 }
 globalThis.VDPSourceLabels={parse,describe,apply,canonical};
})();
