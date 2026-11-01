let companionState=null,companionCopy={},companionBusy=false,companionNotice='';
function companionText(key){const lang=typeof currentLang==='string'?currentLang:'en';return (companionCopy[lang]||companionCopy.en||{})[key]||'';}
function updateCompanionTexts(){
 document.querySelectorAll('[data-companion]').forEach(e=>e.textContent=companionText(e.dataset.companion));
 document.querySelectorAll('[data-companion-step]').forEach(e=>e.textContent=(companionText('steps')||[])[Number(e.dataset.companionStep)]||'');
 renderCompanionState();
}
function renderCompanionState(){
 const s=companionState,browser=document.getElementById('companionBrowser'),consent=document.getElementById('companionConsent');
 if(!browser||!consent)return;
 const entry=s?.browsers.find(b=>b.id===browser.value);
 document.getElementById('companionPrepare').disabled=companionBusy||!consent.checked||!entry?.installed||!s?.package_ready;
 document.getElementById('companionOpen').disabled=companionBusy||!entry?.installed||!s?.prepared;
 for(const id of ['companionCopy','companionFolder'])document.getElementById(id).disabled=companionBusy||!s?.prepared;
 browser.disabled=companionBusy;consent.disabled=companionBusy;document.getElementById('companionCheck').disabled=companionBusy;
 document.getElementById('companionFolderPath').value=s?.prepared?s.folder:'';
 const status=s?.connected?'connected':s?.needs_update?'update':!s?.package_ready?'missing':entry?.registered?'registered':'waiting';
 document.getElementById('companionBadge').textContent=s?.connected?companionText('connected'):companionText('waiting');
 document.getElementById('companionSetupStatus').textContent=companionText(companionNotice||status);
}
async function refreshCompanion(){
 try{
  const r=await fetch('/browser-companion/status',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}),s=await r.json();
  if(!r.ok||s.status!=='success')throw Error(s.code||'setup_failed');
  companionState=s;
  const select=document.getElementById('companionBrowser');
  for(const option of select.options)option.disabled=!s.browsers.find(b=>b.id===option.value)?.installed;
  if(select.selectedOptions[0]?.disabled){const available=[...select.options].find(o=>!o.disabled);if(available)select.value=available.value;}
  renderCompanionState();
 }catch{companionNotice='failed';renderCompanionState();}
}
async function companionAction(action){
 if(companionBusy)return;
 companionBusy=true;companionNotice='';renderCompanionState();
 try{
  const r=await fetch('/browser-companion/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,browser:document.getElementById('companionBrowser').value,consent:document.getElementById('companionConsent').checked})});
  const s=await r.json();if(!r.ok||s.status!=='success')throw Error(s.code||'setup_failed');companionState=s;
 }catch(e){companionNotice=({consent_required:'consentError',browser_missing:'browserError',package_incomplete:'missing'})[e.message]||'failed';}
 finally{companionBusy=false;renderCompanionState();}
}
document.addEventListener('DOMContentLoaded',async()=>{
 try{const r=await fetch('/static/companion-locales.json');companionCopy=await r.json();}catch{}
 updateCompanionTexts();
 if(typeof updateHelpTexts==='function')updateHelpTexts();
 document.getElementById('companionConsent').addEventListener('change',renderCompanionState);
 document.getElementById('companionBrowser').addEventListener('change',()=>{companionNotice='';renderCompanionState();});
 for(const [id,action] of [['companionPrepare','prepare'],['companionOpen','browser'],['companionFolder','folder']])document.getElementById(id).addEventListener('click',()=>companionAction(action));
 document.getElementById('companionCheck').addEventListener('click',async()=>{companionNotice='';await refreshCompanion();});
 document.getElementById('companionCopy').addEventListener('click',async()=>{
  const field=document.getElementById('companionFolderPath');
  try{await navigator.clipboard.writeText(field.value);companionNotice='copied';}catch{field.focus();field.select();document.execCommand('copy');companionNotice='copied';}renderCompanionState();
 });
 document.getElementById('companionPanel').addEventListener('toggle',()=>{if(document.getElementById('companionPanel').open)refreshCompanion();});
 await refreshCompanion();
 setInterval(()=>{if(document.getElementById('companionPanel').open&&!document.hidden&&!companionBusy)refreshCompanion();},5000);
});
