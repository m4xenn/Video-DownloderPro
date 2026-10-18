const assert=require('node:assert/strict'), vm=require('node:vm'), cp=require('node:child_process');
const script=cp.execFileSync('python',['-c',"import sys;sys.path.insert(0,'src');from services.player_activation import START_PLAYER;print(START_PLAYER)"],{encoding:'utf8'});
function run(kind,{captcha=false,drm=false,target='https://player.example/embed',ambiguous=false}={}) {
    const calls=[];
    const container={id:'main',mediaKeys:drm?{}:null,contains:()=>false,
        getBoundingClientRect:()=>({width:640,height:360}),matches:selector=>selector===(kind==='html5'?'video':kind==='jw'?'.jwplayer':'.video-js'),
        play:()=>{calls.push(['html5',container.muted]);return Promise.resolve();}};
    const containers=ambiguous?[container,{...container,id:'other'}]:[container];
    const doc={title:'Video',querySelectorAll:selector=>selector==='video,.jwplayer,.video-js'?containers:captcha?[container]:[]};
    const player={getPlaylist:()=>[{drm}],setMute:value=>calls.push(['mute',value]),
        play:()=>calls.push(['jw']),currentSource:()=>({keySystems:drm?{}:null}),muted:value=>calls.push(['mute',value])};
    const win={document:doc,location:{href:'https://player.example/embed'},getComputedStyle:()=>({display:'block',visibility:'visible'}),
        jwplayer:()=>player,videojs:{getPlayer:()=>({...player,play:()=>{calls.push(['videojs']);return Promise.resolve();}})}};
    vm.runInNewContext(script+'('+JSON.stringify(target)+')',{window:win,Promise,Set});
    return calls;
}
assert.deepEqual(run('html5'),[['html5',true]]);
assert.deepEqual(run('jw'),[['mute',true],['jw']]);
assert.deepEqual(run('videojs'),[['mute',true],['videojs']]);
for(const kind of ['html5','jw','videojs']) {
    assert.deepEqual(run(kind,{captcha:true}),[]);
    assert.deepEqual(run(kind,{drm:true}),[]);
    assert.deepEqual(run(kind,{target:'https://other.example/'}),[]);
    assert.deepEqual(run(kind,{ambiguous:true}),[]);
}
console.log('15 player activation checks passed (muted APIs, verification, DRM, target, ambiguity)');
