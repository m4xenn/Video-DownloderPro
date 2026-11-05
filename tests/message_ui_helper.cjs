const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
module.exports=context=>{
 context.appMessageLocales=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/static/message-locales.json'),'utf8'));
 context.appMessageAliases={};
 for(const copy of Object.values(context.appMessageLocales))for(const [key,text] of Object.entries(copy))if(!text.includes('{'))context.appMessageAliases[text]=key;
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/static/messages.js'),'utf8'),context);
};
