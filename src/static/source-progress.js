function sourcePhaseLabel(phase) { return appMessageLocales.en['phase.'+phase]?appMessage('phase.'+phase):''; }
function queueErrorLabel(code) { return code?appMessage('error.'+code):''; }
function sourceErrorStage(phase) { return sourcePhaseLabel(phase); }
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
        showToast(appMessage('diagnostic_copied'));
    } catch(_) {
        if(report) {
            openSettings();
            document.getElementById('diagnosticsPanel').open=true;
            const text=document.getElementById('diagnosticsText');text.hidden=false;text.value=report;text.focus();text.select();
            showToast(appMessage('copy_manually'));
        } else showToast(appMessage('diagnostic_failed'),true);
    }
}
