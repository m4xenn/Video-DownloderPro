/* Localize the actual controls, not screenshot pixels. */
let interfaceUpdateState=null, interfaceHistoryState=null;
function interfaceText(key,values={}) {
 const locale=interfaceLocales[currentLang] || interfaceLocales.en;
 return (locale[key] || interfaceLocales.en[key] || key).replace(/\{(\w+)\}/g,(match,name)=>String(values[name] ?? match));
}
function interfaceLabel(selector,key) {
 document.querySelectorAll(selector).forEach(node=>{
  const icon=node.querySelector('i');
  if(icon)node.replaceChildren(icon.cloneNode(true),document.createTextNode(' '+interfaceText(key)));
  else node.textContent=interfaceText(key);
 });
}
function localizeUpdateStatus(data) {
 interfaceUpdateState=data;
 if(!data.update_available && data.status!=='error')document.getElementById('appUpdateCheckStatus').textContent=interfaceText('upToDate',{version:data.current_version || ''});
}
function localizeHistory(data) {
 interfaceHistoryState=data;
 const rows=[...document.querySelectorAll('#historyEntries .feature-row')];
 rows.forEach((row,index)=>{
  const entry=data.items[index];if(!entry)return;
  row.querySelectorAll('.feature-actions button').forEach((button,i)=>button.textContent=interfaceText(['openFile','showFolder','downloadAgain'][i]));
  if(typeof localizeHistoryPreview==='function')localizeHistoryPreview(row);
  const format=entry.format==='video'?translations[currentLang].video:(entry.quality || translations[currentLang].audio).toUpperCase();
  row.querySelector('.feature-muted').textContent=`${format} · ${entry.size?formatBytes(entry.size):interfaceText('unknownSize')} · ${new Date(entry.completed_at).toLocaleString(currentLang)}\n${entry.file_exists?entry.path:interfaceText('missingFile')}`;
 });
 document.getElementById('historyStatus').textContent=interfaceText('historyCount',{total:data.total || 0,shown:rows.length});
 const searching=Boolean(document.getElementById('historySearch').value.trim());
 document.getElementById('historyEmpty').hidden=rows.length>0;
 document.getElementById('historyEmptyText').textContent=searching?(queueViewCopy[currentLang] || queueViewCopy.en)[7]:interfaceText('historyEmpty');
 document.getElementById('historyNewDownload').textContent=(queueViewCopy[currentLang] || queueViewCopy.en)[searching?8:9];
}
function localizePlaylist() {
 if(typeof playlistPreview==='undefined' || !playlistPreview?.entries)return;
 document.getElementById('playlistStatus').textContent=interfaceText(playlistPreview.truncated?'playlistTruncated':'playlistHint');
 const entries=matchingPlaylistEntries();
 document.querySelectorAll('#playlistEntries .playlist-entry').forEach((row,index)=>{
  const entry=entries[index];if(!entry)return;
  const duration=entry.duration?Math.floor(entry.duration/60)+':'+String(entry.duration%60).padStart(2,'0'):'';
  row.querySelector('.feature-muted').textContent=[entry.group,entry.available?duration:interfaceText('unavailable'),entry.total_bytes?'≈ '+formatBytes(entry.total_bytes):interfaceText('unknownSize')].filter(Boolean).join(' · ');
 });
 document.getElementById('playlistCount').textContent=interfaceText('playlistCount',{selected:playlistChosen.size,total:playlistPreview.entries.filter(entry=>entry.available).length});
}
function localizeQueueRow(row) {
 const labels={'.queue-pause':'pause','.queue-resume':row.dataset.status==='error'?'retry':'resume','.queue-remove':'remove','.queue-copy-error':'diagCopy'};
 Object.entries(labels).forEach(([selector,key])=>{const button=row.querySelector(selector);button.title=interfaceText(key);button.setAttribute('aria-label',button.title);});
}
function localizeProgress(data) {
 for(const item of data.items || []) {
  const row=document.getElementById('queue-'+btoa(encodeURIComponent(item.url)).replace(/=/g,''));if(!row)continue;
  localizeQueueRow(row);
  const key={queued:'queued',starting:'starting',paused:'paused',pausing:'pausing',converting:'converting',finished:'finished',error:'error'}[item.status];
  if(key)row.querySelector('.q-speed').textContent=interfaceText(key);
  row.querySelector('.q-percent').textContent=new Intl.NumberFormat(currentLang,{style:'percent',maximumFractionDigits:0}).format((item.percent || 0)/100);
  if(item.error_code==='network_error') {
   const stage=typeof sourceErrorStage==='function'?sourceErrorStage(item.error_phase):'';
   row.querySelector('.q-error').textContent=interfaceText('networkError')+(stage?' · '+stage:'');
  }
  const size=item.total_bytes?`${item.size_estimated?'≈ ':''}${formatBytes(item.total_bytes)}`:interfaceText('unknownSize');
  const seconds=Number.isFinite(item.eta)?Math.ceil(item.eta):null;
  const eta=item.status==='downloading' && seconds!==null?' · '+interfaceText('remaining')+': '+Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0'):'';
  row.querySelector('.q-estimate').textContent=size+eta;
 }
 const mode=interfaceText(data.concurrency_mode==='auto'?'autoMode':'manualMode');
 const cap=data.speed_limit_bps?' · '+interfaceText('speedLimit')+': '+(data.speed_limit_bps*8/1000000).toLocaleString(currentLang,{maximumFractionDigits:1})+' Mbps':'';
 document.getElementById('downloadSummary').textContent=`${mode} · ${data.active_count || 0}/${data.concurrency_limit || 2} ${interfaceText('active')} · ${((data.total_speed_bps || 0)/1000000).toLocaleString(currentLang,{minimumFractionDigits:2,maximumFractionDigits:2})} MB/s${cap}`;
}
function updateInterfaceTexts() {
 const labels={
 '#settingsTitle':'settings','label[for=settingMode]':'management','#settingMode option[value=auto]':'auto','#settingMode option[value=manual]':'manual',
 '#settingMode + p':'managementHint','.advanced-download-settings summary':'advanced','label[for=settingConcurrent]':'concurrency','.advanced-download-settings p':'manualHint',
 'label[for=settingSpeed]':'speedLimit','#settingSpeed + p':'speedHint','#checkAppUpdateBtn':'checkUpdates','.settings-save':'save',
 '#historyTitle':'history','#historyMore':'more','#playlistTitle':'playlistTitle','#playlistMore':'more','#playlistDownload':'downloadSelected',
 '[onclick="selectPlaylistResults()"]':'selectResults','[onclick="clearPlaylistSelection()"]':'clearSelection',
 '#diagnosticsTitle':'diagTitle','#diagnosticsDescription':'diagDescription','#diagnosticsLoad':'diagShow','#diagnosticsCopy':'diagCopy','#subLabel':'subtitles'
 };
 Object.entries(labels).forEach(([selector,key])=>interfaceLabel(selector,key));
 [['urlInput','paste'],['historySearch','searchHistory'],['playlistSearch','searchPlaylist']].forEach(([id,key])=>{const input=document.getElementById(id);input.placeholder=interfaceText(key);if(id!=='urlInput')input.setAttribute('aria-label',interfaceText(key));});
 document.querySelectorAll('[onclick="closeSettings()"],[onclick="closeFeature(\'playlistModal\')"]').forEach(button=>button.setAttribute('aria-label',interfaceText('close')));
 if(interfaceUpdateState)localizeUpdateStatus(interfaceUpdateState);
 if(interfaceHistoryState)localizeHistory(interfaceHistoryState);
 localizePlaylist();
 document.querySelectorAll('#queueContainer > .queue-item').forEach(localizeQueueRow);
}
document.addEventListener('DOMContentLoaded',()=>{
 updateInterfaceTexts();
 ['playlistModal'].forEach(id=>new MutationObserver(()=>{if(document.getElementById(id).style.display!=='none')updateInterfaceTexts();}).observe(document.getElementById(id),{attributes:true,attributeFilter:['style']}));
});
