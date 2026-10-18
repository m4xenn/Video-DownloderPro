function sourcePhaseLabel(phase) {
    const tr=typeof currentLang!=='undefined' && currentLang==='tr';
    const labels={finding_player:['Oynatıcı aranıyor…','Finding player…'],starting_player:['Oynatıcı başlatılıyor…','Starting player…'],
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
        invalid_media:['Medya kaynağı doğrulanamadı.','Media source could not be validated.']};
    labels.source_mismatch=['Yenilenen kaynak aynı video/format olarak doğrulanamadı.','Refreshed source did not match the video/format.'];
    labels.partial_preserved=['Kısmi dosya korundu; yeni indirme gerekiyor.','Partial file preserved; a new download is required.'];
    labels.drm=['Kaynak DRM korumalı.','Source is DRM-protected.'];
    labels.interaction_required=['Oynatıcı kullanıcı etkileşimi gerektiriyor.','Player requires user interaction.'];
    labels.not_found=['Kaynak bulunamadı (404).','Source not found (404).'];
    labels.unsupported=['Uygun medya kaynağı bulunamadı.','No supported media source found.'];
    return code ? (labels[code]?.[tr?0:1] || (tr?'İşlem tamamlanamadı. Ayrıntıları kopyalayabilirsin.':'Operation failed. You can copy details.')) : '';
}
function sourceErrorStage(phase) {
    const tr=typeof currentLang!=='undefined' && currentLang==='tr';
    const labels={finding_player:['Oynatıcı arama','Player discovery'],starting_player:['Oynatıcı başlatma','Player activation'],
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
            }
        } catch(_) {}
        if(watch.active)watch.timer=setTimeout(tick,800);
    };
    watch.timer=setTimeout(tick,800);
    return ()=>{watch.active=false;clearTimeout(watch.timer);};
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
