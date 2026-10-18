/* Interaction is requested only when background inspection needs the user. */
let siteInspection = null;
let siteInspectionWatch = null;
function stopSiteInspectionWatch() {
    if(siteInspectionWatch) clearTimeout(siteInspectionWatch.timer);
    siteInspectionWatch=null;
}
function watchSiteInspection(token,url) {
    stopSiteInspectionWatch();
    const watch={token,url,expires:Date.now()+120000,timer:null};
    siteInspectionWatch=watch;
    const check=async()=>{
        if(siteInspectionWatch!==watch || siteInspection?.token!==token) return;
        if(Date.now()>=watch.expires || (typeof singleQualityURL==='function' && singleQualityURL()!==url)) {
            stopSiteInspectionWatch(); return;
        }
        if(typeof qualityLoadingURL==='undefined' || !qualityLoadingURL) await refreshSourceQuality(true);
        if(siteInspectionWatch===watch) watch.timer=setTimeout(check,4000);
    };
    watch.timer=setTimeout(check,4000);
}
function updateSiteInspectionTexts() {
    const tr = typeof currentLang !== 'undefined' && currentLang === 'tr';
    document.getElementById('siteInspectionShow').textContent=tr ? 'Tarayıcıda devam et' : 'Continue in browser';
    document.getElementById('siteInspectionRetry').textContent=tr ? 'Tekrar kontrol et' : 'Check again';
    document.getElementById('siteInspectionCancel').textContent=tr ? 'İptal' : 'Cancel';
}
function dismissSiteInspection(token) {
    return fetch('/site-inspection/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({inspection_id:token})}).catch(()=>{});
}
function clearSiteInspection() {
    stopSiteInspectionWatch();
    siteInspection=null;
    document.getElementById('siteInspection').hidden=true;
}
function cancelSiteInspection() {
    if(siteInspection) dismissSiteInspection(siteInspection.token);
    clearSiteInspection();
}
function showSiteInspection(data,url) {
    if(siteInspection && siteInspection.token!==data.inspection_id) stopSiteInspectionWatch();
    siteInspection={token:data.inspection_id,url};
    document.getElementById('siteInspectionMessage').textContent=data.message;
    document.getElementById('siteInspection').hidden=false;
}
document.addEventListener('DOMContentLoaded',()=>{
    updateSiteInspectionTexts();
    document.getElementById('siteInspectionShow').addEventListener('click',async()=>{
        if(!siteInspection)return;
        const inspection=siteInspection;
        try {
            const response=await fetch('/site-inspection/show',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({inspection_id:siteInspection.token})});
            const data=await response.json();
            if(!response.ok || data.status!=='success') throw new Error(data.message);
            if(siteInspection===inspection) watchSiteInspection(inspection.token,inspection.url);
        } catch(error) {document.getElementById('siteInspectionMessage').textContent=error.message || 'Tarayıcı açılamadı.';}
    });
    document.getElementById('siteInspectionRetry').addEventListener('click',()=>refreshSourceQuality(true));
    document.getElementById('siteInspectionCancel').addEventListener('click',cancelSiteInspection);
});
