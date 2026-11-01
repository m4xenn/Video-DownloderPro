const assert=require('node:assert/strict'),vm=require('node:vm'),cp=require('node:child_process');
const script=cp.execFileSync('python',['-c',"import sys;sys.path.insert(0,'src');from services.media_discovery import DISCOVERY_SNAPSHOT;print(DISCOVERY_SNAPSHOT)"],{encoding:'utf8'});
function fixture(o={}) {
 const container={closest:()=>o.ad?{}:null,querySelector:()=>o.drm?{mediaKeys:{}}:null,getBoundingClientRect:()=>({width:640,height:360})};
 const doc={title:'Episode',baseURI:'https://watch.example/episode',visibilityState:'visible',getElementById:()=>container,querySelector:()=>null,querySelectorAll:()=>[]};
 const calls=[],hls={url:o.blob?'blob:manifest':'https://cdn.example/master.jpg',levels:o.empty?[]:[{url:['https://cdn.example/720.jpg']}]};
 const player={api:k=>{calls.push(k);return k==='id'?'Player':k==='hls'?hls:k==='duration'?2708:null}};
 const location={href:doc.baseURI},navigator={userAgent:'fixture'};
 const window={document:doc,location,navigator,Playerjs:function(){},player,getComputedStyle:()=>({display:o.hidden?'none':'block',visibility:'visible'})};
 const result=vm.runInNewContext(script,{window,document:doc,location,navigator,URL,Set});return {result,calls};
}
assert.equal(fixture().result.media[0].sources[0],'https://cdn.example/master.jpg');
assert.equal(fixture().result.media[0].source_types['https://cdn.example/master.jpg'],'hls');
assert.equal(fixture({blob:true}).result.media[0].sources[0],'https://cdn.example/720.jpg');
for(const o of [{empty:true},{hidden:true},{ad:true}])assert.equal(fixture(o).result.media.length,0);
assert.equal(fixture({drm:true}).result.drm,true);
assert.ok(fixture().calls.every(k=>['id','hls','duration'].includes(k)));
console.log('8 Playerjs HLS source API checks passed');
