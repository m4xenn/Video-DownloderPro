const assert=require('node:assert/strict'),vm=require('node:vm'),cp=require('node:child_process');
const source=cp.execFileSync('python',['-c',"import sys;sys.path.insert(0,'src');from services.media_discovery import DISCOVERY_SNAPSHOT;print(DISCOVERY_SNAPSHOT)"],{encoding:'utf8'});
function fixture(onlyAd=false) {
 const make=(ad)=>({src:ad?'https://cdn.example/promo.jpg':'https://cdn.example/episode.mp4',currentSrc:'',duration:ad?14:2600,mediaKeys:null,
 closest:s=>ad?{}:null,getBoundingClientRect:()=>({width:640,height:360}),querySelectorAll:()=>[]});
 const videos=onlyAd?[make(true)]:[make(true),make(false)];
 const doc={title:'Episode',baseURI:'https://watch.example/episode',visibilityState:'visible',querySelector:()=>null,
 querySelectorAll:s=>s==='video'||s==='video,.jwplayer,.video-js'?videos:s==='[role="advertisement"],[aria-label="Advertisement"],[aria-label="Reklam"],.jw-flag-ads'?[videos[0]]:[]};
 const location={href:doc.baseURI},navigator={userAgent:'fixture'};
 const win={document:doc,location,navigator,getComputedStyle:()=>({display:'block',visibility:'visible'})};
 return vm.runInNewContext(source,{window:win,document:doc,location,navigator,URL,Set});
}
assert.equal(fixture().media.length,1);
assert.equal(fixture().media[0].sources[0],'https://cdn.example/episode.mp4');
assert.equal(fixture().media[0].duration,2600);
assert.equal(fixture().players.length,1);
assert.equal(fixture(true).media.length,0);
assert.equal(fixture(true).players.length,0);
assert.equal(fixture(true).ad_pending,true);
assert.equal(fixture(true).interaction,true);
console.log('8 labelled preroll exclusion and wait checks passed');
