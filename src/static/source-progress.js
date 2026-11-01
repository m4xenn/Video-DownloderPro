function sourcePhaseLabel(phase) {
    const tr=typeof currentLang!=='undefined' && currentLang==='tr';
    const labels={searching_regions:['Uygun YouTube ülke tercihi aranıyor…','Searching YouTube country preferences…'],browser_extension:['Tarayıcıdaki videoyu oynatın; gerekirse eklentiden kaynağı seçin.','Play the video in your browser; choose a source in the extension if needed.'],finding_player:['Oynatıcı aranıyor…','Finding player…'],starting_player:['Oynatıcı başlatılıyor…','Starting player…'],
        validating_source:['Kaynak doğrulanıyor…','Validating source…'],waiting_server:['Sunucu bekleniyor…','Waiting for server…'],
        refreshing_source:['Kaynak yenileniyor…','Refreshing source…'],postprocess:['Video işleniyor…','Processing video…']};
    return labels[phase]?.[tr?0:1] || '';
}
function queueErrorLabel(code) {
    const tr=typeof currentLang!=='undefined' && currentLang==='tr';
    const labels={rate_limited:['Sunucu istekleri sınırladı (429).','Server rate limit (429).'],
        access_denied:['Sunucu erişimi reddetti (403/401).','Server denied access (403/401).'],
        local_file_missing:['Geçici dosya bulunamadı.','Temporary file missing.'],
        network_error:['Bağlantı hatası veya zaman aşımı.','Connection failed or timed out.'],
        fragment_failed:['Bir video parçası alınamadı.','A video fragment could not be downloaded.'],
        invalid_media:['Kaynak veya indirilen dosya doğrulanamadı.','The source or downloaded file could not be validated.']};
    labels.region_restricted=['Platform bu videoya bulunduğunuz ülke/bölgede erişimi kısıtlıyor. Bağlantıyı tarayıcıda kontrol edin.','The platform restricts this video in your country/region. Check the original page.'];
    labels.video_unavailable=['Platform videonun kullanılamadığını bildiriyor. Bağlantıyı tarayıcıda kontrol edin.','The platform reports that the video is unavailable. Check the original page.'];
    labels.recording_gap=['Canlı parçalar eksik; kayıt durduruldu. Varsa geçici kayıt korundu.','Live segments are missing; recording stopped and any temporary data was preserved.'];
    labels.partial_source=["Kaynak yalnız eksik/önizleme verisi sunuyor; tam indirme durduruldu.","Only a partial recording or preview is accessible; full download stopped."];
    labels.source_mismatch=['Yenilenen kaynak aynı video/format olarak doğrulanamadı.','Refreshed source did not match the video/format.'];
    labels.partial_preserved=['Kısmi dosya korundu; yeni indirme gerekiyor.','Partial file preserved; a new download is required.'];
    labels.encrypted_unsupported=['Yayın şifreli; desteklenmeyen yöntem DRM olarak doğrulanmadı.','Stream encryption is unsupported; DRM was not established.'];
    labels.file_access_denied=['Dosya kullanımda veya yazma izni yok. Oynatıcıyı kapatıp klasör izinlerini kontrol et; indirilen dosyaları silme.','File in use or write permission denied. Close the player and check folder permissions; keep downloaded files.'];
    labels.disk_full=['Kayıt diskinde boş alan yok.','The destination disk is full.'];
    labels.drm=['Kaynak DRM korumalı.','Source is DRM-protected.'];
    labels.interaction_required=['Oynatıcı kullanıcı etkileşimi gerektiriyor.','Player requires user interaction.'];
    labels.not_found=['Kaynak bulunamadı (404).','Source not found (404).'];
    labels.unsupported=['Uygun medya kaynağı bulunamadı.','No supported media source found.'];
    if(code==='partial_source' && typeof downloadToolText==='function')return downloadToolText(2);
    return code ? (labels[code]?.[tr?0:1] || (tr?'İşlem tamamlanamadı. Ayrıntıları kopyalayabilirsin.':'Operation failed. You can copy details.')) : '';
}
function sourceErrorStage(phase) {
    const tr=typeof currentLang!=='undefined' && currentLang==='tr';
    const labels={searching_regions:['Uygun YouTube ülke tercihi aranıyor…','Searching YouTube country preferences…'],browser_extension:['Tarayıcıdaki videoyu oynatın; gerekirse eklentiden kaynağı seçin.','Play the video in your browser; choose a source in the extension if needed.'],finding_player:['Oynatıcı arama','Player discovery'],starting_player:['Oynatıcı başlatma','Player activation'],
        validating_source:['Kaynak doğrulama','Source validation'],refreshing_source:['Kaynak yenileme','Source refresh'],
        waiting_server:['Sunucu bekleme','Server wait'],downloading:['İndirme','Download'],postprocess:['Video işleme','Postprocessing']};
    return labels[phase]?.[tr?0:1] || '';
}
function watchSourceProgress(url) {
    const watch={active:true,timer:null};
    const tick=async()=>{
        if(!watch.active)return;
        try {
            const response=await fetch('/source-progress',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
            const data=await response.json();
            if(watch.active && typeof singleQualityURL==='function' && singleQualityURL()===url) {
                const label=sourcePhaseLabel(data.phase);
                if(label)updateQualityHint(label);
                const open=document.getElementById('companionContinue');if(open)open.hidden=data.phase!=='browser_extension';
            }
        } catch(_) {}
        if(watch.active)watch.timer=setTimeout(tick,800);
    };
    watch.timer=setTimeout(tick,800);
    return ()=>{watch.active=false;clearTimeout(watch.timer);const open=document.getElementById('companionContinue');if(open)open.hidden=true;};
}
async function copyDiagnosticReport(url) {
    const tr=typeof currentLang!=='undefined' && currentLang==='tr';
    let report='';
    try {
        const response=await fetch('/diagnostics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
        const data=await response.json();
        if(!response.ok || data.status!=='success')throw new Error();
        report=data.text;await navigator.clipboard.writeText(report);
        showToast(tr?'Hata ayrıntıları kopyalandı.':'Error details copied.');
    } catch(_) {
        if(report) {
            openSettings();
            document.getElementById('diagnosticsPanel').open=true;
            const text=document.getElementById('diagnosticsText');text.hidden=false;text.value=report;text.focus();text.select();
            showToast(tr?'Seçili raporu Ctrl+C ile kopyalayabilirsin.':'Press Ctrl+C to copy the selected report.');
        } else showToast(tr?'Hata ayrıntıları okunamadı.':'Could not read error details.',true);
    }
}
