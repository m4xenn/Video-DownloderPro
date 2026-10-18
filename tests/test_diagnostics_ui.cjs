const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const nodes=new Map(),ready=[];
const el=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',value:'',hidden:true,disabled:false,events:{},addEventListener(e,f){this.events[e]=f;},focus(){this.focused=true;},select(){this.selected=true;}});return nodes.get(id);};
let fail=false,clipboardFail=false,copied='',request;
const context=vm.createContext({currentLang:'tr',document:{getElementById:el,addEventListener:(_,fn)=>ready.push(fn)},
 fetch:async(url,options)=>{request={url,options};if(fail)throw new Error();return {ok:true,json:async()=>({status:'success',text:'<script>plain text</script>',count:1,available:true})};},
 navigator:{clipboard:{writeText:async text=>{if(clipboardFail)throw new Error();copied=text;}}}});
vm.runInContext(fs.readFileSync('src/static/diagnostics.js','utf8'),context);ready[0]();
(async()=>{
 assert.equal(el('diagnosticsTitle').textContent,'Sorun giderme kayıtları');
 await el('diagnosticsLoad').events.click();
 assert.equal(request.url,'/diagnostics');assert.equal(request.options.method,'POST');
 assert.equal(el('diagnosticsText').value,'<script>plain text</script>');
 assert.equal(el('diagnosticsCopy').disabled,false);
 await el('diagnosticsCopy').events.click();assert.equal(copied,el('diagnosticsText').value);
 clipboardFail=true;await el('diagnosticsCopy').events.click();assert.equal(el('diagnosticsText').selected,true);
 fail=true;await el('diagnosticsLoad').events.click();assert.equal(el('diagnosticsCopy').disabled,true);
 assert.equal(el('diagnosticsLoad').disabled,false);
 context.currentLang='en';el('diagnosticsPanel').events.toggle();assert.equal(el('diagnosticsTitle').textContent,'Troubleshooting records');
 console.log('10 diagnostic UI checks passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
