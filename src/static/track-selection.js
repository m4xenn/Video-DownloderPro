/* Only offer languages declared by the inspected source. */
const trackLabels={
 tr:['Ses dili','Altyazı dili','Otomatik','Tüm diller','Kaynağın sunduğu diller · tek video'],
 en:['Audio language','Subtitle language','Automatic','All languages','Source languages · single video'],
 de:['Audiosprache','Untertitelsprache','Automatisch','Alle Sprachen','Quellsprachen · einzelnes Video'],
 es:['Idioma de audio','Idioma de subtítulos','Automático','Todos los idiomas','Idiomas de origen · un vídeo'],
 fr:['Langue audio','Langue des sous-titres','Automatique','Toutes les langues','Langues de la source · une vidéo'],
 pt:['Idioma do áudio','Idioma das legendas','Automático','Todos os idiomas','Idiomas da fonte · um vídeo'],
 ru:['Язык аудио','Язык субтитров','Автоматически','Все языки','Языки источника · одно видео'],
 zh:['音频语言','字幕语言','自动','所有语言','来源提供的语言 · 单个视频'],
 ja:['音声言語','字幕言語','自動','すべての言語','ソースの言語 · 単一動画'],
 hi:['ऑडियो भाषा','उपशीर्षक भाषा','स्वचालित','सभी भाषाएँ','स्रोत की भाषाएँ · एक वीडियो']
};
let inspectedTracks=null;
function setTrackChoices(data) {
 const changed=inspectedTracks?.url!==data?.url;
 inspectedTracks=data;
 updateTrackTexts(changed);
}
function updateTrackTexts(reset=false) {
 const labels=trackLabels[currentLang] || trackLabels.en;
 const panel=document.getElementById('trackChoices');if(!panel)return;
 const single=!!inspectedTracks && !inspectedTracks.is_playlist && typeof singleQualityURL==='function' && !!singleQualityURL();
 panel.hidden=!single || !(inspectedTracks.audio_languages?.length || inspectedTracks.subtitle_languages?.length);
 for(const [index,id,key,defaultValue] of [[0,'audioLanguage','audio_languages','auto'],[1,'subtitleLanguage','subtitle_languages','all']]) {
  const select=document.getElementById(id), previous=reset?defaultValue:select.value;
  document.getElementById(id+'Label').textContent=labels[index];
  const languages=single ? inspectedTracks[key] || [] : [];
  const choices=[[defaultValue,labels[index+2]],...languages.map(code=>{
   let label=code;try{label=new Intl.DisplayNames([currentLang],{type:'language'}).of(code.replaceAll('_','-')) || code;}catch(_){}
   return [code,label+' ('+code+')'];
  })];
  select.replaceChildren(...choices.map(([value,label])=>new Option(label,value)));
  select.value=choices.some(([value])=>value===previous)?previous:defaultValue;
  select.disabled=!single || !languages.length || (index===1 && (inspectedTracks?.is_live || !document.getElementById('subCheck').checked || document.getElementById('formatValue').value==='audio'));
 }
 document.getElementById('trackHint').textContent=labels[4];
}
function selectedTracks() {
 updateTrackTexts();
 return {audio_language:document.getElementById('audioLanguage').value,
  subtitle_language:document.getElementById('subtitleLanguage').disabled?'all':document.getElementById('subtitleLanguage').value};
}
document.addEventListener('DOMContentLoaded',()=>{
 document.getElementById('subCheck').addEventListener('change',()=>updateTrackTexts());
 document.getElementById('formatSelectDiv').addEventListener('click',()=>queueMicrotask(()=>updateTrackTexts()));
 updateTrackTexts();
});

function previewScopeText() {
 return ({tr:'Önizleme kaynağı · tam video doğrulanmadı',en:'Preview source · full video not verified',de:'Vorschauquelle · vollständiges Video nicht bestätigt',es:'Vista previa · vídeo completo sin verificar',fr:'Source de prévisualisation · vidéo complète non vérifiée',pt:'Prévia · vídeo completo não verificado',ru:'Предпросмотр · полное видео не подтверждено',zh:'预览来源 · 完整视频未经验证',ja:'プレビュー · 動画全体は未確認',hi:'पूर्वावलोकन · पूरा वीडियो सत्यापित नहीं'})[currentLang] || 'Preview source · full video not verified';
}
