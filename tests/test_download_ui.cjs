const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../src/templates/index.html'), 'utf8');
const code = html.slice(html.indexOf('        let progressInterval;'), html.indexOf('        function openSettings()'))
    + html.slice(html.indexOf('        async function saveSettings()'), html.indexOf('        async function startDownload()'));
function environment(responses) {
    const nodes = new Map(), calls = [], errors = [];
    let closed = 0;
    const context = vm.createContext({
        currentLang: 'tr', translations: {tr:{tSuccess:'Kaydedildi'}},
        document: {getElementById(id) {
            if (!nodes.has(id)) nodes.set(id, {style:{}, value:'', disabled:false, textContent:''});
            return nodes.get(id);
        }},
        fetch: async (url,options) => {
            calls.push({url,options});
            const response = responses.shift(); assert.ok(response, `Unexpected ${url}`);
            return {ok:response.ok !== false,json:async()=>response};
        }, setInterval:()=>1, clearInterval(){}, setCompressModeUI(){}, resetUI(){},
        closeSettings(){closed++;}, showToast(message){errors.push(message);}, console,
        Set,
    });
    vm.runInContext(code,context);
    return {context,nodes,calls,errors,get closed(){return closed;}};
}
(async()=>{
    let e=environment([{concurrency_mode:'auto',concurrent_downloads:3,speed_limit_mbps:'2.5',auto_compress:false}]);
    await vm.runInContext('loadDownloadSettings()',e.context);
    assert.equal(e.nodes.get('settingMode').value,'auto');
    assert.equal(e.nodes.get('settingConcurrent').disabled,true);
    assert.equal(e.nodes.get('settingSpeed').value,'2.5');
    e.nodes.get('settingMode').value='manual';
    vm.runInContext('updateConcurrencyUI()',e.context);
    assert.equal(e.nodes.get('settingConcurrent').disabled,false);

    e=environment([{status:'success'}]);
    for(const [id,value] of Object.entries({settingMode:'manual',settingConcurrent:'2',settingSpeed:'8',settingCompressMode:'false'})) {
        vm.runInContext(`document.getElementById('${id}')`,e.context).value=value;
    }
    await vm.runInContext('saveSettings()',e.context);
    const payload=JSON.parse(e.calls[0].options.body);
    assert.equal(payload.concurrency_mode,'manual');
    assert.equal(payload.speed_limit_mbps,'8');
    assert.equal(payload.speed_limit,undefined);
    assert.equal(e.closed,1);

    e=environment([{ok:false,message:'Geçersiz sınır'}]);
    for(const id of ['settingMode','settingConcurrent','settingSpeed','settingCompressMode']) vm.runInContext(`document.getElementById('${id}')`,e.context);
    await vm.runInContext('saveSettings()',e.context);
    assert.equal(e.closed,0);
    assert.ok(e.errors.includes('Geçersiz sınır'));

    e=environment([{status:'success'},{status:'downloading',items:[],total_items:1,concurrency_mode:'auto',concurrency_limit:2,active_count:1,total_speed_bps:1000000,speed_limit_bps:1250000}]);
    await vm.runInContext("queueCommand('/resume','https://x/a')",e.context);
    assert.deepEqual(JSON.parse(e.calls[0].options.body),{url:'https://x/a'});
    assert.match(e.nodes.get('downloadSummary').textContent,/Otomatik/);
    assert.match(e.nodes.get('downloadSummary').textContent,/10.0 Mbps/);

    e=environment([{status:'error',items:[],total_items:1,error:'network failed'}]);
    await vm.runInContext('pollDownloadProgress()',e.context);
    assert.ok(e.errors.includes('network failed'));
    console.log('6 download/settings UI flow checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
