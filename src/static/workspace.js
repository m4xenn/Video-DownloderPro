/* Navigation and summaries derive from the existing download queue. */
const workspaceCopy = {
 tr:['Yeni','Kuyruk','Geçmiş','Ayarlar','Ekle','Bağlantı ekleyerek başla','indiriliyor','duraklatıldı','tamamlandı','bekliyor','hata'],
 en:['New','Queue','History','Settings','Add','Start by adding a link','downloading','paused','completed','waiting','failed'],
 de:['Neu','Downloads','Verlauf','Einstellungen','Hinzufügen','Füge einen Link hinzu','aktiv','pausiert','fertig','wartend','fehlgeschlagen'],
 es:['Nueva','Cola','Historial','Ajustes','Añadir','Añade un enlace para empezar','activas','pausadas','completadas','pendientes','fallidas'],
 fr:['Nouveau','File','Historique','Réglages','Ajouter','Ajoutez un lien pour commencer','en cours','en pause','terminés','en attente','en erreur'],
 pt:['Novo','Fila','Histórico','Ajustes','Adicionar','Adicione um link para começar','ativos','pausados','concluídos','aguardando','com falha'],
 ru:['Новая','Очередь','История','Настройки','Добавить','Добавьте ссылку','активно','на паузе','готово','ожидает','ошибка'],
 zh:['新建','队列','历史','设置','添加','添加链接以开始','下载中','已暂停','已完成','等待中','失败'],
 ja:['新規','キュー','履歴','設定','追加','リンクを追加して開始','実行中','一時停止','完了','待機中','失敗'],
 hi:['नया','कतार','इतिहास','सेटिंग्स','जोड़ें','लिंक जोड़कर शुरू करें','सक्रिय','रुके हुए','पूर्ण','प्रतीक्षा','विफल']
};
// These views share one queue DOM and preserve draft inputs and download state.
const queueViewCopy = {
 tr:['Tümü','Aktif','Bekleyen','Duraklatılan','Tamamlanan','Hatalı','Başlık veya bağlantıda ara','Bu aramaya uygun indirme yok.','Filtreleri temizle','Yeni indirme','Bağlantı ekle','İndirmelerini izle, duraklat veya devam ettir. Yeni bağlantılar ve çıktı tercihleri için Yeni indirme’ye dön.','Kuyruğu yönet','Duruma göre filtrele'],
 en:['All','Active','Waiting','Paused','Completed','Failed','Search title or link','No downloads match your search.','Clear filters','New download','Add a link','Track, pause or resume downloads. Return to New download to add links and choose output preferences.','Manage queue','Filter by status'],
 de:['Alle','Aktiv','Wartend','Pausiert','Fertig','Fehler','Titel oder Link suchen','Keine passenden Downloads.','Filter zurücksetzen','Neuer Download','Link hinzufügen','Downloads verfolgen, pausieren oder fortsetzen. Unter Neuer Download Links und Ausgabeoptionen wählen.','Downloads verwalten','Nach Status filtern'],
 es:['Todas','Activas','Pendientes','Pausadas','Completadas','Fallidas','Buscar título o enlace','No hay descargas que coincidan.','Limpiar filtros','Nueva descarga','Añadir enlace','Revisa, pausa o reanuda tus descargas. En Nueva descarga puedes añadir enlaces y elegir el formato.','Gestionar cola','Filtrar por estado'],
 fr:['Tous','En cours','En attente','En pause','Terminés','En erreur','Rechercher un titre ou lien','Aucun téléchargement correspondant.','Effacer les filtres','Nouveau téléchargement','Ajouter un lien','Suivez, suspendez ou reprenez les téléchargements. Ajoutez des liens et choisissez le format dans Nouveau téléchargement.','Gérer la file','Filtrer par état'],
 pt:['Todos','Ativos','Aguardando','Pausados','Concluídos','Com falha','Buscar título ou link','Nenhum download correspondente.','Limpar filtros','Novo download','Adicionar link','Acompanhe, pause ou retome downloads. Volte a Novo download para adicionar links e escolher o formato.','Gerenciar fila','Filtrar por status'],
 ru:['Все','Активные','Ожидают','На паузе','Готовые','Ошибки','Поиск по названию или ссылке','Подходящих загрузок нет.','Сбросить фильтры','Новая загрузка','Добавить ссылку','Следите за загрузками, ставьте на паузу и продолжайте. Ссылки и формат можно выбрать в разделе Новая загрузка.','Управление очередью','Фильтр по состоянию'],
 zh:['全部','下载中','等待中','已暂停','已完成','失败','搜索标题或链接','没有匹配的下载。','清除筛选','新建下载','添加链接','查看、暂停或继续下载。返回新建下载添加链接并选择输出格式。','管理队列','按状态筛选'],
 ja:['すべて','実行中','待機中','一時停止','完了','失敗','タイトル・リンクで検索','一致するダウンロードはありません。','絞り込みを解除','新しいダウンロード','リンクを追加','進行状況の確認、一時停止、再開ができます。リンクの追加と形式の選択は新しいダウンロードから。','キューを管理','状態で絞り込み'],
 hi:['सभी','सक्रिय','प्रतीक्षा','रुके हुए','पूर्ण','विफल','शीर्षक या लिंक खोजें','कोई मिलते डाउनलोड नहीं।','फ़िल्टर हटाएँ','नया डाउनलोड','लिंक जोड़ें','डाउनलोड देखें, रोकें या फिर शुरू करें। लिंक और फ़ॉर्मैट के लिए नया डाउनलोड खोलें।','कतार प्रबंधन','स्थिति के अनुसार फ़िल्टर']
};
function workspaceRowState(row) {
 if(['starting','downloading','processing','merging','converting'].includes(row.dataset.status)) return 'active';
 if(['paused','pausing'].includes(row.dataset.status)) return 'paused';
 if(row.dataset.status==='finished') return 'finished';
 if(row.dataset.status==='error') return 'error';
 return 'waiting';
}
function filterWorkspaceQueue() {
 const inQueue=document.querySelector('.workspace-content').dataset.view==='queue';
 const query=document.getElementById('queueSearch').value.trim().toLocaleLowerCase();
 const filter=document.getElementById('queueFilter').value;
 const rows=[...document.querySelectorAll('#queueContainer > .queue-item')];
 let visible=0;
 rows.forEach(row=>{
  // Full URLs are retained in the source title attribute, not only the short hostname.
  const source=row.querySelector('.queue-url');
  const title=row.querySelector('.queue-title');
  const text=((title?.textContent || '')+' '+(source?.title || '')).toLocaleLowerCase();
  const matches=!inQueue || ((!query || text.includes(query)) && (filter==='all' || workspaceRowState(row)===filter));
  row.hidden=!matches;
  if(matches) visible++;
 });
 document.getElementById('queueNoResults').hidden=!inQueue || !rows.length || visible>0;
 document.getElementById('queueEmptyAction').hidden=rows.length>0;
}
// Cancel unfinished entrances on rapid navigation; keep state changes synchronous.
let workspaceTransition=null, themeSwitchGeneration=0;
function animateWorkspacePanel(panel) {
 if(workspaceTransition) {workspaceTransition.cancel();workspaceTransition=null;}
 if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 workspaceTransition=panel.animate([{opacity:.94,transform:'translateY(6px)'},{opacity:1,transform:'none'}],{duration:180,easing:'cubic-bezier(.2,.7,.2,1)'});
 const animation=workspaceTransition;
 animation.onfinish=()=>{if(workspaceTransition===animation)workspaceTransition=null;};
}
function beginThemeSwitch() {
 if(workspaceTransition){workspaceTransition.cancel();workspaceTransition=null;}
 const generation=++themeSwitchGeneration;
 document.documentElement.classList.add('theme-switching');
 // Apply foregrounds and surfaces in one paint, then restore hover interactions.
 requestAnimationFrame(()=>requestAnimationFrame(()=>{
  if(generation===themeSwitchGeneration)document.documentElement.classList.remove('theme-switching');
 }));
}
const workspaceScrollPositions=new Map();
function setWorkspaceView(view, resetFilters=false) {
 if(resetFilters) { document.getElementById('queueSearch').value=''; document.getElementById('queueFilter').value='all'; }
 const content=document.querySelector('.workspace-content');
 const previousView=content.dataset.view;
 const layout=content.querySelector('.studio-layout');
 workspaceScrollPositions.set(previousView,layout.scrollTop);
 if(view!=='history' && typeof stopHistoryPreview==='function')stopHistoryPreview();
 content.dataset.view=['queue','guide','history','settings'].includes(view)?view:'new';
 if(previousView!==content.dataset.view)layout.scrollTop=workspaceScrollPositions.get(content.dataset.view) || 0;
 const inQueue=content.dataset.view==='queue';
 document.querySelector('.queue-tools').hidden=!inQueue;
 document.querySelectorAll('[data-workspace=new],[data-workspace=queue],[data-workspace=guide],[data-workspace=history],[data-workspace=settings]').forEach(button=>{
  if(button.dataset.workspace===content.dataset.view) button.setAttribute('aria-current','page');
  else button.removeAttribute('aria-current');
 });
 filterWorkspaceQueue();
 const target=content.dataset.view==='settings'?document.getElementById('settingsView'):content.dataset.view==='history'?document.getElementById('historyView'):content.dataset.view==='guide'?document.querySelector('.guide-section'):inQueue?document.querySelector('.queue-panel'):document.getElementById('urlInput');
 if(previousView!==content.dataset.view)animateWorkspacePanel(content.querySelector('.studio-layout'));
 // Avoid centering a long guide/history page and abruptly moving the header away.
 const area=content.querySelector('.studio-layout').getBoundingClientRect();
 if(area.top<0 || area.top>innerHeight-80)content.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
 target.focus({preventScroll:true});
}
function updateWorkspaceQueue() {
 const copy=workspaceCopy[currentLang] || workspaceCopy.en;
 const rows=[...document.querySelectorAll('#queueContainer > .queue-item')];
 const counts={active:0,paused:0,finished:0,error:0,waiting:0};
 rows.forEach(row=>counts[workspaceRowState(row)]++);
 const labels=[['active',6],['paused',7],['finished',8],['waiting',9],['error',10]]
  .filter(([state])=>counts[state]).map(([state,key])=>`${counts[state]} ${copy[key]}`);
 const status=document.getElementById('workspaceQueueStatus');
 const message=labels.length ? labels.join(' · ') : copy[5];
 if(status.textContent!==message) status.textContent=message;
 status.parentElement.dataset.active=String(counts.active>0);
 filterWorkspaceQueue();
}
function updateWorkspaceTexts() {
 const copy=workspaceCopy[currentLang] || workspaceCopy.en;
 const queueCopy=queueViewCopy[currentLang] || queueViewCopy.en;
 const guideLabel=({tr:'Kılavuz',en:'Guide',de:'Anleitung',es:'Guía',fr:'Guide',pt:'Guia',ru:'Помощь',zh:'指南',ja:'ガイド',hi:'गाइड'})[currentLang] || 'Guide';
 const navLabels={new:copy[0],queue:copy[1],history:copy[2],settings:copy[3],guide:guideLabel};
 document.querySelectorAll('.nav-action').forEach(button=>{
  const label=navLabels[button.dataset.workspace];
  button.querySelector('span').textContent=label;
  button.setAttribute('aria-label',label); button.title=label;
 });
 document.getElementById('addLabel').textContent=copy[4];
 document.querySelector('.workspace-nav').setAttribute('aria-label',document.getElementById('queueEyebrow').textContent);
 document.querySelectorAll('#queueFilter option').forEach((option,index)=>option.textContent=queueCopy[index]);
 const search=document.getElementById('queueSearch');
 search.placeholder=queueCopy[6]; search.setAttribute('aria-label',queueCopy[6]);
 document.getElementById('queueFilter').setAttribute('aria-label',queueCopy[13]);
 document.getElementById('queueNoResultsText').textContent=queueCopy[7];
 document.getElementById('queueResetFilters').textContent=queueCopy[8];
 document.getElementById('queueNewDownload').textContent=queueCopy[9];
 document.getElementById('queueEmptyAction').textContent=queueCopy[10];
 document.getElementById('queueViewDescription').textContent=queueCopy[11];
 document.querySelector('#queueExpand span').textContent=queueCopy[12];
 if(typeof updateHelpTexts==='function') updateHelpTexts();
 if(typeof updateInterfaceTexts==='function') updateInterfaceTexts();
 updateWorkspaceQueue();
}
document.addEventListener('DOMContentLoaded',()=>{
 updateWorkspaceTexts();
 document.querySelector('[data-workspace=new]').setAttribute('aria-current','page');
 document.querySelector('[data-workspace=new]').addEventListener('click',()=>setWorkspaceView('new'));
 document.querySelector('[data-workspace=queue]').addEventListener('click',()=>setWorkspaceView('queue'));
 document.querySelector('[data-workspace=guide]').addEventListener('click',()=>setWorkspaceView('guide'));
 document.getElementById('historyNewDownload').addEventListener('click',()=>{
  const search=document.getElementById('historySearch');
  if(search.value.trim()){search.value='';loadHistory();search.focus();}
  else setWorkspaceView('new');
 });
 document.getElementById('queueExpand').addEventListener('click',()=>setWorkspaceView('queue'));
 document.getElementById('queueNewDownload').addEventListener('click',()=>setWorkspaceView('new'));
 document.getElementById('queueEmptyAction').addEventListener('click',()=>setWorkspaceView('new'));
 document.getElementById('queueSearch').addEventListener('input',filterWorkspaceQueue);
 document.getElementById('queueFilter').addEventListener('change',filterWorkspaceQueue);
 document.getElementById('queueResetFilters').addEventListener('click',()=>{
  document.getElementById('queueSearch').value='';
  document.getElementById('queueFilter').value='all';
  filterWorkspaceQueue(); document.getElementById('queueSearch').focus();
 });
 new MutationObserver(updateWorkspaceQueue).observe(document.getElementById('queueContainer'),{childList:true,subtree:true,attributes:true,attributeFilter:['data-status']});
});
