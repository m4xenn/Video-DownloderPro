const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
(async()=>{
 let receive,disconnect,message;let stored={language:'de'};
 const chrome={i18n:{getUILanguage:()=> 'fr-FR'},runtime:{id:'a'.repeat(32),getManifest:()=>({version:'0.4.1'}),getURL:p=>'chrome-extension://test/'+p,
  onMessage:{addListener:f=>message=f},connectNative:()=>({onDisconnect:{addListener:f=>disconnect=f},onMessage:{addListener:f=>receive=f},postMessage:()=>{}})},
  storage:{session:{get:async()=>stored,set:async value=>stored=value}},alarms:{create(){},onAlarm:{addListener(){}}},
  tabs:{create:async()=>({id:1}),update:async()=>{},get:async()=>({windowId:2})},windows:{update:async()=>{}},webRequest:{onHeadersReceived:{addListener(){}}}};
 const context=vm.createContext({chrome,URL,setInterval(){},setTimeout(){},clearTimeout(){}});
 context.importScripts=(...names)=>names.forEach(name=>vm.runInContext(fs.readFileSync('browser-extension/'+name,'utf8'),context));
 vm.runInContext(fs.readFileSync('browser-extension/background.js','utf8'),context);
 await new Promise(r=>setImmediate(r));
 const ask=(payload,sender={url:'chrome-extension://test/popup.html'})=>new Promise(resolve=>message(payload,sender,resolve));
 let reply=await ask({type:'popup-status'});assert.equal(reply.language,'de');assert.equal(reply.connected,false);
 await receive({language:'fr',jobs:[{id:'one',url:'https://example.com/watch'}]});
 reply=await ask({type:'popup-status'});assert.equal(reply.language,'fr');assert.equal(reply.connected,true);assert.match(reply.jobs[0].state,/vidéo/);assert.equal(stored.language,'fr');
 await receive({language:'ja',jobs:[{id:'one',url:'https://example.com/watch'}]});
 reply=await ask({type:'popup-status'});assert.equal(reply.language,'ja');assert.match(reply.jobs[0].state,/動画/);
 await receive({language:'https://evil.example',jobs:[]});assert.equal((await ask({type:'popup-status'})).language,'ja');
 disconnect();reply=await ask({type:'popup-status'});assert.equal(reply.connected,false);assert.equal(reply.language,'ja');
 assert.equal(await ask({type:'popup-status'},{tab:{id:1}}),false);
 const i18n=context.VDPI18n,labels=context.VDPSourceLabels,keys=Object.keys(i18n.locales.en).sort();
 for(const language of ['tr','en','de','es','fr','pt','ru','zh','ja','hi']){
  assert.deepEqual(Object.keys(i18n.locales[language]).sort(),keys);
  for(const key of keys){
   assert.ok(i18n.text(key,language));
   assert.deepEqual([...i18n.locales[language][key].matchAll(/\{(\w+)\}/g)].map(x=>x[1]).sort(),[...i18n.locales.en[key].matchAll(/\{(\w+)\}/g)].map(x=>x[1]).sort());
  }
  const master=labels.describe({url:'https://cdn.example/master?secret=PRIVATE',role:'master',variantCount:4},0,language);
  assert.ok(master.recommended);assert.ok(master.detail.includes('4'));assert.ok(!master.detail.includes('{count}'));
  assert.ok(!JSON.stringify(master).includes('PRIVATE'));
 }
 assert.equal(i18n.normalize('fr_CA'),'fr');assert.equal(i18n.normalize('toString'),null);assert.equal(i18n.normalize('__proto__'),null);
 assert.equal(i18n.text('empty','invalid'),i18n.text('empty','en'));
 console.log('Companion language sync: live changes, disconnected retention, sender boundary, ten locale schemas and localized source labels passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
