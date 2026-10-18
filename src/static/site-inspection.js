/* Interaction is requested only when background inspection needs the user. */
let siteInspection = null;
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
    siteInspection=null;
    document.getElementById('siteInspection').hidden=true;
}
function cancelSiteInspection() {
    if(siteInspection) dismissSiteInspection(siteInspection.token);
    clearSiteInspection();
}
function showSiteInspection(data,url) {
    siteInspection={token:data.inspection_id,url};
    document.getElementById('siteInspectionMessage').textContent=data.message;
    document.getElementById('siteInspection').hidden=false;
}
document.addEventListener('DOMContentLoaded',()=>{
    updateSiteInspectionTexts();
    document.getElementById('siteInspectionShow').addEventListener('click',async()=>{
        if(!siteInspection)return;
        try {
            const response=await fetch('/site-inspection/show',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({inspection_id:siteInspection.token})});
            const data=await response.json();
            if(!response.ok || data.status!=='success') throw new Error(data.message);
        } catch(error) {document.getElementById('siteInspectionMessage').textContent=error.message || 'Tarayıcı açılamadı.';}
    });
    document.getElementById('siteInspectionRetry').addEventListener('click',()=>refreshSourceQuality(true));
    document.getElementById('siteInspectionCancel').addEventListener('click',cancelSiteInspection);
});
