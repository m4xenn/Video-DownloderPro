/* Offline onboarding and illustrated reference. Keep topic IDs stable. */
// Persist in application settings: WebView browser storage may be temporary.
const helpTopics=[
 {id:'start',icon:'fa-link',image:'start.png',tr:{title:'Bir bağlantıyla başla',short:'Bağlantı ekleme',intro:'Video bağlantısını yapıştır. Dosyanın nereye kaydedileceğini seç; tek bağlantıyı doğrudan indir veya birden fazlasını sıraya ekle.',steps:['Video veya playlist bağlantısını Yeni indirme alanına yapıştır. Birden fazla bağlantıyı ayrı satırlara yazabilirsin.','Ekle ile bağlantıları kuyruğa al. Okunamayan bağlantılar, düzeltebilmen için girişte kalır.','Kayıt konumunu ve çıktı tercihlerini kontrol et, ardından İndirmeyi Başlat’a bas.'],tip:'Ekle, indirmeyi başlatmaz. Önce bağlantıları hazırlayıp sonra birlikte başlatabilirsin.'},en:{title:'Start with a link',short:'Adding links',intro:'Paste a video link and choose a save folder. Download one link directly or prepare several in the queue.',steps:['Paste a video or playlist link into New download. Put multiple links on separate lines.','Choose Add to prepare the queue. Links that could not be read stay in the input for correction.','Check the save folder and output preferences, then choose Start download.'],tip:'Add prepares links; it does not start downloading. You can review the queue first.'}},
 {id:'formats',icon:'fa-sliders',image:'formats.png',tr:{title:'Video ya da yalnızca ses',short:'Format ve kalite',intro:'İçeriği MP4 video olarak sakla veya yalnızca sesini indir. Kalite seçenekleri bağlantıdaki kaynağa göre belirlenir.',steps:['Çıktı tercihlerinde Video (MP4) veya Ses seç.','Video için kaynaktaki çözünürlüklerden birini seç; otomatik seçim her video için en yüksek kaliteyi kullanır.','Ses için MP3, M4A, WAV veya Opus seç. Ses Formatları Özellikleri düğmesinden farklarını okuyabilirsin.'],tip:'Yüksek çözünürlük ve WAV daha fazla yer kaplayabilir. Kaynakta bulunmayan bir çözünürlük oluşturulmaz.'},en:{title:'Video or just the audio',short:'Format and quality',intro:'Save an MP4 video or download only its audio. Available video qualities come from the source link.',steps:['Choose Video (MP4) or Audio in Output preferences.','Select a source resolution, or use automatic quality to choose the best available for each video.','For audio, choose MP3, M4A, WAV or Opus. Audio format information explains the differences.'],tip:'High resolution and WAV can take more space. The app does not create resolutions missing from the source.'}},
 {id:'playlist',icon:'fa-list-ul',image:'playlist.png',tr:{title:'Listeden ihtiyacın olanı seç',short:'Playlist ve altyazı',intro:'Bir playlistin tamamını indirmek zorunda değilsin. Listeyi incele, istediğin videoları seç; kaynakta varsa altyazıları da ekle.',steps:['Playlist bağlantısını ekle ve Oynatma Listesi Olarak İndir seçeneğini aç.','İndirmeyi Başlat’a basınca açılan listede ara ve istediğin videoları işaretle. Seçilenleri indir ile devam et.','Video indirirken Altyazı (Soft Sub) seçeneği, kaynakta bulunan altyazıları dosyaya eklemeyi dener.'],tip:'Soft Sub görüntüye kalıcı yazı basmaz; destekleyen oynatıcıda açılıp kapatılabilir. Altyazı bulunması kaynağa bağlıdır.'},en:{title:'Choose what you need from a playlist',short:'Playlists and subtitles',intro:'Select individual playlist videos instead of downloading everything. Include subtitles when the source provides them.',steps:['Add a playlist link and enable Download as playlist.','Choose Start download, search the list and select the videos you want. Continue with Download selected.','When saving video, Subtitles (Soft Sub) attempts to include available source subtitles.'],tip:'Soft subtitles can be switched on or off in a compatible player. Availability depends on the source.'}},
 {id:'queue',icon:'fa-layer-group',image:'queue.png',tr:{title:'İndirmelerin kontrolü sende',short:'Kuyruk yönetimi',intro:'Kuyruk bölümünde ilerlemeyi takip et; indirmeleri duraklat, devam ettir veya bir hata sonrasında yeniden dene.',steps:['Soldaki Kuyruk düğmesi tam genişlikte yönetim ekranını açar.','Başlık veya bağlantıda ara; Aktif, Bekleyen, Duraklatılan, Tamamlanan ya da Hatalı filtresini seç.','Satırdaki düğmelerle duraklat veya devam et. Bir hata varsa ayrıntıyı oku ve tekrar dene.'],tip:'Uygulama önceki oturumdan yarım kalan işleri geri yükleyebilir. Devam etme desteği kaynağa ve dosyanın durumuna bağlıdır.'},en:{title:'Stay in control of your downloads',short:'Managing the queue',intro:'Track progress, pause and resume downloads, or retry after an error from the Queue view.',steps:['Choose Queue in the navigation to open the full management view.','Search by title or link, or filter Active, Waiting, Paused, Completed and Failed jobs.','Use the row controls to pause or resume. Read error details before retrying a failed job.'],tip:'Unfinished jobs can be restored from the previous session. Resuming depends on the source and the partial file.'}},
 {id:'history',icon:'fa-clock-rotate-left',image:'history.png',tr:{title:'İndirdiklerini yeniden bul',short:'İndirme geçmişi',intro:'Geçmiş, tamamlanan indirmelerine geri dönmeni sağlar. Dosyayı aç, klasörüne git veya içeriği yeniden indir.',steps:['Gezinme menüsünden Geçmiş’i aç.','Başlık ya da bağlantıyla arama yap. Her kayıtta format, boyut ve kayıt konumunu inceleyebilirsin.','Dosyayı aç veya Klasörde göster’i kullan. Dosya taşınmış ya da silinmişse Tekrar indir’i seç.'],tip:'Aynı içerik ve çıktı tercihleriyle yeniden indirme yaparken uygulama mevcut dosyaları fark edip onay isteyebilir.'},en:{title:'Find what you downloaded',short:'Download history',intro:'Return to completed downloads, open their files or folders, and download the content again.',steps:['Open History from the navigation.','Search by title or link. Review the format, size and save location for each record.','Choose Open file or Show in folder. If a file was moved or deleted, choose Download again.'],tip:'The app may ask for confirmation when an existing file matches the same content and output preferences.'}},
 {id:'settings',icon:'fa-gear',image:'settings.png',tr:{title:'Çalışma şeklini kendine uyarla',short:'Ayarlar ve güncellemeler',intro:'Aynı anda kaç indirme çalışacağını ve toplam hız sınırını ayarla. Uygulama ve indirme bileşenlerinin güncellemelerini kontrol et.',steps:['Ayarlar’daki Otomatik indirme yönetimiyle başla. Gerekirse Gelişmiş ayarlar’dan manuel eşzamanlı indirme sayısını seç.','Toplam hız sınırını Mbps olarak gir. 0 sınırsızdır; 8 Mbps yaklaşık 1 MB/sn eder. Kaydet’e bas.','Ayarlar’dan uygulama güncellemelerini, üstteki dönen ok düğmesinden yt-dlp ve FFmpeg bileşenlerini kontrol et.'],tip:'Dil ve açık/koyu tema üst çubuktan değişir. Bileşen güncellemesi için internet bağlantısı gerekir.'},en:{title:'Make the app work your way',short:'Settings and updates',intro:'Adjust simultaneous downloads and the total speed limit. Check updates for the app and its download components.',steps:['Start with Automatic download management in Settings. Advanced settings lets you choose a manual concurrency limit.','Enter a total limit in Mbps. 0 means unlimited; 8 Mbps is roughly 1 MB/s. Choose Save.','Check app updates in Settings, and use the top refresh icon for yt-dlp and FFmpeg component updates.'],tip:'Change language and light/dark theme from the top bar. Component updates require an internet connection.'}},
 {id:'troubleshooting',icon:'fa-circle-question',image:'troubleshooting.png',tr:{title:'Takıldığında yardım elinin altında',short:'Sorun giderme',intro:'Kılavuz her zaman menüde. Bir indirme tamamlanamazsa kuyruktaki hata ayrıntıları ve sorun giderme raporu nedenini anlamana yardımcı olur.',steps:['Önce Hatalı kuyruk satırındaki açıklamayı kontrol et. Bağlantıyı, internetini ve kayıt konumunu gözden geçir.','Site doğrulama istiyorsa uygulamadaki Tarayıcıda devam et adımını kullan ve ardından tekrar kontrol et.','Ayarlar → Sorun giderme kayıtları bölümünden kayıtları yükle. Destek isterken raporu kopyalayabilirsin.'],tip:'Bu kılavuz ve ekran görüntüleri uygulamayla birlikte gelir; internet olmadan da açılır. Karşılama turunu istediğin zaman yeniden oynatabilirsin.'},en:{title:'Help is always close by',short:'Troubleshooting',intro:'The Guide stays in the navigation. Queue error details and troubleshooting reports help explain an unsuccessful download.',steps:['Read the failed queue row first. Check the link, connection and save location.','If a site requests verification, use Continue in browser inside the app, then check again.','Open Settings → Troubleshooting records and load the records. Copy the report when asking for support.'],tip:'This guide and its screenshots ship with the app and work offline. Replay the welcome tour whenever you need it.'}}
];
const helpUi={
 tr:{guide:'Kullanım kılavuzu',eyebrow:'HER ADIMDA YANINDA',description:'Bir konu seç; ne işe yaradığını ve nasıl kullanıldığını ekran görüntüsüyle incele.',replay:'Karşılama turunu aç',welcome:'Video Downloader Pro’ya hoş geldin',welcomeDescription:'Bağlantıdan dosyaya: uygulamayı birkaç adımda tanı.',welcomeEyebrow:'BAŞLAMADAN ÖNCE',next:'Sonraki',previous:'Önceki',finish:'Başlayalım',skip:'Şimdilik geç',close:'Kapat',read:'Bu konuyu kılavuzda incele',zoom:'Ekran görüntüsünü büyüt',caption:'Örnek verilerle gerçek uygulama ekranı · Büyütmek için tıkla',tip:'İpucu',steps:'Nasıl kullanılır?',tabs:'Özellikler',swipe:'Sola veya sağa kaydır; ok tuşlarını da kullanabilirsin.'},
 en:{guide:'User guide',eyebrow:'HELP AT EVERY STEP',description:'Choose a topic to learn what it does and how to use it, with a screenshot.',replay:'Replay welcome tour',welcome:'Welcome to Video Downloader Pro',welcomeDescription:'From a link to your file: get to know the app in a few steps.',welcomeEyebrow:'GETTING STARTED',next:'Next',previous:'Previous',finish:'Let’s start',skip:'Skip for now',close:'Close',read:'Read about this in the guide',zoom:'Enlarge screenshot',caption:'Actual app screen with sample data (Turkish) · Click to enlarge',tip:'Tip',steps:'How to use it',tabs:'Features',swipe:'Swipe left or right, or use the arrow keys.'}
};
let welcomeIndex=0, guideTopic='start', welcomeDismissed=false, welcomeTimer, welcomeFrame, welcomeTarget=null;
const helpCopy=()=>helpUi[currentLang==='tr'?'tr':'en'];
const topicCopy=topic=>topic[currentLang==='tr'?'tr':'en'];
const helpImage=topic=>'/static/help/'+(Object.hasOwn(interfaceLocales,currentLang)?currentLang:'en')+'/'+topic.image;
function helpNode(tag,className,text) { const node=document.createElement(tag); if(className) node.className=className; if(text!==undefined) node.textContent=text; return node; }
function helpHasSeenWelcome() { return welcomeDismissed || document.body.dataset.welcomeSeen==='true'; }
function syncWelcome(index) {
 welcomeIndex=Math.max(0,Math.min(helpTopics.length-1,index));
 document.querySelectorAll('#welcomeTabs button').forEach((button,i)=>{button.setAttribute('aria-selected',String(i===welcomeIndex));button.tabIndex=i===welcomeIndex?0:-1;});
 document.querySelectorAll('.welcome-slide').forEach((slide,i)=>{slide.setAttribute('aria-hidden',String(i!==welcomeIndex));slide.inert=i!==welcomeIndex;});
 const copy=helpCopy();
 document.getElementById('welcomePrevious').disabled=welcomeIndex===0;
 document.getElementById('welcomeNext').textContent=welcomeIndex===helpTopics.length-1?copy.finish:copy.next;
 document.getElementById('welcomePosition').textContent=`${welcomeIndex+1} / ${helpTopics.length} · ${topicCopy(helpTopics[welcomeIndex]).short}`;
}
function goWelcome(index, instant=false) {
 syncWelcome(index);
 const track=document.getElementById('welcomeTrack');
 welcomeTarget=welcomeIndex;
 track.scrollTo({left:welcomeIndex*track.clientWidth,behavior:instant || matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
}
function openWelcome() {
 clearTimeout(welcomeTimer);
 document.getElementById('welcomeModal').style.display='flex';
 document.querySelector('main').inert=true;
 document.body.classList.add('welcome-open');
 goWelcome(0,true);
}
function closeWelcome() {
 welcomeDismissed=true;
 fetch('/onboarding/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',keepalive:true})
  .then(response=>{if(response.ok)document.body.dataset.welcomeSeen='true';}).catch(()=>{});
 document.querySelector('main').inert=false;
 document.body.classList.remove('welcome-open');
 document.getElementById('welcomeModal').style.display='none';
}
function openGuideTopic(id) {
 guideTopic=helpTopics.some(topic=>topic.id===id)?id:'start';
 renderGuide(); setWorkspaceView('guide');
}
function renderGuide() {
 const copy=helpCopy(), topic=helpTopics.find(topic=>topic.id===guideTopic), data=topicCopy(topic);
 const tabs=document.getElementById('guideTopics'); tabs.replaceChildren();
 helpTopics.forEach(item=>{
  const button=helpNode('button','guide-topic',topicCopy(item).short); button.type='button';button.id='guide-tab-'+item.id;
  button.setAttribute('role','tab');button.setAttribute('aria-controls','guideArticle');button.setAttribute('aria-selected',String(item.id===guideTopic));button.tabIndex=item.id===guideTopic?0:-1;
  button.addEventListener('click',()=>{if(guideTopic===item.id)return;guideTopic=item.id;renderGuide();if(typeof animateWorkspacePanel==='function')animateWorkspacePanel(document.getElementById('guideArticle'));document.getElementById('guide-tab-'+item.id).focus();}); tabs.append(button);
 });
 const article=document.getElementById('guideArticle');article.setAttribute('aria-labelledby','guide-tab-'+topic.id);article.replaceChildren();
 article.append(helpNode('h3','',data.title),helpNode('p','guide-intro',data.intro));
 const imageButton=helpNode('button','guide-screenshot');imageButton.type='button';imageButton.setAttribute('aria-label',copy.zoom+' · '+data.short);
 const image=helpNode('img');image.src=helpImage(topic);image.alt=data.short;image.loading='lazy';imageButton.append(image);
 imageButton.addEventListener('click',()=>{
  document.getElementById('guideImageTitle').textContent=data.short;
  const large=document.getElementById('guideImageFull');large.src=helpImage(topic);large.alt=data.short;
  document.getElementById('guideImageModal').style.display='flex';
 });
 article.append(imageButton,helpNode('p','guide-caption',interfaceText('caption')),helpNode('h4','',copy.steps));
 const steps=helpNode('ol','guide-steps');data.steps.forEach(text=>steps.append(helpNode('li','',text)));article.append(steps);
 const tip=helpNode('aside','guide-tip');tip.append(helpNode('strong','',copy.tip+' '),document.createTextNode(data.tip));article.append(tip);
}
function updateHelpTexts() {
 const copy=helpCopy();
 const labels={guideTitle:copy.guide,guideEyebrow:copy.eyebrow,guideDescription:copy.description,replayWelcome:copy.replay,welcomeTitle:copy.welcome,welcomeDescription:copy.welcomeDescription+' '+copy.swipe,welcomeEyebrow:copy.welcomeEyebrow,welcomeSkip:copy.skip,welcomeGuide:copy.read,welcomePrevious:copy.previous};
 Object.entries(labels).forEach(([id,text])=>document.getElementById(id).textContent=text);
 ['welcomeClose','guideImageClose'].forEach(id=>document.getElementById(id).setAttribute('aria-label',copy.close));
 document.getElementById('guideTopics').setAttribute('aria-label',copy.tabs);
 document.getElementById('guideTopics').setAttribute('aria-orientation',matchMedia('(max-width:640px)').matches?'horizontal':'vertical');
 document.getElementById('welcomeTabs').setAttribute('aria-label',copy.tabs);
 document.getElementById('welcomeTrack').setAttribute('aria-label',copy.swipe);
 const tabs=document.getElementById('welcomeTabs'),track=document.getElementById('welcomeTrack');tabs.replaceChildren();track.replaceChildren();
 helpTopics.forEach((topic,index)=>{
  const data=topicCopy(topic),tab=helpNode('button','welcome-tab',String(index+1));tab.type='button';tab.id='welcome-tab-'+topic.id;
  tab.title=data.short;tab.setAttribute('role','tab');tab.setAttribute('aria-label',data.short);tab.setAttribute('aria-controls','welcome-slide-'+topic.id);
  tab.addEventListener('click',()=>goWelcome(index));tabs.append(tab);
  const slide=helpNode('section','welcome-slide');slide.id='welcome-slide-'+topic.id;slide.setAttribute('role','tabpanel');slide.setAttribute('aria-labelledby',tab.id);
  const text=helpNode('div','welcome-slide-copy'),icon=helpNode('i','fa-solid '+topic.icon);icon.setAttribute('aria-hidden','true');
  text.append(icon,helpNode('h4','',data.title),helpNode('p','',data.intro));
  const hint=helpNode('p','welcome-hint',data.tip);text.append(hint);
  const image=helpNode('img','welcome-image');image.src=helpImage(topic);image.alt=data.short;image.loading=index===0?'eager':'lazy';
  slide.append(text,image);track.append(slide);
 });
 syncWelcome(welcomeIndex);renderGuide();
 if(document.getElementById('welcomeModal').style.display==='flex') goWelcome(welcomeIndex,true);
}
document.addEventListener('DOMContentLoaded',()=>{
 updateHelpTexts();
 new ResizeObserver(()=>document.getElementById('guideTopics').setAttribute('aria-orientation',matchMedia('(max-width:640px)').matches?'horizontal':'vertical')).observe(document.getElementById('guideTopics'));
 document.getElementById('replayWelcome').addEventListener('click',openWelcome);
 ['welcomeClose','welcomeSkip'].forEach(id=>document.getElementById(id).addEventListener('click',closeWelcome));
 document.getElementById('welcomePrevious').addEventListener('click',()=>goWelcome(welcomeIndex-1));
 document.getElementById('welcomeNext').addEventListener('click',()=>{
  if(welcomeIndex===helpTopics.length-1) {closeWelcome();requestAnimationFrame(()=>{setWorkspaceView('new');});}
  else goWelcome(welcomeIndex+1);
 });
 document.getElementById('welcomeGuide').addEventListener('click',()=>{
  const topic=helpTopics[welcomeIndex].id;closeWelcome();requestAnimationFrame(()=>openGuideTopic(topic));
 });
 document.getElementById('guideImageClose').addEventListener('click',()=>closeFeature('guideImageModal'));
 const track=document.getElementById('welcomeTrack');
 track.addEventListener('scroll',()=>{cancelAnimationFrame(welcomeFrame);welcomeFrame=requestAnimationFrame(()=>{if(track.clientWidth && (welcomeTarget===null || Math.abs(track.scrollLeft-welcomeTarget*track.clientWidth)<2)){syncWelcome(Math.round(track.scrollLeft/track.clientWidth));welcomeTarget=null;}});});
 track.addEventListener('pointerdown',()=>{welcomeTarget=null;});
 track.addEventListener('touchstart',()=>{welcomeTarget=null;},{passive:true});
 track.addEventListener('wheel',()=>{welcomeTarget=null;},{passive:true});
 new ResizeObserver(()=>{if(document.getElementById('welcomeModal').style.display==='flex')goWelcome(welcomeIndex,true);}).observe(track);
 // Horizontal touch swipes use the browser's native scrolling and snap points.
 document.getElementById('welcomeTabs').addEventListener('keydown',event=>{
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();
  goWelcome(event.key==='Home'?0:event.key==='End'?helpTopics.length-1:welcomeIndex+(event.key==='ArrowRight'?1:-1));
  document.querySelector('#welcomeTabs [aria-selected=true]').focus();
 });
 track.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();goWelcome(welcomeIndex+(event.key==='ArrowRight'?1:-1));}});
 document.getElementById('guideTopics').addEventListener('keydown',event=>{
  if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key))return;
  event.preventDefault();const index=helpTopics.findIndex(topic=>topic.id===guideTopic);
  const next=event.key==='Home'?0:event.key==='End'?helpTopics.length-1:(index+(['ArrowRight','ArrowDown'].includes(event.key)?1:-1)+helpTopics.length)%helpTopics.length;
  if(next===index)return;guideTopic=helpTopics[next].id;renderGuide();if(typeof animateWorkspacePanel==='function')animateWorkspacePanel(document.getElementById('guideArticle'));document.getElementById('guide-tab-'+guideTopic).focus();
 });
 function maybeWelcome() {
  if(helpHasSeenWelcome())return;
  const other=[...document.querySelectorAll('.feature-overlay,#appUpdateModal,#formatInfoModal,#updateOverlay')].some(node=>node.id!=='welcomeModal' && getComputedStyle(node).display!=='none');
  if(other)welcomeTimer=setTimeout(maybeWelcome,500);else openWelcome();
 }
 welcomeTimer=setTimeout(maybeWelcome,300);
 window.addEventListener('pagehide',()=>clearTimeout(welcomeTimer));
});
