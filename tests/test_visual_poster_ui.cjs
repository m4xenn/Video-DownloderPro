const assert=require('node:assert/strict'),vm=require('node:vm'),cp=require('node:child_process');
const source=cp.execFileSync('python',['-c',"import sys;sys.path.insert(0,'src');from services.player_controls import LAZY_PLAYER_GATES;print(LAZY_PLAYER_GATES)"],{encoding:'utf8'});
function fixture(o={}) {
 const r={width:640,height:360},image={tagName:'IMG',alt:o.alt||'Example film'};
 const f={getAttribute:n=>n==='src'?(o.src||''):(o.target||'/player')};
 const parent={tagName:o.parentTag||'DIV',getBoundingClientRect:()=>o.huge?{width:4000,height:3000}:r,querySelectorAll:()=>Array(o.frames??1).fill(f)};
 const gate={tagName:'DIV',children:o.noSvg?[image]:[image,{tagName:'svg'}],parentElement:parent,
 getBoundingClientRect:()=>r,closest:()=>o.link||o.ad?{}:null};
 const doc={title:'Example film (2026)',baseURI:'https://watch.example/film',querySelector:()=>null,querySelectorAll:s=>s==='div'?[gate]:[]};
 const win={document:doc,getComputedStyle:()=>({display:o.hidden?'none':'block',visibility:'visible',cursor:o.noCursor?'auto':'pointer'})};
 return vm.runInNewContext(source+'(window)',{window:win,URL,Set});
}
assert.equal(fixture().length,1);
for(const o of [{alt:'Another film'},{alt:'X'},{noSvg:true},{link:true},{ad:true},{hidden:true},{noCursor:true},
 {frames:0},{frames:2},{src:'https://already.example/player'},{target:'javascript:bad()'},{target:'https://captcha.example/check'},{huge:true},{parentTag:'BODY'}])assert.equal(fixture(o).length,0,JSON.stringify(o));
console.log('15 visual poster gate checks passed');
