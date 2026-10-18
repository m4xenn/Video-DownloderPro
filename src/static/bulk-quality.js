/* Bounded metadata inspection and source-derived quality choices. */
let addingLinks = false;
let qualityRequest = 0;
let inspectedQualityURL = null;
let inspectedQualities = [];
let qualityLoadingURL = null;
let inspectionTimer = null;
const pastedMetadata = new Map();
function showLinkPreview(data, message) {
    const panel=document.getElementById("linkPreview");
    if(!panel) return;
    panel.hidden=!data && !message;
    document.getElementById("linkPreviewTitle").textContent=data?.title || message || "";
    const details=[];
    if(data) {
        if(data.duration) details.push(Math.floor(data.duration/60)+":"+String(Math.floor(data.duration%60)).padStart(2,"0"));
        const choices=data.video_qualities || [];
        if(choices.length) details.push(choices[0].label);
        details.push(data.total_bytes ? "Yaklaşık "+formatBytes(data.total_bytes) : "Dosya boyutu kaynak tarafından belirtilmiyor");
    }
    document.getElementById("linkPreviewMeta").textContent=details.join(" · ");
}
function scheduleLinkInspection() {
    resizeLinkInput(); clearTimeout(inspectionTimer);
    if(typeof cancelSiteInspection === "function") cancelSiteInspection();
    ++qualityRequest; qualityLoadingURL=null;
    inspectedQualityURL=null; inspectedQualities=[];
    updateQualityMenu(document.getElementById("formatValue").value);
    showLinkPreview(null);
    inspectionTimer=setTimeout(()=>refreshSourceQuality(),550);
}
function splitLinks(text) {
    const urls=[], invalid=[], seen=new Set(); let duplicates=0;
    for (const token of text.trim().split(/\s+/).filter(Boolean)) {
        try {
            const parsed=new URL(token);
            if(!['https:','http:'].includes(parsed.protocol) || !parsed.hostname) throw new Error();
            parsed.hash=''; const url=parsed.href;
            if(seen.has(url)) { duplicates++; continue; }
            seen.add(url); urls.push(url);
        } catch(_) { invalid.push(token); }
    }
    return {urls,invalid,duplicates};
}
function resizeLinkInput() {
    const input=document.getElementById('urlInput');
    input.style.height='48px'; input.style.height=Math.min(136,Math.max(48,input.scrollHeight))+'px';
}
async function addLinksToQueue() {
    if(addingLinks) return;
    const input=document.getElementById('urlInput'), button=document.getElementById('addBtn');
    const report=document.getElementById('bulkStatus');
    const parsed=splitLinks(input.value);
    if(!input.value.trim()) { showToast(translations[currentLang].tErrLink,true); return; }
    if(parsed.urls.length+parsed.invalid.length>500 || downloadQueue.length+parsed.urls.length>500) {
        report.textContent='Bir seferde ve bekleyen bağlantı kuyruğunda en fazla 500 bağlantı desteklenir.'; return;
    }
    let skipped=parsed.duplicates, added=0, checked=0, cursor=0;
    const failures=parsed.invalid.slice();
    const candidates=parsed.urls.filter(url=>{
        if(downloadQueue.includes(url)||activeQueueURLs.has(url)) { skipped++; return false; }
        return true;
    });
    addingLinks=true; input.disabled=true; button.disabled=true; button.classList.add('loading');
    button.innerHTML='<i class="fa-solid fa-circle-notch" aria-hidden="true"></i>';
    try {
        report.textContent=`Bağlantılar inceleniyor: 0 / ${candidates.length}`;
        async function inspect() {
            while(cursor<candidates.length) {
                const url=candidates[cursor++];
                try {
                    const cached=pastedMetadata.get(url);
                    const response=cached && Date.now()-cached.at<600000 ? null : await fetch('/get-info',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
                    const data=response ? await response.json() : cached.data;
                    if(data.status==='interaction_required' && typeof showSiteInspection==='function') showSiteInspection(data,url);
                    if((response && !response.ok) || data.status!=='success') throw new Error(data.message);
                    if(downloadQueue.includes(data.url)||activeQueueURLs.has(data.url)) skipped++;
                    else {
                        downloadQueue.push(data.url); draftItems.set(data.url,data);
                        renderQueueItem(data.url,data.title,data.thumbnail,data); added++;
                    }
                } catch(_) { failures.push(url); }
                checked++; report.textContent=`Bağlantılar inceleniyor: ${checked} / ${candidates.length}`;
            }
        }
        await Promise.all(Array.from({length:Math.min(3,candidates.length)},()=>inspect()));
        await saveDraftQueue();
        input.value=failures.join('\n');
        report.textContent=`${added} eklendi${skipped ? ' · '+skipped+' tekrar atlandı' : ''}${failures.length ? ' · '+failures.length+' bağlantı eklenemedi; girişte bırakıldı.' : ''}`;
        await refreshSourceQuality();
    } finally {
        addingLinks=false; input.disabled=false; button.disabled=false; button.classList.remove('loading');
        button.innerHTML='<i class="fa-solid fa-plus" aria-hidden="true"></i>'; resizeLinkInput(); input.focus();
    }
}
function singleQualityURL() {
    if(document.getElementById('playlistCheck').checked) return null;
    const parsed=splitLinks(document.getElementById('urlInput').value);
    if(parsed.invalid.length || parsed.urls.length>1) return null;
    const urls=[...new Set([...downloadQueue,...parsed.urls])];
    if(urls.length!==1) return null;
    const url=urls[0];
    return draftItems.get(url)?.is_playlist ? null : url;
}
function getVideoQualityOptions() {
    const label=currentLang==='tr' ? 'Otomatik · En yüksek kalite' : 'Auto · Highest quality';
    return [{value:'max',label},...(singleQualityURL()===inspectedQualityURL ? inspectedQualities.map(choice=>({...choice,label:choice.label+(choice.total_bytes ? ' · ≈ '+formatBytes(choice.total_bytes) : '')})) : [])];
}
function updateQualityHint(message) {
    const hint=document.getElementById('qualityHint');
    if(!hint) return;
    const single=singleQualityURL();
    document.getElementById('refreshQuality').style.display=single && document.getElementById('formatValue').value==='video' ? 'inline-flex' : 'none';
    hint.textContent=message || (document.getElementById('formatValue').value==='audio'
        ? 'Ses, seçtiğin çıktı formatına dönüştürülür.'
        : !single ? 'Her video kendi kaynağındaki en yüksek kalitede indirilir.'
        : inspectedQualities.length ? 'Bu videonun sunduğu çözünürlük ve FPS seçenekleri.'
        : 'Kaynak ayrıntılı kalite listesi vermiyor. En iyi kalite otomatik seçilir.');
}
async function refreshSourceQuality(force=false) {
    const url=singleQualityURL();
    if(!force && url && qualityLoadingURL===url) return;
    const request=++qualityRequest;
    qualityLoadingURL=null;
    inspectedQualityURL=url; inspectedQualities=[];
    if(!url) { showLinkPreview(null); document.getElementById('refreshQuality').disabled=false; updateQualityMenu(document.getElementById('formatValue').value); updateQualityHint(); return; }
    const entry=pastedMetadata.get(url);
    const cached=draftItems.get(url) || (entry && Date.now()-entry.at<600000 ? entry.data : null);
    if(!force && Array.isArray(cached?.video_qualities)) {
        showLinkPreview(cached); inspectedQualities=cached.video_qualities; updateQualityMenu(document.getElementById('formatValue').value); updateQualityHint(); return;
    }
    showLinkPreview(null,'Video bilgileri okunuyor…');
    updateQualityHint('Kaynağın kalite seçenekleri inceleniyor...');
    qualityLoadingURL=url;
    document.getElementById('refreshQuality').disabled=true;
    try {
        const response=await fetch('/get-info',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
        const data=await response.json();
        if(request!==qualityRequest || url!==singleQualityURL()) {
            if(data.inspection_id && typeof dismissSiteInspection==='function') dismissSiteInspection(data.inspection_id);
            return;
        }
        if(data.status==='interaction_required' && typeof showSiteInspection==='function') showSiteInspection(data,url);
        if(!response.ok || data.status!=='success') throw new Error(data.message || 'Kalite bilgisi alınamadı. Yenile düğmesiyle tekrar deneyebilirsin.');
        if(typeof clearSiteInspection==='function') clearSiteInspection();
        pastedMetadata.set(url,{data,at:Date.now()});
        if(pastedMetadata.size>20) pastedMetadata.delete(pastedMetadata.keys().next().value);
        if(downloadQueue.includes(url)) draftItems.set(url,{...cached,...data});
        showLinkPreview(data); inspectedQualities=data.video_qualities || [];
        if(data.is_playlist) inspectedQualityURL=null;
        updateQualityMenu(document.getElementById('formatValue').value); updateQualityHint();
    } catch(error) {
        if(request===qualityRequest) { showLinkPreview(null,error.message); inspectedQualities=[]; updateQualityMenu(document.getElementById('formatValue').value); updateQualityHint(error.message); }
    } finally { if(request===qualityRequest) { qualityLoadingURL=null; document.getElementById('refreshQuality').disabled=false; } }
}
document.addEventListener('DOMContentLoaded',()=>{
    document.getElementById('urlInput').addEventListener('input',scheduleLinkInspection);
    document.getElementById('playlistCheck').addEventListener('change',()=>refreshSourceQuality());
    document.getElementById('formatSelectDiv').addEventListener('click',()=>updateQualityHint());
    new MutationObserver(()=>{ if(!addingLinks) refreshSourceQuality(); }).observe(document.getElementById('queueContainer'),{childList:true});
    updateQualityHint();
});
