const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname,'../src/templates/index.html'),'utf8');
const code = html.slice(html.indexOf('        const draftItems'),html.indexOf('        async function startDownload'));
function node() { return {style:{},dataset:{},value:'',children:[],disabled:false,
    append(...items){this.children.push(...items);},replaceChildren(){this.children=[];},remove(){this.removed=true;}}; }
function environment(responses=[]) {
    const nodes=new Map(),calls=[],messages=[],views=[];
    const get=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};
    const context=vm.createContext({document:{getElementById:get,createElement:node},console,
        fetch:async(url,options)=>{calls.push({url,options});const response=responses.shift();assert.ok(response,`Unexpected ${url}`);return {ok:response.ok!==false,json:async()=>response};},
        downloadQueue:[],managedQueueURLs:new Set(),setTimeout:()=>1,clearTimeout(){},
        setWorkspaceView:view=>views.push(view),
        showToast:message=>messages.push(message),resetUI(){},startProgressPolling(){},
        loadDownloadSettings:async()=>{},pollDownloadProgress:async()=>{},renderQueueItem(){},
        btoa:value=>Buffer.from(value).toString('base64')});
    vm.runInContext(code,context);
    return {context,nodes,calls,get,messages,views,run:source=>vm.runInContext(source,context)};
}
(async()=>{
    let e=environment([{token:'preview'},{status:'ready',entries:[
        {id:'one',title:'Birinci',group:'Liste',available:true},
        {id:'two',title:'İkinci',group:'Liste',available:true},
        {id:'private',title:'Gizli',group:'Liste',available:false}]}]);
    await e.run("beginPlaylistSelection({urls:['https://example.com/list'],is_playlist:true})");
    assert.equal(e.calls.length,2);
    assert.ok(e.calls.every(call=>call.url!='/download'));
    assert.equal(e.run('playlistChosen.size'),2);
    assert.equal(e.get('playlistEntries').children[2].children[0].disabled,true);
    e.run('clearPlaylistSelection()');
    assert.equal(e.get('playlistDownload').disabled,true);
    e.get('playlistSearch').value='İkinci';
    e.run('selectPlaylistResults()');
    assert.equal(e.run('[...playlistChosen].join()'),'two');
    assert.equal(e.get('playlistEntries').children.length,1);

    e=environment();
    await e.run("handleDownloadResult({status:'duplicate',confirmation_token:'server-token',duplicates:[{title:'Video',format:'video',quality:'720p',path:'C:/Video.mp4'}]})");
    assert.equal(e.get('duplicateModal').style.display,'flex');
    assert.equal(e.calls.length,0);
    assert.equal(e.run('duplicateToken'),'server-token');

    e=environment([{status:'success'},{status:'success'}]);
    e.run("duplicateToken='server-token'");
    await e.run("confirmDuplicate('again')");
    assert.deepEqual(JSON.parse(e.calls[0].options.body),{token:'server-token',action:'again'});
    assert.equal(e.get('duplicateModal').style.display,'none');

    e=environment([{total:1,items:[{id:'one',title:'Taşınmış video',format:'video',quality:'720p',size:1024,
        completed_at:'2026-10-17T00:00:00Z',file_exists:false}]}]);
    await e.run('openHistory()');
    assert.equal(e.views.at(-1),'history');
    const buttons=e.get('historyEntries').children[0].children[2].children;
    assert.deepEqual(buttons.map(button=>button.disabled),[true,true,false]);
    assert.match(e.get('historyEntries').children[0].children[1].textContent,/taşınmış veya silinmiş/);

    e=environment([{items:[{url:'https://x/active'},{url:'https://x/draft',title:'Taslak'}]}]);
    e.run("managedQueueURLs.add('https://x/active')");
    await e.run('initializeDownloads()');
    assert.equal(e.run('downloadQueue.join()'),'https://x/draft');
    assert.equal(e.run('formatETA(null)'),'bilinmiyor');
    assert.equal(e.run('formatBytes(null)'),'Bilinmiyor');
    assert.equal(e.run('formatETA(125)'),'2 dk 5 sn');
    e=environment();
    const pending=[];
    e.context.fetch=()=>new Promise(resolve=>pending.push(data=>resolve({ok:true,json:async()=>data})));
    const oldSearch=e.run('loadHistory()');
    assert.equal(e.get('historyMore').disabled,true);
    await e.run('loadHistory(true)');
    assert.equal(pending.length,1,'Do not paginate while a replacement search is pending');
    e.get('historySearch').value='new';
    const newSearch=e.run('loadHistory()');
    pending[1]({total:1,items:[{id:'new',title:'Newest',format:'video',quality:'max',size:1024,completed_at:'2026-10-17T00:00:00Z',file_exists:false}]});
    await newSearch;
    pending[0]({total:0,items:[]});await oldSearch;
    assert.equal(e.get('historyEntries').children.length,1,'Old responses must not erase the newest search');
    assert.equal(e.get('historyEntries').children[0].children[0].textContent,'Newest');
    assert.equal(e.get('historyMore').disabled,false);
    console.log('12 library UI behavior checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
