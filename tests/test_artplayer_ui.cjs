const assert=require('node:assert/strict'),vm=require('node:vm'),cp=require('node:child_process');
const source=cp.execFileSync('python',['-c',"import sys;sys.path.insert(0,'src');from services.media_discovery import DISCOVERY_SNAPSHOT;print(DISCOVERY_SNAPSHOT)"],{encoding:'utf8'});
function fixture(o={}) {
 const doc={title:'Example film',baseURI:'https://watch.example/film',visibilityState:'visible',querySelector:()=>null,querySelectorAll:()=>[]};
 const container={getBoundingClientRect:()=>({width:640,height:360})};
 const art={id:1,url:o.blob?'blob:opaque':'https://cdn.example/master.m3u8',duration:50,
 option:{url:o.original||'https://cdn.example/master.m3u8',drm:o.drm,quality:o.quality||[]},template:{$player:container,$video:{mediaKeys:o.keys?{}:null}}};
 const location={href:doc.baseURI};const navigator={userAgent:'fixture'};
 const win={document:doc,location,Artplayer:{instances:[art]},navigator,getComputedStyle:()=>({display:o.hidden?'none':'block',visibility:'visible'})};
 return vm.runInNewContext(source,{window:win,document:doc,location,navigator,URL,Set});
}
assert.equal(fixture().media[0].group,'artplayer:1');
assert.equal(fixture({blob:true}).media[0].sources[0],'https://cdn.example/master.m3u8');
assert.equal(fixture({blob:true,original:'blob:other'}).media.length,0);
assert.equal(fixture({hidden:true}).media.length,0);
assert.equal(fixture({drm:true}).drm,true);
assert.equal(fixture({keys:true}).drm,true);
assert.equal(fixture({quality:[{url:'https://cdn.example/high.m3u8'}]}).media[0].sources.length,2);
console.log('7 Artplayer source API checks passed');
