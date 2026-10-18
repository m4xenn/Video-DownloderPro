// UI update flow contract tests with a minimal DOM and mocked fetch; no network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../src/templates/index.html'), 'utf8');
const code = html.slice(html.indexOf('        let appUpdatePoll'), html.indexOf('        function closeAppUpdate'));

function environment(responses) {
    const nodes = new Map();
    const calls = [];
    const context = vm.createContext({
        document: {getElementById(id) {
            if (!nodes.has(id)) nodes.set(id, {style: {}, textContent: '', disabled: false, firstElementChild: {style: {}}});
            return nodes.get(id);
        }},
        fetch: async (url, options) => {
            calls.push({url, options});
            const response = responses.shift();
            assert.ok(response, `Unexpected request: ${url}`);
            return {ok: response.ok !== false, json: async () => response};
        },
        setTimeout: () => 1,
        clearTimeout: () => {},
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/static/release-notes.js'),'utf8'),context);
    vm.runInContext(code, context);
    return {context, nodes, calls};
}

(async () => {
    let e = environment([{status: 'up_to_date', current_version: 'v1.1.1', update_available: false}]);
    await vm.runInContext('checkAppUpdate(true)', e.context);
    assert.match(e.nodes.get('appUpdateCheckStatus').textContent, /v1.1.1/);
    assert.equal(e.nodes.get('checkAppUpdateBtn').disabled, false);
    assert.equal(e.nodes.has('appUpdateModal'), false);

    e = environment([{status: 'available', update_available: true, latest_version: 'v1.2.0', release_notes: '<script>bad()</script>'}, {status: 'idle'}]);
    await vm.runInContext('checkAppUpdate(true)', e.context);
    assert.equal(e.nodes.get('appUpdateNotes').innerHTML, '<p>&lt;script&gt;bad()&lt;/script&gt;</p>');
    assert.equal(e.nodes.get('appUpdateModal').style.display, 'flex');

    e = environment([{status: 'error', message: 'offline'}]);
    await vm.runInContext('checkAppUpdate(true)', e.context);
    assert.equal(e.nodes.get('appUpdateCheckStatus').textContent, 'offline');
    assert.equal(e.nodes.has('appUpdateModal'), false);

    e = environment([{status: 'success'}, {status: 'downloading', percent: 42}]);
    await vm.runInContext('downloadAppUpdate()', e.context);
    assert.equal(e.calls[0].options.headers['Content-Type'], 'application/json');
    assert.equal(e.nodes.get('appUpdateProgress').value, 42);
    assert.equal(e.nodes.get('appUpdateAction').disabled, true);

    e = environment([{status: 'ready', latest_version: 'v1.2.0', percent: 100}, {ok: false, message: 'Aktif indirmeyi bekleyin.'}]);
    await vm.runInContext('refreshAppUpdate()', e.context);
    assert.equal(e.nodes.get('appUpdateAction').textContent, 'Kurulumu başlat');
    await vm.runInContext('installAppUpdate()', e.context);
    assert.equal(e.nodes.get('appUpdateAction').disabled, false);
    assert.equal(e.nodes.get('appUpdateStatus').textContent, 'Aktif indirmeyi bekleyin.');
    console.log('5 update UI flow checks passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
