const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const html=fs.readFileSync('src/templates/index.html','utf8');
const source=html.slice(html.indexOf('        let folderSelectionPending'),html.indexOf("        document.querySelectorAll('.custom-select-wrapper')"));
const attrs={},notices=[],path={innerText:'Previous destination',style:{}};
const button={classList:{remove(){}},setAttribute:(k,v)=>attrs[k]=v,removeAttribute:k=>delete attrs[k]};
const ctx=vm.createContext({document:{getElementById:id=>id==='pathBtn'?button:path},
 translations:{tr:{tSuccess:'Folder selected'}},currentLang:'tr',showToast:(text,error)=>notices.push({text,error}),
 appMessage:key=>'localized.'+key,serverMessage:(data,key)=>'localized.'+(data.message_key||key)});
vm.runInContext(source,ctx);
(async()=>{
 ctx.fetch=async()=>({ok:true,json:async()=>({status:'cancel'})});
 assert.equal(await vm.runInContext('selectFolder()',ctx),false);assert.equal(path.innerText,'Previous destination');assert.equal(notices.length,0);
 ctx.fetch=async()=>({ok:false,json:async()=>({status:'error',message_key:'folder_dialog_failed'})});
 assert.equal(await vm.runInContext('selectFolder()',ctx),false);assert.equal(path.innerText,'Previous destination');assert.equal(notices.at(-1).text,'localized.folder_dialog_failed');assert.equal(notices.at(-1).error,true);
 ctx.fetch=async()=>{throw Error('Network failure')};
 assert.equal(await vm.runInContext('selectFolder()',ctx),false);assert.equal(attrs['aria-busy'],undefined);
 let finish,calls=0;
 ctx.fetch=()=>{calls++;return new Promise(resolve=>finish=resolve)};
 const pending=vm.runInContext('selectFolder()',ctx);assert.equal(attrs['aria-busy'],'true');
 assert.equal(await vm.runInContext('selectFolder()',ctx),false);assert.equal(calls,1);
 finish({ok:true,json:async()=>({status:'success',path:'C:/Çalışmalar/動画'})});
 assert.equal(await pending,true);assert.equal(path.innerText,'C:/Çalışmalar/動画');assert.equal(attrs['aria-busy'],undefined);
 assert.equal(notices.at(-1).error,undefined);
 console.log('Folder picker UI: cancel, failure, retry, double click, Unicode path passed');
})().catch(error=>{console.error(error);process.exitCode=1});
