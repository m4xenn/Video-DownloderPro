/* Reports contain only bounded, sanitized diagnostic fields. */
document.addEventListener('DOMContentLoaded',()=>{
    const el=id=>document.getElementById(id);
    const tr=()=>typeof currentLang!=='undefined' && currentLang==='tr';
    function texts() {
        el('diagnosticsTitle').textContent=tr()?'Sorun giderme kayıtları':'Troubleshooting records';
        el('diagnosticsDescription').textContent=tr()?'Son 300 kayıt yeniden başlatma sonrasında korunur. Bağlantılar ve oturum bilgileri rapora eklenmez.':'The last 300 records survive restarts. URLs and session credentials are excluded.';
        el('diagnosticsLoad').textContent=tr()?'Kayıtları göster':'Show records';
        el('diagnosticsCopy').textContent=tr()?'Raporu kopyala':'Copy report';
    }
    el('diagnosticsPanel').addEventListener('toggle',texts);texts();
    el('diagnosticsLoad').addEventListener('click',async()=>{
        el('diagnosticsLoad').disabled=true; el('diagnosticsCopy').disabled=true;
        try {
            const response=await fetch('/diagnostics',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
            const data=await response.json();
            if(!response.ok || data.status!=='success') throw new Error();
            el('diagnosticsText').value=data.text;el('diagnosticsText').hidden=false;
            el('diagnosticsCopy').disabled=false;
            el('diagnosticsStatus').textContent=data.available
                ? (tr()?`${data.count} kayıt. Rapor dili İngilizcedir.`:`${data.count} records.`)
                : (tr()?'Kayıt dosyasına erişilemiyor; rapor eksik olabilir.':'Records unavailable; the report may be incomplete.');
        } catch(_) {el('diagnosticsStatus').textContent=tr()?'Kayıtlar okunamadı.':'Could not read records.';}
        finally {el('diagnosticsLoad').disabled=false;}
    });
    el('diagnosticsCopy').addEventListener('click',async()=>{
        try {
            await navigator.clipboard.writeText(el('diagnosticsText').value);
            el('diagnosticsStatus').textContent=tr()?'Rapor kopyalandı.':'Report copied.';
        } catch(_) {
            el('diagnosticsText').focus();el('diagnosticsText').select();
            el('diagnosticsStatus').textContent=tr()?'Ctrl+C ile seçili raporu kopyalayabilirsin.':'Press Ctrl+C to copy the selected report.';
        }
    });
});
