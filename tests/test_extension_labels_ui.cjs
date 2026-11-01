const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context=vm.createContext({URL});vm.runInContext(fs.readFileSync('browser-extension/locales.js','utf8'),context);vm.runInContext(fs.readFileSync('browser-extension/source-labels.js','utf8'),context);
const {parse,apply,describe}=context.VDPSourceLabels,base='https://cdn.example/master.m3u8?token=secret';
const text='#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",LANGUAGE="tr",NAME="Turkish",URI="audio.m3u8"\n#EXT-X-STREAM-INF:BANDWIDTH=2400000,RESOLUTION=1428x804,CODECS="avc1.640028,mp4a.40.2"\nvideo.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=1200000,RESOLUTION=952x536\nlow.m3u8\n';
const m=parse(text,base);assert.equal(m.role,'master');assert.equal(m.variantCount,2);assert.equal(m.tracks.length,3);assert.equal(m.tracks[1].height,804);
const candidates=[{url:base},{url:'https://cdn.example/video.m3u8'},{url:'https://cdn.example/audio.m3u8'},{url:'https://cdn.example/unknown.m3u8'}];apply(candidates,base,m);
assert.equal(describe(candidates[0],0).recommended,true);assert.match(describe(candidates[0],0).detail,/2 quality/);assert.match(describe(candidates[1],1).label,/804p/);assert.equal(describe(candidates[2],2).detail,'tr');assert.match(describe(candidates[3],3).detail,/unknown/i);
assert.equal(JSON.stringify(candidates.map(describe)).includes('secret'),false);
assert.equal(parse('<html>#EXTM3U</html>',base),null);assert.equal(parse('#EXTM3U evil\n#EXTINF:1,\nx.ts',base),null);assert.equal(parse('x'.repeat(65537),base),null);
assert.equal(parse('\uFEFF#EXTM3U\r\n#EXTINF:2.4,\r\nx.ts\r\n#EXT-X-ENDLIST',base).duration,2);
assert.equal(parse('#EXTM3U\n#EXTINF:2,\nx.ts',base).duration,null);
const odd=parse('#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=123\nunknown.m3u8',base);assert.equal(odd.tracks[0].height,null);
const imagePath='https://cdn.example/image.jpg';assert.equal(parse(text,imagePath).role,'master'); // Body proof, never extension guessing.
const self=parse('#EXTM3U\n#EXT-X-STREAM-INF:RESOLUTION=1280x720\n'+base,base);assert.equal(self.variantCount,0);
assert.equal(parse('#EXTM3U\n#EXT-X-STREAM-INF:RESOLUTION=1280x720\nhttps://user:pass@cdn.example/video',base).variantCount,0);
console.log('HLS source labels: master/quality/audio/unknown, exact heights, CRLF/BOM, bounds and URL privacy checks passed');
