/* Source certainty, bounded live recording and opt-in transfer controls. */
const downloadToolLabels={
 tr:['Dosya yapısı tutarlı','Tam erişim henüz doğrulanmadı','Eksik/önizleme kaynağı · tam indirme durduruldu','Canlı yayın kaydı','En fazla kayıt süresi (dakika)','Durdurma zamanı (isteğe bağlı)','Kaydı bitir ve kaydet','Kesintide yeniden bağlanılır. Duraklatıp tekrar başlatmak yeni bir kayıt oluşturur.','Aktarım modu','Kararlı (önerilen)','Ölçerek hızlandır','Hızlı mod, tamamlanan indirmeler arasında en fazla 3 parçayı dener; fayda yoksa veya hata olursa geri döner.','Videoyu tarayıcıda aç','Kaydı başlat','Kaydedilen'],
 en:['Container structure checked','Full access not yet verified','Partial/preview source · full download stopped','Live recording','Maximum recording time (minutes)','Stop at (optional)','Finish and save recording','Reconnects on interruptions. Pausing and restarting creates a new recording.','Transfer mode','Stable (recommended)','Measured acceleration','Fast mode probes up to 3 fragments between completed downloads; rolls back on errors or no benefit.','Open video in browser','Start recording','Recorded'],
 de:['Dateistruktur geprüft','Vollständiger Zugriff noch ungeprüft','Teil-/Vorschauquelle · Download gestoppt','Live-Aufnahme','Maximale Aufnahmezeit (Minuten)','Stoppen um (optional)','Aufnahme beenden und speichern','Verbindet sich bei Unterbrechungen erneut. Ein Neustart erstellt eine neue Aufnahme.','Übertragungsmodus','Stabil (empfohlen)','Gemessene Beschleunigung','Testet bis zu 3 Fragmente zwischen Downloads; setzt bei Fehlern oder ohne Vorteil zurück.','Video im Browser öffnen','Aufnahme starten','Aufgenommen'],
 es:['Estructura verificada','Acceso completo sin verificar','Fuente parcial · descarga completa detenida','Grabación en directo','Duración máxima (minutos)','Detener a las (opcional)','Finalizar y guardar','Reconecta tras interrupciones. Reiniciar crea una grabación nueva.','Modo de transferencia','Estable (recomendado)','Aceleración medida','Prueba hasta 3 fragmentos entre descargas; revierte si hay errores o no mejora.','Abrir vídeo en el navegador','Iniciar grabación','Grabado'],
 fr:['Structure vérifiée','Accès complet non vérifié','Source partielle · téléchargement arrêté','Enregistrement en direct','Durée maximale (minutes)','Arrêter à (facultatif)','Terminer et enregistrer','Reconnexion en cas de coupure. Un redémarrage crée un nouvel enregistrement.','Mode de transfert','Stable (recommandé)','Accélération mesurée',"Teste jusqu’à 3 fragments entre les téléchargements ; revient en arrière en cas d’erreur ou sans gain.",'Ouvrir la vidéo dans le navigateur',"Démarrer l’enregistrement",'Enregistré'],
 pt:['Estrutura verificada','Acesso completo não verificado','Fonte parcial · download completo interrompido','Gravação ao vivo','Duração máxima (minutos)','Parar às (opcional)','Finalizar e salvar','Reconecta após interrupções. Reiniciar cria uma nova gravação.','Modo de transferência','Estável (recomendado)','Aceleração medida','Testa até 3 fragmentos entre downloads; reverte com erros ou sem melhoria.','Abrir vídeo no navegador','Iniciar gravação','Gravado'],
 ru:['Структура проверена','Полный доступ не проверен','Частичный источник · загрузка остановлена','Запись эфира','Максимальное время (минуты)','Остановить в (необязательно)','Завершить и сохранить','Переподключается при обрывах. Перезапуск создаёт новую запись.','Режим передачи','Стабильный (рекомендуется)','Измеряемое ускорение','Проверяет до 3 фрагментов между загрузками; откатывается при ошибках или без прироста.','Открыть видео в браузере','Начать запись','Записано'],
 zh:['文件结构已检查','完整访问尚未验证','部分/预览来源 · 已停止完整下载','直播录制','最长录制时间（分钟）','停止时间（可选）','结束并保存录制','断线后重新连接。暂停后重新开始将创建新录制。','传输模式','稳定（推荐）','测量后加速','在完成下载之间测试最多 3 个分片；出现错误或无提升时回退。','在浏览器中打开视频','开始录制','已录制'],
 ja:['ファイル構造を確認済み','全体へのアクセスは未確認','部分・プレビューソース · ダウンロード停止','ライブ録画','最大録画時間（分）','終了時刻（任意）','録画を終了して保存','切断時に再接続します。再開すると新しい録画になります。','転送モード','安定（推奨）','計測して高速化','ダウンロード間で最大3分割を試し、エラーや改善なしの場合は元に戻します。','ブラウザーで動画を開く','録画を開始','録画済み'],
 hi:['फ़ाइल संरचना जाँची गई','पूर्ण पहुँच सत्यापित नहीं','आंशिक/पूर्वावलोकन स्रोत · डाउनलोड रोका गया','लाइव रिकॉर्डिंग','अधिकतम समय (मिनट)','रुकने का समय (वैकल्पिक)','रिकॉर्डिंग समाप्त करके सहेजें','रुकावट पर फिर जुड़ता है। दोबारा शुरू करने पर नई रिकॉर्डिंग बनती है।','ट्रांसफ़र मोड','स्थिर (अनुशंसित)','मापकर तेज़ करें','डाउनलोड के बीच अधिकतम 3 खंड जाँचता है; त्रुटि या लाभ न मिलने पर वापस लौटता है।','ब्राउज़र में वीडियो खोलें','रिकॉर्डिंग शुरू करें','रिकॉर्ड किया गया']
};
const unknownSizeLabels={tr:'Dosya boyutu kaynak tarafından belirtilmiyor',en:'File size is not declared by the source',de:'Die Quelle gibt keine Dateigröße an',es:'La fuente no indica el tamaño',fr:'La source ne précise pas la taille',pt:'A fonte não informa o tamanho',ru:'Источник не указал размер файла',zh:'来源未提供文件大小',ja:'ソースはファイルサイズを示していません',hi:'स्रोत ने फ़ाइल का आकार नहीं बताया'};
for(const [lang,label] of Object.entries(unknownSizeLabels))downloadToolLabels[lang].push(label);
const liveLimits={tr:'Canlı altyazı desteklenmez; kesintiler kayıtta boşluk oluşturabilir.',en:'Live subtitles are not supported; interruptions may leave gaps.',de:'Live-Untertitel werden nicht unterstützt; Unterbrechungen können Lücken verursachen.',es:'Sin subtítulos en directo; las interrupciones pueden dejar huecos.',fr:'Sans sous-titres en direct ; les coupures peuvent laisser des lacunes.',pt:'Sem legendas ao vivo; interrupções podem deixar lacunas.',ru:'Субтитры эфира не поддерживаются; обрывы могут оставлять пропуски.',zh:'不支持直播字幕；中断可能造成录制缺口。',ja:'ライブ字幕には未対応です。切断で録画に欠落が生じる場合があります。',hi:'लाइव उपशीर्षक समर्थित नहीं हैं; रुकावट से रिकॉर्डिंग में अंतराल आ सकता है।'};
for(const [lang,label] of Object.entries(liveLimits))downloadToolLabels[lang][7]+=' '+label;
const liveRealtime={tr:['Gerçek zamanlı','1 dakikalık canlı yayın yaklaşık 1 dakikada kaydedilir. MB/s, kaydın yaklaşık veri hızıdır; internet bağlantınızın üst sınırı değildir.'],en:['Real time','One minute of live video takes about one minute to record. MB/s is the approximate recording data rate, not your connection limit.'],de:['Echtzeit','Eine Minute Livevideo braucht etwa eine Minute Aufnahmezeit. MB/s zeigt die ungefähre Datenrate der Aufnahme, nicht das Verbindungslimit.'],es:['Tiempo real','Un minuto en directo tarda aproximadamente un minuto en grabarse. MB/s indica la tasa aproximada de grabación, no el límite de conexión.'],fr:['Temps réel','Une minute de direct prend environ une minute à enregistrer. MB/s est le débit approximatif de l’enregistrement, pas la limite de connexion.'],pt:['Tempo real','Um minuto ao vivo leva cerca de um minuto para gravar. MB/s indica a taxa aproximada da gravação, não o limite da conexão.'],ru:['Реальное время','Минута эфира записывается примерно за минуту. MB/s — примерная скорость данных записи, а не предел соединения.'],zh:['实时','录制一分钟直播大约需要一分钟。MB/s 表示录制数据的近似速率，而非连接速度上限。'],ja:['リアルタイム','1分のライブ映像の録画には約1分かかります。MB/sは録画データの概算速度で、回線の上限ではありません。'],hi:['वास्तविक समय','एक मिनट के लाइव वीडियो को रिकॉर्ड करने में लगभग एक मिनट लगता है। MB/s रिकॉर्डिंग की अनुमानित डेटा दर है, कनेक्शन की सीमा नहीं।']};
for(const [lang,copy] of Object.entries(liveRealtime))downloadToolLabels[lang][7]+=' '+copy[1];
function liveClock(seconds){const value=Math.max(0,Math.floor(Number(seconds)||0));return [Math.floor(value/3600),Math.floor(value/60)%60,value%60].map(n=>String(n).padStart(2,'0')).join(':');}
const liveAbout={tr:'Kayıt hakkında',en:'About recording',de:'Über die Aufnahme',es:'Acerca de la grabación',fr:"À propos de l’enregistrement",pt:'Sobre a gravação',ru:'О записи',zh:'关于录制',ja:'録画について',hi:'रिकॉर्डिंग के बारे में'};
for(const [lang,label] of Object.entries(liveAbout))downloadToolLabels[lang].push(label);
let inspectedDownload=null;
function downloadToolText(index){return (downloadToolLabels[currentLang]||downloadToolLabels.en)[index];}
function sourceCertaintyText(data){return downloadToolText(data?.source_status==='partial'?2:data?.source_status==='container_checked'?0:1);}
function setDownloadTools(data){
 const changed=inspectedDownload?.url!==data?.url;inspectedDownload=data;
 if(changed){document.getElementById('liveRecordMinutes').value='60';document.getElementById('liveRecordUntil').value='';}
 updateDownloadToolTexts();
}
function updateDownloadToolTexts(){
 const labels=[[3,'liveRecordingTitle'],[4,'liveRecordMinutesLabel'],[5,'liveRecordUntilLabel'],[7,'liveRecordingHint'],[8,'transferModeLabel'],[11,'transferModeHint'],[12,'companionContinue'],[16,'liveRecordingDetailsLabel']];
 for(const [index,id] of labels){const node=document.getElementById(id);if(node)node.textContent=downloadToolText(index);}
 const select=document.getElementById('settingTransfer');
 if(select){select.options[0].textContent=downloadToolText(9);select.options[1].textContent=downloadToolText(10);}
 const subtitle=document.getElementById('subCheck');
 if(subtitle){subtitle.disabled=!!inspectedDownload?.is_live;if(subtitle.disabled)subtitle.checked=false;}
 if(typeof updateTrackTexts==='function')updateTrackTexts();
 const panel=document.getElementById('liveRecordingOptions');
 if(panel)panel.hidden=!inspectedDownload?.is_live || !singleQualityURL();
 if(typeof updateDownloadButtonText==='function')updateDownloadButtonText();
}
function selectedDownloadTools(){
 if(inspectedDownload?.source_status==='partial')throw new Error(downloadToolText(2));
 if(!inspectedDownload?.is_live || !singleQualityURL())return {};
 const minutes=Number(document.getElementById('liveRecordMinutes').value), raw=document.getElementById('liveRecordUntil').value;
 const until=raw?new Date(raw).getTime()/1000:null;
 if(!Number.isFinite(minutes)||minutes<1||minutes>1440||raw&&!Number.isFinite(until))throw new Error(downloadToolText(4));
 return {live_record_minutes:minutes,live_record_until:until};
}
function decorateLiveQueue(row,item){
 let button=row.querySelector('.queue-finish-recording');
 if(!button && !item.is_live)return;
 if(!button){button=document.createElement('button');button.type='button';button.className='queue-finish-recording settings-action';button.onclick=async()=>{if(await queueCommand('/recording/finish',item.url))startProgressPolling();};(row.querySelector('.queue-info')||row).append(button);}
 button.hidden=!item.is_live || !['starting','downloading'].includes(item.status);button.disabled=!!item.stop_requested;button.textContent=downloadToolText(6);
 if(item.is_live){
  const estimate=row.querySelector('.q-estimate');if(estimate)estimate.textContent=downloadToolText(14)+' · '+liveClock(item.recorded_seconds)+' / '+liveClock(item.recording_limit)+(typeof formatBytes==='function'?' · '+formatBytes(item.downloaded_bytes||0):'');
  if(item.status==='downloading'){const speed=row.querySelector('.q-speed');if(speed)speed.textContent=(liveRealtime[currentLang]||liveRealtime.en)[0]+' · '+((item.recording_speed_bps||0)/1000000).toLocaleString(currentLang,{minimumFractionDigits:2,maximumFractionDigits:2})+' MB/s';}
  const pause=row.querySelector('.queue-pause');if(pause)pause.title=downloadToolText(7);
  const resume=row.querySelector('.queue-resume');if(resume){resume.title=downloadToolText(13);resume.setAttribute('aria-label',downloadToolText(13));}
 }
}
document.addEventListener('DOMContentLoaded',()=>{
 updateDownloadToolTexts();
 document.getElementById('companionContinue').addEventListener('click',async()=>{
  const url=singleQualityURL();if(!url)return;
  try{const response=await fetch('/browser-companion/focus',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});if(!response.ok)throw new Error();}
  catch(_){showToast(downloadToolText(12),true);}
 });
});
