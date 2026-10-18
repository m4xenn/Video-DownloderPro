import re

with open(r"C:\Users\salih\Desktop\HTML\YoutubePro\templates\index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Add translation dictionary and language selector logic in JavaScript
i18n_script = """
        // --- i18n LOGIC ---
        const translations = {
            tr: {
                flag: "🇹🇷", name: "Türkçe",
                title: "Studio Downloader", sub: "Premium Video & Audio Converter",
                defPath: "Lütfen Klasör Seçiniz...", placeholder: "Link yapıştırın ve Enter'a basın...",
                video: "Video (MP4)", audio: "Ses (MP3/WAV)", maxQuality: "En Yüksek",
                formatInfo: "Ses Formatları Özellikleri", playlist: "Oynatma Listesi Olarak İndir",
                startBtn: "İndirmeyi Başlat",
                startBtnWait: "Başlatılıyor...", downloading: "İndiriliyor...", converting: "Dönüştürülüyor...",
                finishedAll: "Tüm İndirmeler Tamamlandı!", errUnknown: "Bilinmeyen",
                errPrefix: "Hata:", tSuccess: "İşlem Başarılı!", tErrPath: "Lütfen klasör seçin!",
                tErrLink: "Link girmediniz!", tErrQueue: "Sırada indirilecek link yok!",
                tErrExist: "Bu link zaten sırada!", tErrInfo: "Video bilgisi alınamadı!", tErrConn: "Bağlantı hatası!",
                bottom1: "1000'den fazla platformdan dilediğiniz videoyu indirebilir ve",
                bottom2: "aktif canlı yayınları anlık olarak cihazınıza kaydedebilirsiniz!",
                modalTitle: "Ses Formatları Bilgisi",
                mp3d: "İdeal kalite ve boyut dengesi.", mp3c: "Şarkı kapağı destekler.",
                wavd: "Kayıpsız, en yüksek ses kalitesi ancak dosya boyutu büyüktür.", wavc: "Şarkı kapağı desteklemez.",
                opusd: "Düşük boyutta yüksek kalite sunan modern bir formattır.", opusc: "Şarkı kapağı desteklemez.",
                okBtn: "Anladım"
            },
            en: {
                flag: "🇬🇧", name: "English",
                title: "Studio Downloader", sub: "Premium Video & Audio Converter",
                defPath: "Please Select a Folder...", placeholder: "Paste link and press Enter...",
                video: "Video (MP4)", audio: "Audio (MP3/WAV)", maxQuality: "Highest",
                formatInfo: "Audio Format Features", playlist: "Download as Playlist",
                startBtn: "Start Download",
                startBtnWait: "Starting...", downloading: "Downloading...", converting: "Converting...",
                finishedAll: "All Downloads Completed!", errUnknown: "Unknown",
                errPrefix: "Error:", tSuccess: "Operation Successful!", tErrPath: "Please select a folder!",
                tErrLink: "No link entered!", tErrQueue: "Queue is empty!",
                tErrExist: "This link is already in queue!", tErrInfo: "Failed to fetch video info!", tErrConn: "Connection error!",
                bottom1: "Download videos from over 1000+ platforms and",
                bottom2: "record active live streams to your device instantly!",
                modalTitle: "Audio Formats Info",
                mp3d: "Ideal balance of quality and size.", mp3c: "Supports cover art.",
                wavd: "Lossless, highest audio quality but large file size.", wavc: "No cover art support.",
                opusd: "Modern format offering high quality at small size.", opusc: "No cover art support.",
                okBtn: "Got it"
            },
            es: {
                flag: "🇪🇸", name: "Español",
                title: "Studio Downloader", sub: "Premium Video & Audio Converter",
                defPath: "Seleccione una carpeta...", placeholder: "Pegue el enlace y presione Enter...",
                video: "Video (MP4)", audio: "Audio (MP3/WAV)", maxQuality: "Máxima",
                formatInfo: "Características del Formato", playlist: "Descargar como Lista",
                startBtn: "Iniciar Descarga",
                startBtnWait: "Iniciando...", downloading: "Descargando...", converting: "Convirtiendo...",
                finishedAll: "¡Todas las descargas completadas!", errUnknown: "Desconocido",
                errPrefix: "Error:", tSuccess: "¡Operación Exitosa!", tErrPath: "¡Seleccione una carpeta!",
                tErrLink: "¡No se ingresó enlace!", tErrQueue: "¡La cola está vacía!",
                tErrExist: "¡Este enlace ya está en la cola!", tErrInfo: "¡Fallo al obtener información!", tErrConn: "¡Error de conexión!",
                bottom1: "Descarga videos de más de 1000+ plataformas y",
                bottom2: "graba transmisiones en vivo activas al instante!",
                modalTitle: "Información de Formatos",
                mp3d: "Equilibrio ideal entre calidad y tamaño.", mp3c: "Soporta carátula.",
                wavd: "Sin pérdida, máxima calidad pero tamaño grande.", wavc: "No soporta carátula.",
                opusd: "Formato moderno de alta calidad en tamaño reducido.", opusc: "No soporta carátula.",
                okBtn: "Entendido"
            },
            fr: {
                flag: "🇫🇷", name: "Français",
                title: "Studio Downloader", sub: "Premium Video & Audio Converter",
                defPath: "Veuillez choisir un dossier...", placeholder: "Collez le lien et appuyez sur Entrée...",
                video: "Vidéo (MP4)", audio: "Audio (MP3/WAV)", maxQuality: "Maximale",
                formatInfo: "Caractéristiques du Format", playlist: "Télécharger en Playlist",
                startBtn: "Démarrer le Téléchargement",
                startBtnWait: "Démarrage...", downloading: "Téléchargement...", converting: "Conversion...",
                finishedAll: "Tous les téléchargements terminés !", errUnknown: "Inconnu",
                errPrefix: "Erreur:", tSuccess: "Opération réussie !", tErrPath: "Veuillez choisir un dossier !",
                tErrLink: "Aucun lien saisi !", tErrQueue: "La file est vide !",
                tErrExist: "Ce lien est déjà dans la file !", tErrInfo: "Échec d'obtention des infos !", tErrConn: "Erreur de connexion !",
                bottom1: "Téléchargez des vidéos sur plus de 1000 plateformes et",
                bottom2: "enregistrez les diffusions en direct instantanément !",
                modalTitle: "Infos Formats Audio",
                mp3d: "Équilibre idéal qualité/taille.", mp3c: "Prend en charge la pochette.",
                wavd: "Sans perte, très haute qualité mais fichier lourd.", wavc: "Pas de pochette.",
                opusd: "Format moderne offrant une haute qualité pour une petite taille.", opusc: "Pas de pochette.",
                okBtn: "Compris"
            },
            de: {
                flag: "🇩🇪", name: "Deutsch",
                title: "Studio Downloader", sub: "Premium Video & Audio Converter",
                defPath: "Bitte Ordner wählen...", placeholder: "Link einfügen und Enter drücken...",
                video: "Video (MP4)", audio: "Audio (MP3/WAV)", maxQuality: "Höchste",
                formatInfo: "Audioformat-Funktionen", playlist: "Als Playlist Herunterladen",
                startBtn: "Download Starten",
                startBtnWait: "Startet...", downloading: "Wird heruntergeladen...", converting: "Wird konvertiert...",
                finishedAll: "Alle Downloads Abgeschlossen!", errUnknown: "Unbekannt",
                errPrefix: "Fehler:", tSuccess: "Erfolgreich!", tErrPath: "Bitte Ordner wählen!",
                tErrLink: "Kein Link eingegeben!", tErrQueue: "Warteschlange ist leer!",
                tErrExist: "Link ist bereits in der Warteschlange!", tErrInfo: "Video-Info konnte nicht abgerufen werden!", tErrConn: "Verbindungsfehler!",
                bottom1: "Lade Videos von über 1000+ Plattformen herunter und",
                bottom2: "zeichne Live-Streams sofort auf deinem Gerät auf!",
                modalTitle: "Audioformate Info",
                mp3d: "Ideales Gleichgewicht zwischen Qualität und Größe.", mp3c: "Unterstützt Cover.",
                wavd: "Verlustfrei, höchste Qualität, aber große Datei.", wavc: "Kein Cover.",
                opusd: "Modernes Format mit hoher Qualität bei kleiner Größe.", opusc: "Kein Cover.",
                okBtn: "Verstanden"
            },
            ru: {
                flag: "🇷🇺", name: "Русский",
                title: "Studio Downloader", sub: "Premium Video & Audio Converter",
                defPath: "Пожалуйста, выберите папку...", placeholder: "Вставьте ссылку и нажмите Enter...",
                video: "Видео (MP4)", audio: "Аудио (MP3/WAV)", maxQuality: "Лучшее",
                formatInfo: "Особенности форматов", playlist: "Скачать как плейлист",
                startBtn: "Начать скачивание",
                startBtnWait: "Запуск...", downloading: "Скачивание...", converting: "Конвертация...",
                finishedAll: "Все загрузки завершены!", errUnknown: "Неизвестно",
                errPrefix: "Ошибка:", tSuccess: "Успешно!", tErrPath: "Выберите папку!",
                tErrLink: "Ссылка не введена!", tErrQueue: "Очередь пуста!",
                tErrExist: "Эта ссылка уже в очереди!", tErrInfo: "Не удалось получить информацию!", tErrConn: "Ошибка соединения!",
                bottom1: "Скачивайте видео с более чем 1000+ платформ и",
                bottom2: "сохраняйте прямые трансляции на свое устройство мгновенно!",
                modalTitle: "Информация о форматах",
                mp3d: "Идеальный баланс качества и размера.", mp3c: "Поддержка обложки.",
                wavd: "Без потерь, лучшее качество, но большой размер.", wavc: "Нет обложки.",
                opusd: "Современный формат, высокое качество при малом размере.", opusc: "Нет обложки.",
                okBtn: "Понятно"
            },
            pt: {
                flag: "🇵🇹", name: "Português",
                title: "Studio Downloader", sub: "Premium Video & Audio Converter",
                defPath: "Selecione uma pasta...", placeholder: "Cole o link e pressione Enter...",
                video: "Vídeo (MP4)", audio: "Áudio (MP3/WAV)", maxQuality: "Máxima",
                formatInfo: "Recursos de Áudio", playlist: "Baixar como Playlist",
                startBtn: "Iniciar Download",
                startBtnWait: "Iniciando...", downloading: "Baixando...", converting: "Convertendo...",
                finishedAll: "Todos os Downloads Concluídos!", errUnknown: "Desconhecido",
                errPrefix: "Erro:", tSuccess: "Sucesso!", tErrPath: "Selecione uma pasta!",
                tErrLink: "Nenhum link inserido!", tErrQueue: "Fila vazia!",
                tErrExist: "Este link já está na fila!", tErrInfo: "Falha ao obter info!", tErrConn: "Erro de conexão!",
                bottom1: "Baixe vídeos de mais de 1000 plataformas e",
                bottom2: "grave transmissões ao vivo no seu dispositivo instantaneamente!",
                modalTitle: "Info de Formatos",
                mp3d: "Equilíbrio ideal entre qualidade e tamanho.", mp3c: "Suporta capa.",
                wavd: "Sem perda, maior qualidade, mas arquivo grande.", wavc: "Sem capa.",
                opusd: "Formato moderno com alta qualidade e tamanho pequeno.", opusc: "Sem capa.",
                okBtn: "Entendido"
            },
            zh: {
                flag: "🇨🇳", name: "中文",
                title: "Studio Downloader", sub: "Premium Video & Audio Converter",
                defPath: "请选择一个文件夹...", placeholder: "粘贴链接并按回车...",
                video: "视频 (MP4)", audio: "音频 (MP3/WAV)", maxQuality: "最高",
                formatInfo: "音频格式功能", playlist: "作为播放列表下载",
                startBtn: "开始下载",
                startBtnWait: "启动中...", downloading: "下载中...", converting: "转换中...",
                finishedAll: "所有下载已完成！", errUnknown: "未知",
                errPrefix: "错误：", tSuccess: "操作成功！", tErrPath: "请选择文件夹！",
                tErrLink: "未输入链接！", tErrQueue: "队列为空！",
                tErrExist: "此链接已在队列中！", tErrInfo: "获取视频信息失败！", tErrConn: "连接错误！",
                bottom1: "从超过1000个平台下载视频，并",
                bottom2: "将实时直播立即保存到您的设备！",
                modalTitle: "音频格式信息",
                mp3d: "质量和大小的理想平衡。", mp3c: "支持封面。",
                wavd: "无损，最高音质，但文件较大。", wavc: "不支持封面。",
                opusd: "现代格式，文件小但音质高。", opusc: "不支持封面。",
                okBtn: "明白了"
            },
            ja: {
                flag: "🇯🇵", name: "日本語",
                title: "Studio Downloader", sub: "Premium Video & Audio Converter",
                defPath: "フォルダを選択してください...", placeholder: "リンクを貼り付けてEnterを押す...",
                video: "ビデオ (MP4)", audio: "オーディオ (MP3/WAV)", maxQuality: "最高",
                formatInfo: "フォーマットの機能", playlist: "プレイリストとしてダウンロード",
                startBtn: "ダウンロード開始",
                startBtnWait: "開始中...", downloading: "ダウンロード中...", converting: "変換中...",
                finishedAll: "すべてのダウンロードが完了しました！", errUnknown: "不明",
                errPrefix: "エラー:", tSuccess: "成功しました！", tErrPath: "フォルダを選択してください！",
                tErrLink: "リンクが入力されていません！", tErrQueue: "キューが空です！",
                tErrExist: "このリンクはすでにキューにあります！", tErrInfo: "情報の取得に失敗しました！", tErrConn: "接続エラー！",
                bottom1: "1000以上のプラットフォームからビデオをダウンロードし、",
                bottom2: "アクティブなライブストリームをすぐに保存できます！",
                modalTitle: "フォーマット情報",
                mp3d: "品質とサイズの理想的なバランス。", mp3c: "カバーアート対応。",
                wavd: "ロスレス、最高音質ですがファイルは大きいです。", wavc: "カバーアート非対応。",
                opusd: "小さいサイズで高品質を提供するモダンなフォーマット。", opusc: "カバーアート非対応。",
                okBtn: "了解"
            },
            hi: {
                flag: "🇮🇳", name: "हिन्दी",
                title: "Studio Downloader", sub: "Premium Video & Audio Converter",
                defPath: "कृपया एक फ़ोल्डर चुनें...", placeholder: "लिंक पेस्ट करें और Enter दबाएं...",
                video: "वीडियो (MP4)", audio: "ऑडियो (MP3/WAV)", maxQuality: "सर्वश्रेष्ठ",
                formatInfo: "ऑडियो प्रारूप विशेषताएँ", playlist: "प्लेलिस्ट के रूप में डाउनलोड करें",
                startBtn: "डाउनलोड शुरू करें",
                startBtnWait: "शुरू हो रहा है...", downloading: "डाउनलोड हो रहा है...", converting: "परिवर्तित हो रहा है...",
                finishedAll: "सभी डाउनलोड पूरे हुए!", errUnknown: "अज्ञात",
                errPrefix: "त्रुटि:", tSuccess: "सफल!", tErrPath: "कृपया फ़ोल्डर चुनें!",
                tErrLink: "कोई लिंक नहीं डाला गया!", tErrQueue: "कतार खाली है!",
                tErrExist: "यह लिंक पहले से कतार में है!", tErrInfo: "जानकारी प्राप्त करने में विफल!", tErrConn: "कनेक्शन त्रुटि!",
                bottom1: "1000+ से अधिक प्लेटफार्मों से वीडियो डाउनलोड करें और",
                bottom2: "लाइव स्ट्रीम को तुरंत अपने डिवाइस पर सहेजें!",
                modalTitle: "ऑडियो प्रारूप जानकारी",
                mp3d: "गुणवत्ता और आकार का आदर्श संतुलन।", mp3c: "कवर आर्ट का समर्थन करता है।",
                wavd: "हानिरहित, उच्चतम गुणवत्ता लेकिन बड़ी फ़ाइल।", wavc: "कवर आर्ट समर्थित नहीं।",
                opusd: "आधुनिक प्रारूप, कम आकार में उच्च गुणवत्ता।", opusc: "कवर आर्ट समर्थित नहीं।",
                okBtn: "समझ गया"
            }
        };

        let currentLang = localStorage.getItem('ytpro_lang') || 'tr';

        function updateTexts() {
            const t = translations[currentLang];
            document.querySelector("h1").innerText = t.title;
            document.querySelector(".subtitle").innerText = t.sub;

            let pathDisplay = document.getElementById('pathDisplay');
            if (pathDisplay.innerText.includes("Lütfen") || pathDisplay.innerText.includes("Please") || pathDisplay.innerText.includes("Seleccione") || pathDisplay.innerText.includes("Veuillez") || pathDisplay.innerText.includes("Bitte") || pathDisplay.innerText.includes("Пожалуйста") || pathDisplay.innerText.includes("Selecione") || pathDisplay.innerText.includes("请") || pathDisplay.innerText.includes("フォルダ") || pathDisplay.innerText.includes("कृपया")) {
                pathDisplay.innerText = t.defPath;
            }

            document.getElementById('urlInput').placeholder = t.placeholder;

            // Format options
            const formatSelected = document.getElementById('formatValue').value;
            const formatTrigger = document.querySelector("#formatSelectDiv .custom-select__trigger span");
            document.querySelectorAll("#formatSelectDiv .custom-option")[0].innerText = t.video;
            document.querySelectorAll("#formatSelectDiv .custom-option")[1].innerText = t.audio;
            if (formatSelected === 'video') formatTrigger.innerText = t.video;
            else formatTrigger.innerText = t.audio;

            document.querySelector("#formatInfoLinkContainer span").innerHTML = `<i class="fa-solid fa-circle-info" style="margin-right: 4px;"></i>${t.formatInfo}`;
            document.querySelector(".playlist-info").innerHTML = `<i class="fa-solid fa-list-ul"></i>${t.playlist}`;

            updateDownloadButtonText(); // will use t.startBtn

            document.querySelector("#formatInfoModalContent h3").innerHTML = `<i class="fa-solid fa-music" style="color: var(--primary); margin-right: 8px;"></i>${t.modalTitle}`;
            const divs = document.querySelectorAll("#formatInfoModalContent > div > div");
            divs[0].innerHTML = `<strong style="color: var(--primary);">MP3 & M4A:</strong> ${t.mp3d} <span style="color: #32D74B; font-weight: 600;">${t.mp3c}</span>`;
            divs[1].innerHTML = `<strong style="color: var(--primary);">WAV:</strong> ${t.wavd} <span style="color: var(--danger); font-weight: 600;">${t.wavc}</span>`;
            divs[2].innerHTML = `<strong style="color: var(--primary);">Opus:</strong> ${t.opusd} <span style="color: var(--danger); font-weight: 600;">${t.opusc}</span>`;

            document.querySelector("#formatInfoModalContent button:last-child").innerText = t.okBtn;

            document.querySelector(".glass-card > p:last-child").innerHTML = `<i class="fa-solid fa-cloud-arrow-down" style="margin-right: 4px;"></i> ${t.bottom1}<br><i class="fa-solid fa-tower-broadcast" style="margin-right: 4px;"></i> ${t.bottom2}`;

            // Quality texts
            if (videoQualities && audioFormats) {
                videoQualities[0].label = t.maxQuality;
                // others are static like 8K, 4K, 1080p, MP3 etc.
                updateQualityMenu(formatSelected);
            }

            // Flag UI update
            document.getElementById('currentLangFlag').innerText = t.flag;
        }

        function setLanguage(langCode) {
            currentLang = langCode;
            localStorage.setItem('ytpro_lang', langCode);
            updateTexts();
            document.getElementById('langSelectDiv').classList.remove('open');
            // update python via fetch
            fetch('/set-lang', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lang: langCode })
            }).catch(e => {});
        }
"""

lang_html = """
            <div style="display: flex; gap: 8px; align-items: center;">
                <div class="custom-select-wrapper" style="width: 70px; height: 32px; z-index: 50;">
                    <div class="custom-select" id="langSelectDiv">
                        <div class="custom-select__trigger" style="height: 32px; padding: 0 10px; border-radius: 8px;">
                            <span id="currentLangFlag">🇹🇷</span><div class="arrow"></div>
                        </div>
                        <div class="custom-options" style="width: 140px; right: 0; left: auto; max-height: 250px; overflow-y: auto;">
                            <span class="custom-option" onclick="setLanguage('tr')">🇹🇷 Türkçe</span>
                            <span class="custom-option" onclick="setLanguage('en')">🇬🇧 English</span>
                            <span class="custom-option" onclick="setLanguage('es')">🇪🇸 Español</span>
                            <span class="custom-option" onclick="setLanguage('fr')">🇫🇷 Français</span>
                            <span class="custom-option" onclick="setLanguage('de')">🇩🇪 Deutsch</span>
                            <span class="custom-option" onclick="setLanguage('ru')">🇷🇺 Русский</span>
                            <span class="custom-option" onclick="setLanguage('pt')">🇵🇹 Português</span>
                            <span class="custom-option" onclick="setLanguage('zh')">🇨🇳 中文</span>
                            <span class="custom-option" onclick="setLanguage('ja')">🇯🇵 日本語</span>
                            <span class="custom-option" onclick="setLanguage('hi')">🇮🇳 हिन्दी</span>
                        </div>
                    </div>
                </div>
"""

# Replace the HTML for the theme/update buttons container to inject the language dropdown
# Current HTML has:
#             <div style="display: flex; gap: 8px;">
#                 <button id="themeToggleBtn"...

content = content.replace('<div style="display: flex; gap: 8px;">\n                <button id="themeToggleBtn"', lang_html + '\n                <button id="themeToggleBtn"')

# Add i18n_script logic to javascript
content = content.replace('// --- 0. AUTO UPDATER LOGIC ---', i18n_script + '\n        // --- 0. AUTO UPDATER LOGIC ---')

# Replace fixed JS texts with t.variables
content = content.replace('showToast("Link girmediniz!", true);', 'showToast(translations[currentLang].tErrLink, true);')
content = content.replace('showToast("Bu link zaten sırada!", true);', 'showToast(translations[currentLang].tErrExist, true);')
content = content.replace('showToast("Video bilgisi alınamadı!", true);', 'showToast(translations[currentLang].tErrInfo, true);')
content = content.replace('showToast("Bağlantı hatası!", true);', 'showToast(translations[currentLang].tErrConn, true);')
content = content.replace('btn.innerText = `İndirmeyi Başlat (${downloadQueue.length} Video)`;', 'btn.innerText = `${translations[currentLang].startBtn} (${downloadQueue.length} Video)`;')
content = content.replace('btn.innerText = "İndirmeyi Başlat";', 'btn.innerText = translations[currentLang].startBtn;')
content = content.replace('showToast("Konum Seçildi!");', 'showToast(translations[currentLang].tSuccess);')
content = content.replace('pText.innerText = `${baseText}İndiriliyor... %${data.percent}`;', 'pText.innerText = `${baseText}${translations[currentLang].downloading} %${data.percent}`;')
content = content.replace('pText.innerText = `${baseText}Dönüştürülüyor...`;', 'pText.innerText = `${baseText}${translations[currentLang].converting}`;')
content = content.replace('pText.innerText = "Tüm İndirmeler Tamamlandı!";', 'pText.innerText = translations[currentLang].finishedAll;')
content = content.replace('showToast("İşlem Başarılı!");', 'showToast(translations[currentLang].tSuccess);')
content = content.replace('pText.innerText = "Hata: " + (data.error || "Bilinmeyen");', 'pText.innerText = translations[currentLang].errPrefix + " " + (data.error || translations[currentLang].errUnknown);')
content = content.replace('showToast("Sırada indirilecek link yok!", true);', 'showToast(translations[currentLang].tErrQueue, true);')
content = content.replace('showToast("Lütfen klasör seçin!", true);', 'showToast(translations[currentLang].tErrPath, true);')
content = content.replace('btn.innerText = "Başlatılıyor...";', 'btn.innerText = translations[currentLang].startBtnWait;')
content = content.replace('showToast("Hata: " + data.message, true);', 'showToast(translations[currentLang].errPrefix + " " + data.message, true);')
content = content.replace('showToast("Sunucu Hatası!", true);', 'showToast(translations[currentLang].tErrConn, true);')
content = content.replace('document.getElementById("updateTitle").innerText = "Sistem güncelleniyor...";', 'document.getElementById("updateTitle").innerText = translations[currentLang].sysUpdate;')
content = content.replace('startUpdate("Gerekli ilk kurulum yapılıyor...");', 'startUpdate(translations[currentLang].sysReq);')
content = content.replace('startUpdate("Sistem güncelleniyor...");', 'startUpdate(translations[currentLang].sysUpdate);')
content = content.replace('document.getElementById(\'updateDesc\').innerText = "Lütfen bekleyin, bu işlem internet hızınıza bağlı olarak 1-2 dakika sürebilir.";', 'document.getElementById(\'updateDesc\').innerText = translations[currentLang].updateWait;')
content = content.replace('document.getElementById(\'updateTitle\').innerText = "Güncelleme Başarılı!";', 'document.getElementById(\'updateTitle\').innerText = translations[currentLang].updateSuccess;')
content = content.replace('document.getElementById(\'updateDesc\').innerText = "Değişikliklerin tamamen uygulanması için lütfen programı kapatıp yeniden açın.";', 'document.getElementById(\'updateDesc\').innerText = translations[currentLang].updateSuccessDesc;')
content = content.replace('document.getElementById(\'updateTitle\').innerText = "Hata Oluştu!";', 'document.getElementById(\'updateTitle\').innerText = translations[currentLang].updateErr;')
content = content.replace('document.getElementById(\'updateDesc\').innerText = "Bağlantı hatası, lütfen internetinizi kontrol edip tekrar deneyin.";', 'document.getElementById(\'updateDesc\').innerText = translations[currentLang].updateErrDesc;')
content = content.replace('showToast("Güncelleme isteği başarısız oldu", true);', 'showToast(translations[currentLang].toastUpdateFail, true);')

# Also add updateTexts() at DOMContentLoaded
content = content.replace('checkComponentsStatus();', 'checkComponentsStatus();\n            updateTexts();')

with open(r"C:\Users\salih\Desktop\HTML\YoutubePro\templates\index.html", "w", encoding="utf-8") as f:
    f.write(content)
