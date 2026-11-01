const assert=require('node:assert/strict'),vm=require('node:vm'),cp=require('node:child_process');
const source=cp.execFileSync('python',['-c',"import sys;sys.path.insert(0,'src');from services.player_controls import LAZY_PLAYER_GATES;print(LAZY_PLAYER_GATES)"],{encoding:'utf8'});
function fixture({label='Play Arcane episode 1',title='Watch Arcane Episode 1',aria=true,frames=1,src='about:blank',data=null,href=false,form=false,submit=false,edge=false,huge=false,tag='BUTTON',parentTag='DIV'}={}) {
 const r={width:64,height:64,left:288,top:148};if(edge)r.left=0;
 const p={width:640,height:360,left:0,top:0};if(huge){p.width=3000;p.height=3000;}
 const frame={getAttribute:name=>name==='src'?src:data};
 const parent={tagName:parentTag,parentElement:null,getBoundingClientRect:()=>p,querySelectorAll:()=>Array(frames).fill(frame)};
 const gate={tagName:tag,parentElement:parent,textContent:label,getAttribute:()=>aria?label:null,
  getBoundingClientRect:()=>r,closest:()=>href||form?{}:null,matches:()=>submit};
 const doc={title,baseURI:'https://example.com/watch',querySelectorAll:selector=>selector==='button,[role="button"]'?[gate]:[]};
 const win={document:doc,getComputedStyle:()=>({display:'block',visibility:'visible'})};
 return vm.runInNewContext(source+'(window)',{window:win,URL,Set,Math});
}
assert.equal(fixture().length,1);
assert.equal(fixture({label:'Oynat',aria:false}).length,1);
assert.equal(fixture()[0].__vdpPlayerArea,640*360);
for(const options of [{label:'Play next'},{label:'Download in HD'},{label:'Verify'},{title:'Another movie'},
 {frames:0},{frames:2},{src:'https://already.example/player'},{data:'javascript:bad()'},
 {href:true},{form:true},{submit:true},{edge:true},{huge:true},{tag:'DIV'},{parentTag:'MAIN'}])assert.equal(fixture(options).length,0,JSON.stringify(options));
console.log('18 modern poster gate checks passed');
