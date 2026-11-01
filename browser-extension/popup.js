let language=VDPI18n.normalize(chrome.i18n?.getUILanguage?.())||'en', rendering=false;
let elements=new Map();
const t=(key,values)=>VDPI18n.text(key,language,values);
function updateHeader(){document.documentElement.lang=language;document.getElementById('intro').textContent=t('intro');}
async function render(){
 if(rendering)return;rendering=true;
 const root=document.getElementById('jobs');
 try{
  const status=await chrome.runtime.sendMessage({type:'popup-status'});
  language=VDPI18n.normalize(status?.language)||language;updateHeader();
  const jobs=Array.isArray(status?.jobs)?status.jobs:[];
  const preserve=!!document.querySelector('button:hover')||document.activeElement?.tagName==='BUTTON';
  const next=new Map(),ordered=[];
  function node(key,tag,text,className=''){
   let el=elements.get(key);
   if(!el){el=document.createElement(tag);el.className=className;}
   el.textContent=text;next.set(key,el);return el;
  }
  if(!status?.connected)ordered.push(node('connection','p',t('disconnected')));
  if(!jobs.length&&status?.connected)ordered.push(node('empty','p',t('empty')));
  for(const j of jobs){
   ordered.push(node(j.id+':state','p',j.state));
   const open=node(j.id+':open','button',t('open'));open.onclick=()=>chrome.runtime.sendMessage({type:'focus',id:j.id});ordered.push(open);
   const candidates=[...j.candidates].sort((a,b)=>Number(!!b.recommended)-Number(!!a.recommended)||a.index-b.index);
   if(candidates.length)ordered.push(node(j.id+':hint','p',t('hint'),'hint'));
   for(const c of candidates){
    const key=j.id+':source:'+c.index;
    let b=elements.get(key);if(!b)b=document.createElement('button');
    b.className='source'+(c.recommended?' recommended':'');
    const title=node(key+':title','strong',c.label||t('source',{kind:'HLS',index:c.index+1}));
    const detail=node(key+':detail','span',c.detail||t('qualityUnknown'));
    const host=node(key+':host','small',c.host);
    if(!elements.has(key))b.append(title,detail,host);
    b.disabled=!!c.disabled;
    b.onclick=async()=>{b.disabled=true;try{await chrome.runtime.sendMessage({type:'select',id:j.id,index:c.index});await render();}catch{b.disabled=!!c.disabled;}};
    next.set(key,b);ordered.push(b);
   }
  }
  // Reuse nodes. During hover/keyboard focus, update text in place and defer
  // structural changes, so a language switch cannot move a source under a click.
  if(!preserve){root.replaceChildren(...ordered);elements=next;}
 }catch{updateHeader();root.textContent=t('connectError');elements=new Map();}
 finally{rendering=false;}
}
updateHeader();render();
setInterval(render,2000);
