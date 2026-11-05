/* Quality policy and stage feedback share the application message catalog. */
function selectedContainer() {
 const value=document.getElementById('videoContainer')?.value || 'mp4';
 return document.getElementById('formatValue').value==='video' && value!=='mp4'?{video_container:value}:{};
}
function queueSnapshotKey(item,lang) {
 return JSON.stringify([lang,{...item,stage_seconds:Math.floor(Number(item.stage_seconds)||0)}]);
}
function updateStabilityTexts() {
 const audio=document.getElementById('formatValue')?.value==='audio';
 const live=typeof inspectedTracks!=='undefined' && !!inspectedTracks?.is_live;
 const panel=document.getElementById('videoContainerPanel'),select=document.getElementById('videoContainer');
 if(!panel || !select)return;
 panel.hidden=audio;
 select.querySelector('[value="mkv"]').disabled=live;
 if(live)select.value='mp4';
 panel.querySelector('label').textContent=appMessage('quality.container');
 document.getElementById('qualityPolicyNote').textContent=appMessage(audio?'quality.audio_note':select.value==='mkv'?'quality.mkv_note':'quality.mp4_note');
 const trigger=document.getElementById('formatText');
 const videoOption=document.querySelector('#formatSelectDiv .custom-option[data-value="video"]');
 if(videoOption)videoOption.textContent=(translations[currentLang]?.video || 'Video (MP4)').replace('MP4','MP4 / MKV');
 if(trigger && !audio)trigger.textContent=(translations[currentLang]?.video || 'Video (MP4)').replace('MP4',select.value.toUpperCase());
}
function stabilityClock(seconds) {
 seconds=Math.max(0,Math.floor(Number(seconds)||0));
 return Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');
}
function decorateStabilityQueue(row,item) {
 const stages=['postprocess','security_check','security_scan','quality_check','preview','saving_file','recovering_file','recording_finalize','remuxing','session_export','session_join'];
 const inStage=['starting','converting'].includes(item.status) && stages.includes(item.phase);
 row.dataset.progressKind=inStage?'stage':!item.total_bytes && item.status==='downloading' && !item.is_live?'unknown':'determinate';
 if(inStage) {
  row.querySelector('.q-speed').textContent=appMessage('phase.'+item.phase)+' · '+stabilityClock(item.stage_seconds);
  row.querySelector('.q-percent').textContent='…';
 }
 if(item.status==='downloading' && !item.total_bytes && !item.is_live)row.querySelector('.q-percent').textContent='…';
 if(item.format==='video')row.querySelector('.q-format').textContent=(item.video_container || 'mp4').toUpperCase();
 const summary=item.quality_summary;
 let label=row.querySelector('.q-quality');
 if(summary && (summary.verified_fields?.length || summary.video_reencoded===false || summary.mismatch)) {
  if(!label){label=document.createElement('p');label.className='q-quality feature-muted';row.querySelector('.queue-info').append(label);}
  const actual=summary.actual || {};
  label.textContent=summary.mismatch?appMessage('error.quality_mismatch'):
   [actual.height?actual.height+'p':'',actual.fps?actual.fps+' fps':'',actual.codec_name || '',appMessage('quality.no_video_encoding')].filter(Boolean).join(' · ');
 } else if(label)label.remove();
}
document.addEventListener('DOMContentLoaded',()=>{
 document.getElementById('videoContainer')?.addEventListener('change',updateStabilityTexts);
 document.getElementById('formatSelectDiv')?.addEventListener('click',()=>queueMicrotask(updateStabilityTexts));
 updateStabilityTexts();
});

function acknowledgeRecordingJoin() {
 const dialog=document.getElementById('recordingJoinDialog'),focus=document.activeElement;
 dialog.querySelectorAll('[data-message]').forEach(node=>node.textContent=appMessage(node.dataset.message));
 dialog.hidden=false;
 return new Promise(resolve=>{
  const done=value=>{dialog.hidden=true;dialog.removeEventListener('keydown',key);focus?.focus();resolve(value);};
  const key=event=>{
   if(event.key==='Escape')done(false);
   if(event.key==='Tab'){event.preventDefault();(document.activeElement===accept?cancel:accept).focus();}
  };
  const accept=document.getElementById('recordingJoinAccept'),cancel=document.getElementById('recordingJoinCancel');
  accept.onclick=()=>done(true);cancel.onclick=()=>done(false);dialog.addEventListener('keydown',key);cancel.focus();
 });
}
async function startRecordingRecovery(id,action,history=false,chooseFolder=false) {
 let acknowledged=false;
 if(action==='join') {acknowledged=await acknowledgeRecordingJoin();if(!acknowledged)return;}
 try {
  if(chooseFolder && !(await selectFolder()))return;
  await postJSON('/recordings/recover',{id,action,history,acknowledge_gaps:acknowledged,use_selected_folder:chooseFolder});
  if(typeof setWorkspaceView==='function')setWorkspaceView('queue');
  startProgressPolling();await pollDownloadProgress();
 } catch(error){showToast(error.message,true);}
}
function decorateRecordingHistory(actions,entry) {
 if(entry.quality_summary?.recovered_parts?.joined) {
  const note=document.createElement('p');note.className='feature-muted';note.dataset.message='session.continuity_unknown';note.textContent=appMessage(note.dataset.message);actions.append(note);
 }
 if(!entry.recording_parts_count)return;
 for(const action of ['export',...(entry.recording_parts_count>1?['join']:[])]) {
  const button=document.createElement('button');button.className='settings-action';button.dataset.message='session.'+action;
  button.textContent=appMessage(button.dataset.message);button.onclick=()=>startRecordingRecovery(entry.id,action,true);actions.append(button);
 }
 const folder=document.createElement('button');folder.className='settings-action';folder.dataset.message='session.export_folder';folder.textContent=appMessage(folder.dataset.message);
 folder.onclick=()=>startRecordingRecovery(entry.id,'export',true,true);actions.append(folder);
}
let recordingOperationsKey='';
function renderRecordingOperations(items) {
 const panel=document.getElementById('recordingOperations');if(!panel)return;
 const key=JSON.stringify([currentLang,items]);if(key===recordingOperationsKey)return;recordingOperationsKey=key;
 panel.hidden=!items.length;panel.replaceChildren();
 for(const item of items.slice(-8)) {
  const line=document.createElement('p');
  line.textContent=item.status==='finished'?appMessage('session.saved',{count:item.saved}):item.status==='cancelled'?appMessage('session.stopped'):
   item.status==='error'?appMessage('error.'+item.error_code):appMessage('phase.'+item.phase)+' · '+(item.current+1)+'/'+item.total;
  panel.append(line);
  if(['queued','running'].includes(item.status)) {
   const stop=document.createElement('button');stop.className='settings-action';stop.textContent=appMessage('session.cancel');
   stop.onclick=()=>postJSON('/recordings/recover',{id:item.id,action:'cancel'}).catch(error=>showToast(error.message,true));panel.append(stop);
  }
 }
}
