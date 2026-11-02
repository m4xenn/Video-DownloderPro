const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const context=vm.createContext({currentLang:'tr',document:{addEventListener(){}},formatBytes:n=>n+' bytes'});
vm.runInContext(fs.readFileSync('src/static/download-tools.js','utf8'),context);
const nodes={};for(const name of ['.queue-live-state','.queue-finish-recording','.q-estimate','.q-speed','.queue-pause','.queue-resume'])nodes[name]={dataset:{},setAttribute(){}};
const row={querySelector:name=>nodes[name]};
context.row=row;
context.item={is_live:true,status:'downloading',recorded_seconds:194,recording_limit:14400,recording_speed_bps:60000,downloaded_bytes:12000000};
vm.runInContext('decorateLiveQueue(row,item)',context);
assert.match(nodes['.q-estimate'].textContent,/00:03:14 \/ 04:00:00/);
assert.match(nodes['.q-speed'].textContent,/Gerçek zamanlı/);assert.match(nodes['.q-speed'].textContent,/0,06 MB\/s/);
assert.equal(nodes['.queue-live-state'].hidden,false);assert.match(nodes['.queue-live-state'].textContent,/Gerçek zamanlı/);
context.item.recording_phase='catchup';context.item.catchup_remaining_seconds=3590;context.item.recording_pace=12.4;
vm.runInContext('decorateLiveQueue(row,item)',context);
assert.match(nodes['.q-speed'].textContent,/Geçmiş indiriliyor/);assert.match(nodes['.q-estimate'].textContent,/≈00:59:50/);
assert.match(nodes['.queue-live-state'].textContent,/Geçmiş indiriliyor.*12,4×.*00:59:50/);
for(const lang of ['tr','en','de','es','fr','pt','ru','zh','ja','hi']){
 vm.runInContext(`currentLang='${lang}';decorateLiveQueue(row,item)`,context);
 assert.ok(nodes['.q-speed'].textContent.endsWith(' MB/s'));
 assert.equal(vm.runInContext('downloadToolText(7)',context).includes('undefined'),false);
}
context.item.status='paused';vm.runInContext('decorateLiveQueue(row,item)',context);
assert.equal(nodes['.queue-live-state'].hidden,true);
console.log('Live UI: clock duration, measured byte rate, real-time explanation and ten languages passed');
