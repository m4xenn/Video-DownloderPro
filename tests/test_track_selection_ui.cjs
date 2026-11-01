const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map();
function get(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,disabled:false,hidden:false,replaceChildren(...options){this.options=options;this.value=options[0]?.value || '';}});return nodes.get(id);}
const context=vm.createContext({Intl,currentLang:'tr',singleQualityURL:()=>context.single,
 document:{getElementById:get,addEventListener(){}},Option:function(label,value){this.text=label;this.value=value;}});
context.single='https://example.com/video';get('formatValue').value='video';
vm.runInContext(fs.readFileSync('src/static/track-selection.js','utf8'),context);
const run=code=>vm.runInContext(code,context);
run("setTrackChoices({url:'https://example.com/video',audio_languages:['en','tr'],subtitle_languages:['en','tr']})");
assert.equal(get('trackChoices').hidden,false);assert.equal(get('subtitleLanguage').disabled,true);
get('subCheck').checked=true;run('updateTrackTexts()');get('audioLanguage').value='tr';get('subtitleLanguage').value='en';
assert.equal(run('selectedTracks().audio_language'),'tr');assert.equal(run('selectedTracks().subtitle_language'),'en');
for(const language of ['tr','en','de','es','fr','pt','ru','zh','ja','hi']){
 context.currentLang=language;run('updateTrackTexts()');assert.equal(get('audioLanguage').value,'tr');assert.ok(get('audioLanguageLabel').textContent);assert.ok(run('previewScopeText()'));
}
context.single=null;assert.equal(run('selectedTracks().audio_language'),'auto');assert.equal(get('trackChoices').hidden,true);
context.single='https://example.com/next';run("setTrackChoices({url:'https://example.com/next',audio_languages:['en']})");assert.equal(get('audioLanguage').value,'auto');
console.log('Track UI: explicit choices, subtitle gating, 10 locales, bulk reset and changed URL passed');
