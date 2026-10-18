const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('src/templates/index.html','utf8');
const fn=html.slice(html.indexOf('function initialLanguage()'),html.indexOf('let currentLang = initialLanguage()'));
function choose(saved,previous,system,blocked=false){const context={languageBootstrap:{saved,system},translations:Object.fromEntries(['tr','en','fr','de','pt','zh'].map(x=>[x,{}])),localStorage:{getItem(){if(blocked)throw Error();return previous;}}};vm.createContext(context);vm.runInContext(fn,context);return vm.runInContext('initialLanguage()',context);}
assert.equal(choose(null,null,'de'),'de');assert.equal(choose('fr','tr','de'),'fr');assert.equal(choose(null,'tr','de'),'tr');assert.equal(choose(null,'bogus','de'),'de');assert.equal(choose(null,null,'xx'),'en');assert.equal(choose(null,null,'pt',true),'pt');console.log('6 automatic language priority checks passed');
