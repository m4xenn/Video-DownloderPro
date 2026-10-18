const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map(),calls=[],ready=[];
const node=id=>{if(!nodes.has(id))nodes.set(id,{hidden:true,textContent:'',events:{},addEventListener(event,fn){this.events[event]=fn;}});return nodes.get(id);};
let retries=0;
const c=vm.createContext({document:{getElementById:node,addEventListener:(event,fn)=>ready.push(fn)},fetch:async(url,options)=>{calls.push({url,body:JSON.parse(options.body)});return {ok:true,json:async()=>({status:'success'})};},refreshSourceQuality:()=>retries++});
vm.runInContext(fs.readFileSync('src/static/site-inspection.js','utf8'),c);ready.forEach(fn=>fn());
(async()=>{
vm.runInContext("showSiteInspection({inspection_id:'token',message:'<script>not HTML</script>'},'https://example.com')",c);
assert.equal(node('siteInspection').hidden,false);assert.equal(node('siteInspectionMessage').textContent,'<script>not HTML</script>');
await node('siteInspectionShow').events.click();assert.equal(calls[0].url,'/site-inspection/show');assert.equal(calls[0].body.inspection_id,'token');
node('siteInspectionRetry').events.click();assert.equal(retries,1);
node('siteInspectionCancel').events.click();assert.equal(calls[1].url,'/site-inspection/cancel');assert.equal(node('siteInspection').hidden,true);
await node('siteInspectionShow').events.click();assert.equal(calls.length,2);
console.log('5 site inspection interaction checks passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
