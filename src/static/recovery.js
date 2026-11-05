let recoveryLocales = {}, recoveryState = null, recoveryFirstPoll = true;
let recoveryRenderKey = '', shutdownActive = false, shutdownFailed = false;
const recoveryPending = new Set();
function recoveryText(key) {
    const lang = typeof currentLang === 'undefined' ? 'en' : currentLang;
    return (recoveryLocales[lang] || recoveryLocales.en || {})[key] || '';
}
function updateRecoveryTexts() {
    document.getElementById('recoveryTitle').textContent = recoveryText('title');
    document.getElementById('recoveryIntro').textContent = recoveryText('intro');
    document.getElementById('shutdownMessage').textContent = recoveryText(shutdownFailed ? 'saveFailed' : 'saving');
    recoveryRenderKey = '';
    if (recoveryState) renderRecoveryItems();
}
function updateRecoveryCenter(data) {
    recoveryState = data;
    if (recoveryFirstPoll) {
        recoveryFirstPoll = false;
        if (data.restored_count && typeof setWorkspaceView === 'function') setWorkspaceView('queue');
    }
    renderRecoveryItems();
}
function renderRecoveryItems() {
    const items = recoveryState?.recovery_items || [];
    const panel = document.getElementById('recoveryCenter');
    panel.hidden = !items.length;
    const key = JSON.stringify([items, [...recoveryPending], recoveryState?.shutting_down, typeof currentLang === 'undefined' ? 'en' : currentLang]);
    if (key === recoveryRenderKey) return;
    recoveryRenderKey = key;
    const container = document.getElementById('recoveryItems');
    const focus = document.activeElement?.dataset?.recoveryFocus;
    container.replaceChildren();
    items.forEach(item => {
        const card = document.createElement('article'); card.className = 'recovery-item';
        const title = document.createElement('strong'); title.textContent = item.title || 'Video';
        const progress = document.createElement('p'); progress.className = 'feature-muted';
        const percent = Math.max(0, Math.min(100, Number(item.percent) || 0));
        const size = typeof formatBytes === 'function' ? formatBytes(item.downloaded_bytes || 0) : '';
        progress.textContent = `${recoveryText('progress')}: ${percent.toFixed(1)}%${size ? ' · ' + size : ''}`;
        const reason = document.createElement('p');
        reason.textContent = ['publication','parts'].includes(item.reason)?appMessage('recovery.'+item.reason):recoveryText(item.reason === 'refresh' ? 'refreshReason' : item.reason) || recoveryText('paused');
        if (item.error_code && typeof queueErrorLabel === 'function') {
            const detail = queueErrorLabel(item.error_code);
            if (detail) reason.textContent += ' ' + detail;
        }
        const actions = document.createElement('div'); actions.className = 'recovery-actions';
        const addAction = (action, label) => {
            const button = document.createElement('button'); button.type = 'button';
            button.className = 'settings-action'; button.textContent = ['finalize','mkv','folder','max_quality'].includes(action)?appMessage('recovery.'+action):recoveryText(label);
            button.disabled = !item.ready || recoveryPending.has(item.id) || recoveryState.shutting_down;
            button.dataset.recoveryFocus = item.id + ':' + action;
            button.addEventListener('click', () => recoverItem(item, action));
            actions.append(button);
        };
        for(const action of item.actions || (item.is_live?['resume']:['resume','refresh']))addAction(action,action==='resume' && item.is_live?'liveResume':action);
        if(item.parts_count) {
            progress.textContent+=' · '+appMessage('session.parts',{count:item.parts_count});
            for(const action of ['export',...(item.parts_count>1?['join']:[])]) {
                const button=document.createElement('button');button.type='button';button.className='settings-action';button.textContent=appMessage('session.'+action);
                button.disabled=!item.parts_ready || recoveryState.shutting_down;
                button.onclick=()=>startRecordingRecovery(item.id,action);actions.append(button);
            }
            const folder=document.createElement('button');folder.type='button';folder.className='settings-action';folder.textContent=appMessage('session.export_folder');
            folder.disabled=!item.parts_ready || recoveryState.shutting_down;folder.onclick=()=>startRecordingRecovery(item.id,'export',false,true);actions.append(folder);
        }
        if (!item.ready && !item.parts_ready) { const waiting = document.createElement('p'); waiting.textContent = recoveryText('waiting'); actions.append(waiting); }
        card.append(title, progress, reason, actions); container.append(card);
    });
    if (focus) [...container.querySelectorAll('button')].find(b => b.dataset.recoveryFocus === focus)?.focus({preventScroll:true});
}
async function recoverItem(item, action) {
    if (recoveryPending.has(item.id) || !item.ready || shutdownActive) return;
    recoveryPending.add(item.id); renderRecoveryItems();
    try {
        if(action==='folder' && !(await selectFolder()))return;
        await postJSON('/queue/recover', {url:item.url, action});
        startProgressPolling();
        await pollDownloadProgress();
    } catch (error) { showToast(error.message, true); }
    finally { recoveryPending.delete(item.id); renderRecoveryItems(); }
}
window.setShutdownState = function(active, failed = false) {
    shutdownActive = active; shutdownFailed = failed;
    const overlay = document.getElementById('shutdownOverlay');
    overlay.hidden = !active && !failed;
    overlay.classList.toggle('shutdown-error', failed);
    // On a disk error keep a readable notice but allow the user to retry closing.
    document.getElementById('shutdownMessage').textContent = recoveryText(failed ? 'saveFailed' : 'saving');
    if (active) overlay.focus();
};
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/static/recovery-locales.json');
        if (!response.ok) return;
        recoveryLocales = await response.json(); updateRecoveryTexts();
    } catch (error) { console.error('Recovery labels unavailable', error); }
});
