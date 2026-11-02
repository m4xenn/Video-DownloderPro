const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const context=vm.createContext({currentLang:'tr',document:{addEventListener(){}},formatBytes:n=>n+' bytes'});
vm.runInContext(fs.readFileSync('src/static/download-tools.js','utf8'),context);
const nodes={};for(const name of ['.queue-finish-recording','.q-estimate','.q-speed','.queue-pause','.queue-resume'])nodes[name]={setAttribute(){}};
const row={querySelector:name=>nodes[name]};
context.row=row;
context.item={is_live:true,status:'downloading',recorded_seconds:194,recording_limit:14400,recording_speed_bps:60000,downloaded_bytes:12000000};
vm.runInContext('decorateLiveQueue(row,item)',context);
assert.match(nodes['.q-estimate'].textContent,/00:03:14 \/ 04:00:00/);
assert.match(nodes['.q-speed'].textContent,/Gerçek zamanlı/);assert.match(nodes['.q-speed'].textContent,/0,06 MB\/s/);
for(const lang of ['tr','en','de','es','fr','pt','ru','zh','ja','hi']){
 vm.runInContext(`currentLang='${lang}';decorateLiveQueue(row,item)`,context);
 assert.ok(nodes['.q-speed'].textContent.endsWith(' MB/s'));
 assert.equal(vm.runInContext('downloadToolText(7)',context).includes('undefined'),false);
}
console.log('Live UI: clock duration, measured byte rate, real-time explanation and ten languages passed');
