const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context=vm.createContext({URL});vm.runInContext(fs.readFileSync('browser-extension/locales.js','utf8'),context);vm.runInContext(fs.readFileSync('browser-extension/source-labels.js','utf8'),context);
const p=context.VDPSourceLabels;
const master={url:'https://cdn.example/master',role:'master',manifest:{protection:'clear',tracks:[{url:'https://cdn.example/v'},{url:'https://cdn.example/a'}]}};
const video={url:'https://cdn.example/v'},audio={url:'https://cdn.example/a'};
assert.equal(p.canonical([video,master,audio]),master);
assert.equal(p.canonical([master,video,audio,{url:'https://ads.example/preroll'}]),null);
assert.equal(p.canonical([video,audio]),null);
assert.equal(p.canonical([{...master,manifest:{protection:'drm',tracks:master.manifest.tracks}},video,audio]),null);
const a={url:'https://cdn.example/a',role:'master',manifest:{tracks:[{url:'https://cdn.example/b'}]}},b={url:'https://cdn.example/b',role:'master',manifest:{tracks:[{url:a.url}]}};assert.equal(p.canonical([a,b]),null);
let m=p.parse('#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="drm-key"','https://cdn.example/master');assert.equal(m.protection,'aes128');
m=p.parse('#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,KEYFORMAT="com.widevine.alpha",URI="license-secret"','https://cdn.example/master');assert.equal(m.protection,'drm');assert.equal(p.describe({url:master.url,manifest:m},0).disabled,true);assert.equal(JSON.stringify(p.describe({url:master.url,manifest:m},0)).includes('license-secret'),false);
m=p.parse('#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,KEYFORMAT="identity",URI="key"','https://cdn.example/master');assert.equal(m.protection,'unknown');assert.equal(p.describe({url:master.url,manifest:m},0).disabled,true);
(async()=>{
 let tick,onEncrypted;const messages=[];class Media{}
 const video=Object.assign(new Media(),{duration:120,paused:false,mediaKeys:{},currentSrc:'blob:test',getBoundingClientRect:()=>({width:320,height:180}),closest:()=>null});
 const doc={addEventListener:(name,f)=>{if(name==='encrypted')onEncrypted=f},querySelectorAll:()=>[video],title:'Test'};
 vm.runInNewContext(fs.readFileSync('browser-extension/content.js','utf8'),{WeakSet,HTMLMediaElement:Media,document:doc,getComputedStyle:()=>({visibility:'visible',display:'block'}),setInterval:f=>tick=f,chrome:{runtime:{sendMessage:async m=>{if(m.type==='tracked')return true;messages.push(m);return true;}}}});
 await tick();assert.equal(messages.at(-1).drm,false); // A CDM attached to a video is not alone proof of encrypted playback.
 onEncrypted({target:video});await tick();assert.equal(messages.at(-1).drm,true);
 console.log('Verified HLS root selection, ad/cycle ambiguity, encryption classification and EME event checks passed');
})().catch(e=>{console.error(e);process.exit(1)});
