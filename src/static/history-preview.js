let activeHistoryPreview=null;
function stopHistoryPreview() {
 if(!activeHistoryPreview)return;
 const {row,button,panel,media}=activeHistoryPreview;
 media.pause();media.removeAttribute('src');media.load();panel.remove();
 button.setAttribute('aria-expanded','false');activeHistoryPreview=null;
 localizeHistoryPreview(row);
}
function localizeHistoryPreview(row) {
 const button=row.querySelector('.history-preview-toggle');
 if(!button)return;
 const label=interfaceText(button.getAttribute('aria-expanded')==='true'?'closePreview':'preview');
 button.querySelector('span').textContent=label;
 button.setAttribute('aria-label',label+' · '+row.querySelector('.feature-row-title').textContent);
 const error=row.querySelector('.history-preview-error');
 if(error)error.textContent=interfaceText('previewUnsupported');
}
function decorateHistoryPreview(row,entry) {
 row.classList.add('history-record');
 const button=document.createElement('button');button.type='button';button.className='history-preview-toggle';
 button.setAttribute('aria-expanded','false');button.disabled=!entry.file_exists;
 const image=document.createElement('img');image.alt='';image.loading='lazy';updateQueueThumbnail(image,entry.thumbnail);
 const label=document.createElement('span');button.append(image,label);row.prepend(button);
 button.onclick=()=>{
  const wasOpen=activeHistoryPreview?.button===button;stopHistoryPreview();if(wasOpen)return;
  const panel=document.createElement('div');panel.className='history-player';
  const media=document.createElement(entry.format==='video'?'video':'audio');
  media.controls=true;media.preload='metadata';media.setAttribute('aria-label',entry.title);media.setAttribute('playsinline','');
  if(entry.format==='video')media.poster=image.src;
  const error=document.createElement('p');error.className='history-preview-error';error.hidden=true;error.setAttribute('role','status');
  media.onerror=()=>{error.hidden=false;};
  panel.append(media,error);row.append(panel);
  activeHistoryPreview={row,button,panel,media};button.setAttribute('aria-expanded','true');
  media.src='/history/'+encodeURIComponent(entry.id)+'/media';localizeHistoryPreview(row);
 };
 localizeHistoryPreview(row);
}
document.addEventListener('visibilitychange',()=>{if(document.hidden)activeHistoryPreview?.media.pause();});
