const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const code=fs.readFileSync(require('node:path').join(__dirname,'../src/static/bulk-quality.js'),'utf8');
function environment(text='',failURL='') {
    const nodes=new Map(),calls=[],messages=[];let active=0,peak=0,saved=0;
    const get=id=>{if(!nodes.has(id))nodes.set(id,{value:'',checked:false,disabled:false,style:{},textContent:'',classList:{add(){},remove(){}},focus(){},scrollHeight:48});return nodes.get(id);};
    get('urlInput').value=text;get('formatValue').value='video';
    const context=vm.createContext({URL,Map,Set,document:{getElementById:get,addEventListener(){}},
        downloadQueue:[],activeQueueURLs:new Set(),draftItems:new Map(),currentLang:'tr',translations:{tr:{tErrLink:'Boş'}},
        showToast:m=>messages.push(m),renderQueueItem(){},updateQualityMenu(){},formatBytes:()=> '1 MB',
        saveDraftQueue:async()=>{saved++;},fetch:async(url,options)=>{
            calls.push({url,options});active++;peak=Math.max(peak,active);await new Promise(resolve=>setImmediate(resolve));active--;
            const target=JSON.parse(options.body).url;
            return {ok:target!==failURL,json:async()=>target===failURL?{status:'error'}:{status:'success',url:target,title:'Video',video_qualities:[]}};
        }});
    vm.runInContext(code,context);
    return {get,context,calls,messages,run:source=>vm.runInContext(source,context),get peak(){return peak;},get saved(){return saved;}};
}
(async()=>{
    let e=environment();
    let parsed=e.run("splitLinks('https://EXAMPLE.com/a https://example.com/a#again file:///private invalid https://example.com/b?x=1,2')");
    assert.equal(parsed.urls.length,2);assert.equal(parsed.duplicates,1);assert.equal(parsed.invalid.length,2);
    assert.ok(parsed.urls[1].includes('1,2'));
    e=environment('https://example.com/1\nhttps://example.com/2\nhttps://example.com/3\nhttps://example.com/4\nhttps://example.com/5');
    await e.run('addLinksToQueue()');assert.equal(e.peak,3);assert.equal(e.run('downloadQueue.length'),5);
    assert.equal(e.saved,1);assert.equal(e.get('urlInput').value,'');assert.equal(e.get('addBtn').disabled,false);
    e=environment('https://example.com/good https://example.com/bad invalid https://example.com/good','https://example.com/bad');
    await e.run('addLinksToQueue()');assert.equal(e.run('downloadQueue.length'),1);
    assert.match(e.get('urlInput').value,/invalid/);assert.match(e.get('urlInput').value,/example.com\/bad/);
    assert.match(e.get('bulkStatus').textContent,/1 tekrar atlandı/);assert.match(e.get('bulkStatus').textContent,/2 bağlantı eklenemedi/);
    e=environment('https://example.com/active');e.run("activeQueueURLs.add('https://example.com/active')");
    await e.run('addLinksToQueue()');assert.equal(e.calls.length,0);
    e=environment(Array.from({length:501},(_,i)=>'https://example.com/'+i).join('\n'));
    await e.run('addLinksToQueue()');assert.equal(e.calls.length,0);assert.match(e.get('bulkStatus').textContent,/500/);
    e=environment();e.run("downloadQueue.push('https://example.com/one');draftItems.set(downloadQueue[0],{video_qualities:[{value:'source:2160:60',label:'2160p · 60 FPS'}]})");
    await e.run('refreshSourceQuality()');assert.equal(e.run('getVideoQualityOptions().length'),2);assert.equal(e.calls.length,0);
    assert.equal(e.run('getVideoQualityOptions()[0].value'),'max');
    e.run("downloadQueue.push('https://example.com/two')");await e.run('refreshSourceQuality()');
    assert.equal(e.run('getVideoQualityOptions().length'),1);assert.match(e.get('qualityHint').textContent,/en yüksek/);
    e.run('downloadQueue.pop()');e.get('playlistCheck').checked=true;await e.run('refreshSourceQuality()');
    assert.equal(e.run('getVideoQualityOptions().length'),1);
    e=environment('https://example.com/pasted');
    await e.run('refreshSourceQuality()');
    assert.equal(e.run('downloadQueue.length'),0);
    assert.equal(e.get('linkPreviewTitle').textContent,'Video');
    assert.match(e.get('linkPreviewMeta').textContent,/belirtilmiyor/);
    assert.equal(e.calls.length,1);
    await e.run('addLinksToQueue()');
    assert.equal(e.calls.length,1);assert.equal(e.run('downloadQueue.length'),1);
    e=environment('https://example.com/old');
    const pending=e.run('refreshSourceQuality()');
    e.get('urlInput').value='https://example.com/new';
    await pending;
    assert.notEqual(e.get('linkPreviewTitle').textContent,'Video');
    assert.equal(e.run('pastedMetadata.size'),0);
    e=environment('https://example.com/a https://example.com/b');
    await e.run('refreshSourceQuality()');assert.equal(e.calls.length,0);
    e=environment('https://example.com/one');
    e.run("pastedMetadata.set('https://example.com/one',{at:Date.now(),data:{status:'success',url:'https://example.com/one',title:'Cached',video_qualities:[{value:'source:720:30',label:'720p'}]}})");
    await e.run('refreshSourceQuality()');assert.equal(e.run('getVideoQualityOptions().length'),2);
    assert.equal(e.run('downloadQueue.length'),0);
    await e.run('addLinksToQueue()');assert.equal(e.run('getVideoQualityOptions().length'),2);assert.equal(e.calls.length,0);
    console.log('14 bulk/source-quality UI flow checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
