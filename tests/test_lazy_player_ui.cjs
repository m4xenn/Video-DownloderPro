const assert=require('node:assert/strict'),vm=require('node:vm'),cp=require('node:child_process');
const script=cp.execFileSync('python',['-c',"import sys;sys.path.insert(0,'src');from services.player_activation import START_PLAYER;print(START_PLAYER)"],{encoding:'utf8'});
function fixture({label='Play video',frames=1,href=false,form=false,submit=false,verification=false,drm=false,already=false,huge=false,src='',target='/embed',gates=1}={}) {
 let clicks=0;
 const rect={width:640,height:360};
 const frame={getAttribute:name=>name==='src'?src:target};
 const parent={parentElement:null,getBoundingClientRect:()=>huge?{width:3000,height:3000}:rect,querySelectorAll:()=>Array(frames).fill(frame)};
 const makeGate=()=>({parentElement:parent,getBoundingClientRect:()=>rect,getAttribute:()=>label,
   closest:()=>href||form?{}:null,matches:()=>submit,hasAttribute:()=>already,
   setAttribute:()=>{already=true},click:()=>clicks++});
 const controls=Array.from({length:gates},makeGate);
 const doc={title:'A video',baseURI:'https://example.com/watch',querySelectorAll:selector=>
   selector==='[aria-label]'?controls:selector==='video,.jwplayer,.video-js'?[]:verification?[controls[0]]:[]};
 const win={document:doc,location:{href:'https://example.com/watch'},getComputedStyle:()=>({display:'block',visibility:'visible'})};
 vm.runInNewContext(script+'("https://example.com/watch")',{window:win,URL,Set});
 return clicks;
}
assert.equal(fixture(),1);
assert.equal(fixture({label:'Videoyu oynat'}),1);
for(const options of [{label:'Download'},{label:'Verify'},{label:'Register'},{frames:0},{frames:2},
 {href:true},{form:true},{submit:true},{verification:true},{already:true},{huge:true},
 {src:'https://example.com/already-started'},{target:'javascript:alert(1)'},{target:'https://captcha.example/check'},{gates:2}]) {
 assert.equal(fixture(options),0,JSON.stringify(options));
}
console.log('17 lazy-player controls checks passed');
