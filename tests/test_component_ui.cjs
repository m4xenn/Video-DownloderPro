const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../src/templates/index.html'), 'utf8');
const code = html.slice(html.indexOf('        let componentPoll'), html.indexOf('        // --- 1. SIRA'));
function node() {
    return {style: {}, textContent: '', disabled: false, children: [],
        replaceChildren() {this.children = [];}, append(...children) {this.children.push(...children);}};
}
function environment(responses, lang='tr') {
    const nodes = new Map(), calls = [];
    const context = vm.createContext({currentLang: lang,
        document: {getElementById(id) {if (!nodes.has(id)) nodes.set(id,node()); return nodes.get(id);}, createElement: node},
        fetch: async (url, options) => {
            calls.push({url,options});
            const response=responses.shift(); assert.ok(response, `Unexpected ${url}`);
            return {ok: response.ok !== false, json: async () => response};
        }, setTimeout: () => 1, clearTimeout() {}, console,
    });
    vm.runInContext(code,context);
    return {context,nodes,calls};
}
(async () => {
    let e=environment([{status:'idle'},{status:'success'},{status:'checking',message:'Kontrol ediliyor...'}]);
    await vm.runInContext('forceUpdate()',e.context);
    assert.deepEqual(e.calls.map(c=>c.url), ['/components/status','/components/check','/components/status']);
    assert.ok(!e.nodes.get('updateTitle').textContent.includes('undefined'));

    e=environment([{status:'available',message:'Yeni sürüm',components:[{name:'yt-dlp',installed:'old',latest:'<script>bad()</script>',update_available:true}]}]);
    await vm.runInContext('pollComponentUpdate()',e.context);
    assert.equal(e.nodes.get('componentAction').style.display,'flex');
    assert.match(e.nodes.get('componentVersions').children[0].children[1].textContent,/<script>/);

    e=environment([{status:'up_to_date',message:'Bileşenler güncel.',components:[]}]);
    await vm.runInContext('pollComponentUpdate()',e.context);
    assert.equal(e.nodes.get('componentAction').style.display,'none');

    e=environment([{status:'success'},{status:'downloading',percent:40,downloaded:4194304,total:10485760,message:'FFmpeg indiriliyor'}]);
    await vm.runInContext('downloadComponentUpdates()',e.context);
    assert.equal(e.nodes.get('componentProgress').value,40);
    assert.match(e.nodes.get('componentTransfer').textContent,/4.0 \/ 10.0 MB/);

    e=environment([{status:'error',message:'Bağlantı kurulamadı'}], 'de');
    await vm.runInContext('pollComponentUpdate()',e.context);
    assert.equal(e.nodes.get('componentAction').textContent,'Check again');
    assert.equal(e.nodes.get('componentAction').disabled,false);

    e=environment([{status:'finished',message:'Tamamlandı. Yeniden açın.',restart_required:true}]);
    await vm.runInContext('pollComponentUpdate()',e.context);
    assert.equal(e.nodes.get('componentProgress').style.display,'none');
    assert.match(e.nodes.get('updateDesc').textContent,/Yeniden açın/);
    vm.runInContext('closeComponentUpdate()',e.context);
    assert.equal(e.nodes.get('updateOverlay').style.display,'none');
    e=environment([{status:'available',verification_only:true,components:[{name:'ffmpeg',installed:'same build',latest:'Latest build',update_available:false,verification_required:true,untracked:true}]}]);
    await vm.runInContext('pollComponentUpdate()',e.context);
    assert.equal(e.nodes.get('componentAction').textContent,'Doğrulanmış paketi yeniden kur');
    const details=e.nodes.get('componentVersions').children[0].children[1].textContent;
    assert.match(details,/Kurulum doğrulanamadı/);
    assert.doesNotMatch(details,/Güncelleme mevcut/);
    console.log('7 component UI flow checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
