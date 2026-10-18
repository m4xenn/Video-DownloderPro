const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map(),calls=[],ready=[];
const node=id=>{if(!nodes.has(id))nodes.set(id,{hidden:true,textContent:'',events:{},addEventListener(event,fn){this.events[event]=fn;}});return nodes.get(id);};
let retries=0; const timers=new Map(); let nextTimer=0;
const c=vm.createContext({setTimeout:fn=>{timers.set(++nextTimer,fn);return nextTimer;},clearTimeout:id=>timers.delete(id),document:{getElementById:node,addEventListener:(event,fn)=>ready.push(fn)},fetch:async(url,options)=>{calls.push({url,body:JSON.parse(options.body)});return {ok:true,json:async()=>({status:'success'})};},refreshSourceQuality:()=>retries++});
vm.runInContext(fs.readFileSync('src/static/site-inspection.js','utf8'),c);ready.forEach(fn=>fn());
(async()=>{
vm.runInContext("showSiteInspection({inspection_id:'token',message:'<script>not HTML</script>'},'https://example.com')",c);
assert.equal(node('siteInspection').hidden,false);assert.equal(node('siteInspectionMessage').textContent,'<script>not HTML</script>');
await node('siteInspectionShow').events.click();assert.equal(calls[0].url,'/site-inspection/show');assert.equal(calls[0].body.inspection_id,'token');
assert.equal(timers.size,1);
const first=[...timers.entries()][0];timers.delete(first[0]);await first[1]();assert.equal(retries,1);assert.equal(timers.size,1);
node('siteInspectionRetry').events.click();assert.equal(retries,2);
node('siteInspectionCancel').events.click();assert.equal(calls[1].url,'/site-inspection/cancel');assert.equal(node('siteInspection').hidden,true);assert.equal(timers.size,0);
await node('siteInspectionShow').events.click();assert.equal(calls.length,2);
console.log('8 site inspection interaction and automatic continuation checks passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
