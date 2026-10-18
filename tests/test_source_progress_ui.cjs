const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const timers=new Map(),nodes=new Map();let next=0,copied='',hint='',requests=[],current='https://example.com/video',fallback=false;
const node=id=>{if(!nodes.has(id))nodes.set(id,{hidden:true,value:'',focus(){this.focused=true},select(){this.selected=true}});return nodes.get(id)};
const c=vm.createContext({currentLang:'tr',setTimeout:fn=>{timers.set(++next,fn);return next},clearTimeout:id=>timers.delete(id),
 singleQualityURL:()=>current,updateQualityHint:text=>hint=text,document:{getElementById:node},openSettings:()=>fallback=true,showToast:()=>{},
 navigator:{clipboard:{writeText:async text=>{copied=text;}}},
 fetch:async(url,options)=>{requests.push({url,body:JSON.parse(options.body)});return {ok:true,json:async()=>url==='/diagnostics'?{status:'success',text:'sanitized report'}:{phase:'waiting_server'}}}});
vm.runInContext(fs.readFileSync('src/static/source-progress.js','utf8'),c);
(async()=>{
 assert.equal(vm.runInContext("sourcePhaseLabel('validating_source')",c),'Kaynak doğrulanıyor…');
 assert.match(vm.runInContext("queueErrorLabel('access_denied')",c),/403/);
 const stop=vm.runInContext("watchSourceProgress('https://example.com/video')",c);
 const [id,fn]=[...timers.entries()][0];timers.delete(id);await fn();
 assert.equal(hint,'Sunucu bekleniyor…');assert.equal(timers.size,1);
 stop();assert.equal(timers.size,0);await fn();assert.equal(requests.length,1);
 await vm.runInContext("copyDiagnosticReport('https://example.com/video')",c);
 assert.equal(copied,'sanitized report');assert.equal(requests.at(-1).body.url,'https://example.com/video');
 c.navigator.clipboard.writeText=async()=>{throw new Error()};
 await vm.runInContext("copyDiagnosticReport('https://example.com/video')",c);
 assert.equal(fallback,true);assert.equal(node('diagnosticsText').selected,true);
 const html=fs.readFileSync('src/templates/index.html','utf8');
 assert.match(html,/class="q-error" hidden/);assert.match(html,/class="queue-copy-error" hidden/);
 assert.doesNotMatch(html,/class="queue-copy-error queue-remove"/);
 console.log('12 source progress and queue error UI checks passed');
})().catch(e=>{console.error(e);process.exitCode=1});
