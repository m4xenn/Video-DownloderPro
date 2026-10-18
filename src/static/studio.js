/* UI behavior only: keyboard access, dialog focus and queue presentation. */
const studioCopy = {
    tr: ['SANA AİT BİR KOLEKSİYON','Sevdiğin içerikler.','Her zaman yanında.','Bir bağlantıyla başla. Gerisini bize bırak.','Video veya playlist bağlantısı','Kayıt konumu','Çıktı tercihleri','ÇALIŞMA ALANIN','İndirme kuyruğu','Sıradaki favorin burada.','Bir bağlantı eklediğinde indirmelerin bu alanda görünecek.','İndirme geçmişini aç','Dosyaların, seçtiğin klasörde.'],
    en: ['A COLLECTION OF YOUR OWN','The things you love.','Always with you.','Start with a link. We’ll take it from here.','Video or playlist link','Save location','Output preferences','YOUR WORKSPACE','Download queue','Your next favorite starts here.','Add a link and your downloads will appear here.','Open download history','Your files, in your chosen folder.'],
    de: ['DEINE EIGENE SAMMLUNG','Deine Lieblingsinhalte.','Immer dabei.','Beginne mit einem Link. Wir erledigen den Rest.','Video- oder Playlist-Link','Speicherort','Ausgabeoptionen','DEIN ARBEITSBEREICH','Downloads','Hier beginnt dein nächster Favorit.','Füge einen Link hinzu, um deine Downloads zu sehen.','Downloadverlauf öffnen','Deine Dateien, in deinem Ordner.'],
    es: ['TU PROPIA COLECCIÓN','Lo que te encanta.','Siempre contigo.','Empieza con un enlace. Nosotros nos encargamos.','Enlace de vídeo o lista','Guardar en','Preferencias de salida','TU ESPACIO','Descargas','Tu próximo favorito empieza aquí.','Añade un enlace para ver tus descargas aquí.','Abrir historial','Tus archivos, en tu carpeta.'],
    fr: ['VOTRE COLLECTION','Ce que vous aimez.','Toujours avec vous.','Un lien suffit. Nous faisons le reste.','Lien vidéo ou playlist','Dossier de destination','Options de sortie','VOTRE ESPACE','Téléchargements','Votre prochain favori commence ici.','Ajoutez un lien pour voir vos téléchargements ici.','Ouvrir l’historique','Vos fichiers, dans votre dossier.'],
    pt: ['A SUA COLEÇÃO','O que você adora.','Sempre com você.','Comece com um link. Nós cuidamos do resto.','Link de vídeo ou playlist','Salvar em','Opções de saída','SEU ESPAÇO','Downloads','Seu próximo favorito começa aqui.','Adicione um link para ver seus downloads aqui.','Abrir histórico','Seus arquivos, na sua pasta.'],
    ru: ['ВАША КОЛЛЕКЦИЯ','Любимый контент.','Всегда с вами.','Начните со ссылки. Остальное сделаем мы.','Ссылка на видео или плейлист','Папка сохранения','Параметры','ВАШЕ ПРОСТРАНСТВО','Очередь загрузок','Здесь будет ваш следующий фаворит.','Добавьте ссылку, чтобы увидеть загрузки.','Открыть историю','Ваши файлы — в выбранной папке.'],
    zh: ['你的专属收藏','喜爱的内容。','始终相伴。','从一个链接开始，剩下的交给我们。','视频或播放列表链接','保存位置','输出选项','工作空间','下载队列','下一份喜爱从这里开始。','添加链接后，下载将在此处显示。','打开下载历史','文件保存在你选择的文件夹中。'],
    ja: ['あなただけのコレクション','お気に入りを。','いつもそばに。','リンクを追加。あとはおまかせ。','動画・再生リストのリンク','保存先','出力設定','ワークスペース','ダウンロード','次のお気に入りはここから。','リンクを追加すると、ここに表示されます。','履歴を開く','ファイルは選んだフォルダに。'],
    hi: ['आपका अपना संग्रह','पसंदीदा सामग्री।','हमेशा आपके साथ।','एक लिंक से शुरू करें। बाकी हम संभालेंगे।','वीडियो या प्लेलिस्ट लिंक','सहेजने का स्थान','आउटपुट विकल्प','आपका कार्यक्षेत्र','डाउनलोड कतार','आपका अगला पसंदीदा यहाँ है।','लिंक जोड़ें और डाउनलोड यहाँ दिखेंगे।','डाउनलोड इतिहास खोलें','आपकी फ़ाइलें, आपके चुने फ़ोल्डर में।']
};
function updateStudioTexts() {
    const copy = studioCopy[currentLang] || studioCopy.en;
    document.querySelector('.subtitle').textContent = 'Video & Audio';
    document.getElementById('urlInput').placeholder = currentLang === 'tr' ? 'Bir veya birden fazla bağlantı yapıştır…' : 'Paste one or more links…';
    const ids = ['studioEyebrow',null,null,'studioDescription','linkFieldLabel','destinationLabel','outputLabel','queueEyebrow','queueTitle','emptyTitle','emptyDescription','historyLinkLabel'];
    ids.forEach((id,index) => { if(id) document.getElementById(id).textContent = copy[index]; });
    const title = document.getElementById('studioTitle');
    const accent = document.createElement('span'); accent.textContent = copy[2];
    title.replaceChildren(document.createTextNode(copy[1]),document.createElement('br'),accent);
    const quiet = ({
        tr:['Yeni indirme','Bağlantıları ekle, formatı seç ve indir.','Henüz indirme yok','Eklediğin bağlantılar burada görünecek.','Geçmiş'],
        en:['New download','Add links, choose a format and download.','No downloads yet','Your links will appear here.','History'],
        de:['Neuer Download','Links hinzufügen, Format wählen und laden.','Noch keine Downloads','Deine Links erscheinen hier.','Verlauf'],
        es:['Nueva descarga','Añade enlaces, elige formato y descarga.','Sin descargas','Tus enlaces aparecerán aquí.','Historial'],
        fr:['Nouveau téléchargement','Ajoutez des liens et choisissez un format.','Aucun téléchargement','Vos liens apparaîtront ici.','Historique'],
        pt:['Novo download','Adicione links, escolha o formato e baixe.','Nenhum download','Seus links aparecerão aqui.','Histórico'],
        ru:['Новая загрузка','Добавьте ссылки и выберите формат.','Загрузок пока нет','Ваши ссылки появятся здесь.','История'],
        zh:['新建下载','添加链接，选择格式并下载。','暂无下载','添加的链接将在此显示。','历史记录'],
        ja:['新しいダウンロード','リンクを追加して形式を選択。','ダウンロードはありません','追加したリンクがここに表示されます。','履歴'],
        hi:['नया डाउनलोड','लिंक जोड़ें, फ़ॉर्मैट चुनें और डाउनलोड करें।','अभी कोई डाउनलोड नहीं','आपके लिंक यहाँ दिखाई देंगे।','इतिहास']
    })[currentLang] || ['New download','Add links, choose a format and download.','No downloads yet','Your links will appear here.','History'];
    title.textContent = quiet[0];
    document.getElementById('studioDescription').textContent = quiet[1];
    document.getElementById('emptyTitle').textContent = quiet[2];
    document.getElementById('emptyDescription').textContent = quiet[3];
    document.getElementById('historyLinkLabel').textContent = quiet[4];
    document.getElementById('platformFootnote').textContent = 'Video Downloader Pro · MP4 / MP3 / WAV / M4A / Opus';
    document.querySelector('#studioFootnote span').textContent = copy[12];
    document.documentElement.lang = currentLang;
    document.getElementById('addBtn').setAttribute('aria-label', currentLang === 'tr' ? 'Sıraya ekle' : 'Add to queue');
    document.querySelectorAll('.custom-select__trigger').forEach(trigger => {
        const id = trigger.parentElement.id;
        const label = id === 'langSelectDiv' ? (currentLang === 'tr' ? 'Dil' : 'Language')
            : id === 'formatSelectDiv' ? (currentLang === 'tr' ? 'Dosya formatı' : 'File format')
            : (currentLang === 'tr' ? 'Kalite' : 'Quality');
        trigger.setAttribute('aria-label',label);
    });
}
document.addEventListener('DOMContentLoaded', () => {
    updateStudioTexts();
    const queue = document.getElementById('queueContainer');
    function syncQueue() {
        const count = queue.children.length;
        document.getElementById('queueCount').textContent = count;
        document.getElementById('queueEmpty').style.display = count ? 'none' : 'flex';
    }
    new MutationObserver(syncQueue).observe(queue,{childList:true}); syncQueue();
    document.querySelectorAll('.custom-select__trigger').forEach(trigger => {
        trigger.tabIndex = 0; trigger.setAttribute('role','button'); trigger.setAttribute('aria-haspopup','true');
        const select = trigger.parentElement;
        new MutationObserver(() => trigger.setAttribute('aria-expanded',String(select.classList.contains('open')))).observe(select,{attributes:true,attributeFilter:['class']});
        trigger.setAttribute('aria-expanded','false');
    });
    document.addEventListener('keydown', event => {
        const option = event.target.closest('.custom-option');
        const trigger = event.target.closest('.custom-select__trigger');
        if ((option || trigger) && ['Enter',' ','ArrowDown','ArrowUp','Escape'].includes(event.key)) {
            event.preventDefault();
            const select = event.target.closest('.custom-select');
            const items = [...select.querySelectorAll('.custom-option')];
            items.forEach(item => item.tabIndex = -1);
            if (event.key === 'Escape') { select.classList.remove('open'); select.querySelector('.custom-select__trigger').focus(); }
            else if (event.key === 'Enter' || event.key === ' ') { event.target.click(); }
            else {
                select.classList.add('open');
                const position = items.indexOf(option);
                const next = event.key === 'ArrowDown' ? (position + 1) % items.length : (position <= 0 ? items.length - 1 : position - 1);
                items[next]?.focus();
            }
        }
    });
    const dialogs = [...document.querySelectorAll('.feature-overlay,#settingsModal,#appUpdateModal,#formatInfoModal,#updateOverlay')];
    const openers = new WeakMap();
    const visible = node => node.style.display !== 'none' && getComputedStyle(node).display !== 'none';
    const focusable = node => [...node.querySelectorAll('button:not(:disabled),input:not([type=hidden]):not(:disabled),select:not(:disabled),summary,[tabindex="0"]')].filter(item => item.getClientRects().length);
    dialogs.forEach(dialog => {
        if (!dialog.hasAttribute('role')) { dialog.setAttribute('role','dialog'); dialog.setAttribute('aria-modal','true'); }
        if (!dialog.hasAttribute('aria-labelledby')) { const title = dialog.querySelector('h3'); if(title) { title.id ||= dialog.id+'Heading'; dialog.setAttribute('aria-labelledby',title.id); } }
        new MutationObserver(() => {
            if (visible(dialog)) {
                if (!openers.has(dialog)) { openers.set(dialog,document.activeElement); focusable(dialog)[0]?.focus(); }
            } else if (openers.has(dialog)) {
                const opener = openers.get(dialog); openers.delete(dialog);
                if (opener?.isConnected) opener.focus();
            }
        }).observe(dialog,{attributes:true,attributeFilter:['style']});
        dialog.querySelectorAll('button').forEach(button => { if(!button.textContent.trim() && !button.hasAttribute('aria-label')) button.setAttribute('aria-label','Kapat'); });
    });
    document.addEventListener('keydown', event => {
        const dialog = dialogs.filter(visible).sort((a,b) => Number(getComputedStyle(b).zIndex)-Number(getComputedStyle(a).zIndex))[0];
        if(!dialog) return;
        if(event.key==='Escape') {
            const close = {settingsModal:closeSettings,appUpdateModal:closeAppUpdate,formatInfoModal:closeFormatInfo,updateOverlay:closeComponentUpdate,duplicateModal:cancelDuplicate};
            event.preventDefault(); (close[dialog.id] || (()=>closeFeature(dialog.id)))();
        } else if(event.key==='Tab') {
            const items=focusable(dialog); if(!items.length) return;
            if(event.shiftKey && (document.activeElement===items[0] || !dialog.contains(document.activeElement))) { event.preventDefault(); items.at(-1).focus(); }
            else if(!event.shiftKey && (document.activeElement===items.at(-1) || !dialog.contains(document.activeElement))) { event.preventDefault(); items[0].focus(); }
        }
    });
});
