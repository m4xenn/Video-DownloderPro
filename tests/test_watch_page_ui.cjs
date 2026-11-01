const assert=require('node:assert/strict'),vm=require('node:vm'),cp=require('node:child_process');
const source=cp.execFileSync('python',['-c',"import sys;sys.path.insert(0,'src');from services.poster_navigation import WATCH_PAGE_LINKS;print(WATCH_PAGE_LINKS)"],{encoding:'utf8'});
function fixture(o={}) {
 const a={href:o.href||'https://watch.example/episode/1?vod=hd',rel:o.rel||'',textContent:o.text||'',closest:()=>o.ad?{}:null,
 querySelector:()=>o.noImage?null:{alt:o.alt||'Example Episode 1 HD'},getBoundingClientRect:()=>({width:o.width||640,height:o.height||360})};
 const doc={baseURI:'https://watch.example/episode/1',querySelector:s=>s==='h1'?{textContent:'Example Episode 1'}:o.player?{}:null,querySelectorAll:()=>o.ambiguous?[a,{...a,href:a.href+'&server=2'}]:[a]};
 return vm.runInNewContext(source+'(window)',{window:{document:doc,location:{href:'https://watch.example/episode/1'},getComputedStyle:()=>({display:o.hidden?'none':'block',visibility:'visible'})},URL});
}
assert.deepEqual(Array.from(fixture()),['https://watch.example/episode/1?vod=hd']);
for(const o of [{href:'https://ad.example/episode/1?vod=hd'},{href:'https://watch.example/episode/2?vod=hd'},
 {href:'https://watch.example/episode/1'},{href:'javascript:alert(1)'},{href:'https://u:p@watch.example/episode/1?vod=hd'},
 {ad:true},{rel:'sponsored'},{alt:'Another movie'},{text:'Download in HD'},{text:'Trailer'},
 {noImage:true},{width:100},{height:40},{hidden:true},{ambiguous:true},{player:true}]) assert.equal(fixture(o).length,0,JSON.stringify(o));
console.log('17 same-page watch cover navigation checks passed');
