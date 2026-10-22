const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const nodes=new Map();
const node=()=>({textContent:'',title:'',setAttribute(){}});
const row={dataset:{status:'finished'},querySelector(selector){if(!nodes.has(selector))nodes.set(selector,node());return nodes.get(selector);}};
const summary=node(),ids=new Map();
const context=vm.createContext({currentLang:'en',document:{addEventListener(){},getElementById(id){if(id==='downloadSummary')return summary;if(id.startsWith('queue-'))return row;if(!ids.has(id))ids.set(id,node());return ids.get(id);},querySelectorAll(){return [];}},btoa:value=>Buffer.from(value).toString('base64'),encodeURIComponent,Intl,playlistPreview:{entries:[],truncated:true},playlistChosen:new Set(),matchingPlaylistEntries:()=>[],sourceErrorStage:phase=>phase==='download'?'STAGE':''});
for(const file of ['interface-locales.js','interface-localization.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/static',file),'utf8'),context);
const expected=['tr','en','de','es','fr','pt','ru','zh','ja','hi'].sort();
assert.deepEqual(Array.from(vm.runInContext('Object.keys(interfaceLocales)',context)).sort(),expected);
const keys=Array.from(vm.runInContext('Object.keys(interfaceLocales.en)',context)).sort();
for(const lang of expected){
 context.currentLang=lang;
 assert.deepEqual(Array.from(vm.runInContext(`Object.keys(interfaceLocales.${lang})`,context)).sort(),keys);
 assert.equal(vm.runInContext(`Object.values(interfaceLocales.${lang}).every(value=>typeof value==='string' && value.trim().length>0)`,context),true);
 const count=vm.runInContext("interfaceText('historyCount',{total:8,shown:3})",context);
 assert.ok(count.includes('8') && count.includes('3'));assert.ok(!count.includes('{'));
 vm.runInContext("localizeProgress({items:[{url:'https://example.com/a',status:'finished',percent:100,total_bytes:0}],concurrency_mode:'auto',active_count:1,concurrency_limit:2,total_speed_bps:1000000,speed_limit_bps:1000000})",context);
 assert.match(summary.textContent,/8 Mbps/,'A translated summary must retain the configured speed limit');
 assert.ok(nodes.get('.q-estimate').textContent.length>0);
 vm.runInContext('localizePlaylist()',context);
 assert.equal(ids.get('playlistStatus').textContent,vm.runInContext("interfaceText('playlistTruncated')",context),'Playlist truncation must stay visible after localization');
 row.dataset.status='error';
 vm.runInContext("localizeProgress({items:[{url:'https://example.com/a',status:'error',percent:42,error_code:'network_error',error_phase:'download'}]})",context);
 assert.ok(nodes.get('.q-error').textContent.endsWith(' · STAGE'),'Keep the original error stage');
 row.dataset.status='finished';
}
console.log('10 locale schemas, substitutions and speed-limit UI checks passed');
