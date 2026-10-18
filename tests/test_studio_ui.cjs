const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require('node:path').join(__dirname,'../src/templates/index.html'),'utf8');
function section(start,end){return html.slice(html.indexOf(start),html.indexOf(end));}
function element(){return {value:'',innerText:'',className:'',children:[],attributes:{},classList:{add(){},remove(){}},
    setAttribute(k,v){this.attributes[k]=v;},addEventListener(){},appendChild(item){this.children.push(item);},
    replaceChildren(...items){this.children=items;},querySelectorAll(){return this.children;}};}
const nodes=new Map();
const get=id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);};
let light=false;
const preferences=new Map();
const context=vm.createContext({document:{getElementById:get,createElement:element,
    documentElement:{classList:{contains:()=>light,add(){light=true;},remove(){light=false;}}}},
    localStorage:{setItem:(k,v)=>preferences.set(k,v)},setTimeout:()=>1,
    translations:{tr:{startBtn:'İndir'}},currentLang:'tr',downloadQueue:['https://example.com/a'],
    videoQualities:[{value:'max',label:'En yüksek'},{value:'720p',label:'720p'}],audioFormats:[{value:'mp3',label:'MP3'}]});
vm.runInContext(section('        function updateQualityMenu(type)', '        async function selectFolder()')+
    section('        function toggleTheme(forceDark', '        // Auto-detect and set theme')+
    section('        function showToast(', '        // --- 3. İNDİRME')+
    section('        function updateDownloadButtonText()', '        // --- 2. KLASÖR'),context);
get('qualityValue').value='720p';
vm.runInContext("updateQualityMenu('video')",context);
assert.equal(get('qualityValue').value,'720p');
assert.equal(get('qualityText').innerText,'720p');
vm.runInContext("updateQualityMenu('audio')",context);
assert.equal(get('qualityValue').value,'mp3');
vm.runInContext('toggleTheme(false)',context);
assert.equal(light,true);assert.equal(preferences.size,0);
vm.runInContext('toggleTheme()',context);
assert.equal(light,false);assert.equal(preferences.get('ytpro_theme'),'dark');
vm.runInContext("showToast('<img src=x onerror=alert(1)>',true)",context);
assert.equal(get('snackbar').children[1].textContent,'<img src=x onerror=alert(1)>');
assert.equal(get('snackbar').children[1].children.length,0);
vm.runInContext('resetUI()',context);
assert.equal(get('dlBtn').innerText,'İndir (1 Video)');
console.log('7 studio regression checks passed');
