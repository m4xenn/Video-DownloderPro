const fs=require('fs'),vm=require('vm'),assert=require('assert');
(async()=>{
 let onNative,onMessage,onHeaders;const sent=[],tabs=[],metadataRequests=[],focused=[];let stored={};
 const fetch=async(url,options)=>{
  metadataRequests.push({url,options});
  const text=url.endsWith('/master')?'#EXTM3U\n#EXT-X-STREAM-INF:RESOLUTION=1428x804,BANDWIDTH=3200000\nvideo.m3u8\n':'#EXTM3U\n#EXTINF:10,\nsegment.ts\n#EXT-X-ENDLIST\n';
  let done=false;
  return {ok:true,url,body:{getReader:()=>({
   read:async()=>done?{done:true}:(done=true,{done:false,value:new TextEncoder().encode(text)}),
   cancel:async()=>{}
  })}};
 };
 const chrome={runtime:{getURL:p=>'chrome-extension://test/'+p,onMessage:{addListener:f=>onMessage=f},connectNative:()=>({onDisconnect:{addListener:()=>{}},onMessage:{addListener:f=>onNative=f},postMessage:m=>sent.push(m)})},
 storage:{session:{get:async()=>stored,set:async s=>{stored=s}}},alarms:{create:()=>{},onAlarm:{addListener:()=>{}}},
 tabs:{create:async o=>{tabs.push(o);return{id:7,windowId:2}},update:async(id,options)=>focused.push({id,options}),get:async()=>({windowId:2})},windows:{update:async()=>{}},webRequest:{onHeadersReceived:{addListener:f=>onHeaders=f}}};
 const context=vm.createContext({chrome,URL,fetch,AbortController,TextDecoder,setInterval:()=>{},setTimeout:()=>{},clearTimeout:()=>{}});
 context.importScripts=(...paths)=>paths.forEach(p=>vm.runInContext(fs.readFileSync('browser-extension/'+p,'utf8'),context));
 vm.runInContext(fs.readFileSync('browser-extension/background.js','utf8'),context);
 await new Promise(r=>setImmediate(r));
 await onNative({jobs:[{id:'abc',url:'https://example.com/watch'}]});
 assert.equal(tabs.length,1);assert.equal(tabs[0].active,false);
 await onNative({jobs:[{id:'abc',url:'https://example.com/watch',focus_seq:1}]});assert.equal(focused.length,1);assert.equal(focused[0].id,7);
 await onNative({jobs:[{id:'abc',url:'https://example.com/watch',focus_seq:1}]});assert.equal(focused.length,1);
 await onNative({jobs:[{id:'abc',url:'https://example.com/watch',focus_seq:2}]});assert.equal(focused.length,2);
 const msg=(m,s={url:'chrome-extension://test/popup.html'})=>new Promise(r=>onMessage(m,s,r));
 assert.equal(await msg({type:'tracked'},{tab:{id:99}}),false);
 assert.equal(await msg({type:'tracked'},{tab:{id:7}}),true);
 await onHeaders({tabId:99,statusCode:200,url:'https://cdn.example/ignored.m3u8',responseHeaders:[{name:'Content-Type',value:'application/vnd.apple.mpegurl'}]});
 await onHeaders({tabId:7,frameId:2,statusCode:200,url:'https://cdn.example/master',responseHeaders:[{name:'Content-Type',value:'application/vnd.apple.mpegurl'}]});
 assert.equal((await msg({type:'status'}))[0].candidates.length,0);
 await new Promise(r=>setImmediate(r));
 await msg({type:'video',source:'blob:example',duration:120},{tab:{id:7}});
 assert.equal((await msg({type:'status'}))[0].candidates.length,1);
 assert.equal((await msg({type:'status'}))[0].candidates[0].recommended,true);
 assert.equal(metadataRequests.length,1);assert.equal(metadataRequests[0].options.credentials,'omit');assert.equal(metadataRequests[0].options.redirect,'error');
 await onHeaders({tabId:7,frameId:2,statusCode:200,url:'https://cdn.example/video.m3u8',responseHeaders:[{name:'Content-Type',value:'application/vnd.apple.mpegurl'}]});
 await new Promise(r=>setImmediate(r));
 assert.match((await msg({type:'status'}))[0].candidates[1].label,/804p/);
 assert.equal(await msg({type:'select',id:'abc',index:0},{tab:{id:7}}),false);
 await msg({type:'select',id:'abc',index:0});
 assert.equal(sent.at(-1).type,'result');assert.equal(sent.at(-1).source,'https://cdn.example/master');assert.equal(sent.at(-1).page,'https://example.com/watch');
 await onNative({jobs:[]});assert.equal((await msg({type:'status'})).length,0);
 await onNative({jobs:[{id:'blocked',url:'https://example.com/drm'}]});
 await msg({type:'video',source:'https://cdn.example/a.mp4',drm:true},{tab:{id:7}});
 assert.equal((await msg({type:'status'}))[0].candidates.length,0);
 const count=sent.length;await msg({type:'video',source:'https://cdn.example/b.mp4'},{tab:{id:7}});assert.equal(sent.length,count);
 console.log('Extension tab isolation, source selection, popup boundary, lifecycle and DRM flow checks passed');
})().catch(e=>{console.error(e);process.exit(1)});
