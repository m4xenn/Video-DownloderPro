"""Windows WebView2 end-to-end check using only synthetic, temporary local media.

Run explicitly: python tests/verify_generic_native.py
The public-address guard is relaxed ONLY inside this fixture for its local server.
"""
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


class Handler(http.server.SimpleHTTPRequestHandler):
    handoff_check=None
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path.split('?')[0].endswith('.ts') and type(self).handoff_check:
            check=type(self).handoff_check;type(self).handoff_check=None;check()
        super().do_GET()
    def translate_path(self,path):
        return super().translate_path('/master.m3u8' if path.split('?')[0]=='/opaque-stream' else path)
    def guess_type(self,path):
        if str(path).endswith('.m3u8'):return 'application/vnd.apple.mpegurl'
        return super().guess_type(path)
    def end_headers(self):
        if self.path in ('/player.html','/cookie.html'):self.send_header('Set-Cookie','media_session=fixture; HttpOnly; SameSite=Lax; Path=/')
        super().end_headers()


def main():
    import webview
    from yt_dlp import YoutubeDL
    from services.site_browser import site_browser
    from services.site_resolver import extract_media_info
    from services.generic_resolver import generic_resolver
    from services.media_discovery import public_url
    bin_dir=Path(os.environ['APPDATA'])/'YoutubePro/bin'
    result={'checks':[]}
    with tempfile.TemporaryDirectory(prefix='site-preview-generic-',dir=ROOT) as temporary:
        base=Path(temporary)
        for height,width in [(180,320),(360,640)]:
            subprocess.run([str(bin_dir/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-f','lavfi','-i',f'testsrc2=s={width}x{height}:r=10','-f','lavfi','-i','sine=frequency=440','-t','2','-c:v','libx264','-preset','ultrafast','-g','10','-c:a','aac','-hls_time','1','-hls_playlist_type','vod',str(base/f'{height}.m3u8')],check=True,timeout=30)
        (base/'master.m3u8').write_text('#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=300000,RESOLUTION=320x180,FRAME-RATE=10,CODECS="avc1.42c00b,mp4a.40.2"\n180.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,FRAME-RATE=10,CODECS="avc1.42c01e,mp4a.40.2"\n360.m3u8\n')
        (base/'index.html').write_text('''<h1>Generic discovery fixture</h1><script>
          setTimeout(()=>{const frame=document.createElement('iframe');frame.width=700;frame.height=400;frame.src=location.origin.replace('127.0.0.1','localhost')+'/outer.html';document.body.append(frame)},150);
        </script>''')
        (base/'outer.html').write_text('''<script>setTimeout(()=>{const f=document.createElement('iframe');f.width=640;f.height=360;f.src=location.origin.replace('localhost','127.0.0.1')+'/player.html';document.body.append(f)},150)</script>''')
        (base/'player.html').write_text('''<div id="player" class="jwplayer" style="width:640px;height:360px"></div><script>
          let ready=false,muted=false;
          window.jwplayer=()=>({getPlaylist:()=>ready?[{file:location.origin+'/master.m3u8',duration:2}]:[],
            getContainer:()=>document.getElementById('player'),setMute:value=>{muted=value},
            play:()=>{if(muted && window.parent!==window) fetch('/master.m3u8',{credentials:'same-origin'}).then(r=>r.text()).then(()=>ready=true)}});
          </script>''')
        (base/'cookie.html').write_text('<h1>Cookie fixture</h1>'+ (base/'player.html').read_text().replace('muted && window.parent!==window','muted'))
        (base/'gate.html').write_text('''<h1>Lazy iframe fixture</h1>
          <div style="width:640px;height:360px">
            <div aria-label="Play video" style="width:640px;height:360px" onclick="
              this.hidden=true;const box=this.nextElementSibling;box.hidden=false;
              const frame=box.querySelector('iframe');frame.src=frame.dataset.src;">Play</div>
            <div hidden><iframe width="640" height="360" data-src="/player.html"></iframe></div>
          </div>''')
        subprocess.run([str(bin_dir/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-i',str(base/'360.m3u8'),'-c','copy',str(base/'native.mp4')],check=True,timeout=30)
        subprocess.run([str(bin_dir/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-i',str(base/'native.mp4'),'-c','copy','-f','dash',str(base/'native.mpd')],check=True,timeout=30)
        (base/'html5.html').write_text('''<h1>HTML5 fixture</h1><script>setTimeout(()=>{
          const video=document.createElement('video');video.width=640;video.height=360;video.src=location.origin+'/native'+'.mp4';document.body.append(video);
        },150)</script>''')
        (base/'videojs.html').write_text('''<h1>Video.js fixture</h1><div id="p" style="width:640px;height:360px"></div><script>
          window.videojs={getAllPlayers:()=>[{id:()=>'p',el:()=>document.getElementById('p'),duration:()=>2,currentSources:()=>[{src:location.origin+'/native'+'.mp4'}],currentSource:()=>({})}]};
        </script>''')
        (base/'dash.html').write_text('''<h1>DASH fixture</h1><div id="p" style="width:640px;height:360px"></div><script>
          window.jwplayer=()=>({getPlaylist:()=>[{file:location.origin+'/native'+'.mpd'}],getContainer:()=>document.getElementById('p')});
        </script>''')
        (base/'blob.html').write_text('''<h1>Network blob fixture</h1><script>
          const video=document.createElement('video');video.width=640;video.height=360;
          video.src=URL.createObjectURL(new Blob(['fixture'],{type:'video/mp4'}));document.body.append(video);
          fetch('/master.m3u8');
        </script>''')
        (base/'network.html').write_text('''<h1>Opaque network fixture</h1><canvas width="640" height="360"></canvas>
          <script>fetch('/opaque-stream').then(r=>r.text());</script>''')
        (base/'network-frame.html').write_text('''<h1>Opaque iframe network fixture</h1><script>
          const f=document.createElement('iframe');f.width=640;f.height=360;
          f.src=location.origin.replace('127.0.0.1','localhost')+'/network.html';document.body.append(f);
          </script>''')
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(base)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        page=f'http://127.0.0.1:{server.server_port}/index.html'
        # Only this exact local fixture origin is admitted by the test override.
        origin=page.rsplit('/',1)[0]+'/'
        origins=(origin,origin.replace('127.0.0.1','localhost'))
        def fixture_url(value,resolve=False):
            return (isinstance(value,str) and value.startswith(origins)) or public_url(value,resolve=resolve)
        main_window=webview.create_window('Isolated generic discovery fixture',html='<html>Test fixture</html>',hidden=True)
        site_browser.enabled=True
        def verify():
            try:
                with patch('services.generic_resolver.public_url',side_effect=fixture_url),patch('services.media_discovery.public_url',side_effect=fixture_url):
                    options={'quiet':True,'noprogress':True,'no_warnings':True,'ffmpeg_location':str(bin_dir),'socket_timeout':5}
                    with YoutubeDL(options) as ydl:
                        info=extract_media_info(ydl,page)
                    assert info['title']=='Generic discovery fixture',info.get('title')
                    assert info['webpage_url']==page and info['extractor_key']=='EmbeddedMedia'
                    heights=sorted({f.get('height') for f in info['formats'] if f.get('height')})
                    assert heights==[180,360],heights
                    result['checks']+=['native yt-dlp failure -> hidden browser fallback','cross-origin dynamic nested iframe traversal preserving real parent','muted automatic JW Player activation before source is available','180p/360p source qualities','scoped native request cookie capture']
                    for route,title in [('html5','HTML5 fixture'),('videojs','Video.js fixture'),('dash','DASH fixture'),('blob','Network blob fixture'),('cookie','Cookie fixture'),('gate','Lazy iframe fixture'),('network','Opaque network fixture'),('network-frame','Opaque iframe network fixture')]:
                        with YoutubeDL(options) as ydl:
                            extra=extract_media_info(ydl,origin+route+'.html')
                        assert extra['title']==title,(route,extra.get('title'))
                        if route.startswith('network'):
                            assert generic_resolver.cache[origin+route+'.html'][1]['discovery_method']=='network'
                            assert {f.get('height') for f in extra['formats']} >= {180,360}
                        if route=='dash':
                            assert any(f.get('height')==360 for f in extra['formats'])
                            assert any(f.get('acodec') not in ('none',None) for f in extra['formats'])
                        if route=='cookie':
                            context=generic_resolver.cache[origin+'cookie.html'][1]['source_headers'][origin+'master.m3u8']
                            assert 'media_session=fixture' in context.get('Cookie',''),'Native request cookie missing'
                        result['checks'].append(route+': dynamic source inspection and metadata')
                    for label,selector,expected in [('selected','best[height<=180]',180),('maximum','best',360)]:
                        with YoutubeDL(dict(options,format=selector,outtmpl=str(base/f'{label}.%(ext)s'))) as ydl:
                            downloaded=extract_media_info(ydl,page,fresh=True)
                            ydl.process_ie_result(downloaded,download=True)
                        file=next(base.glob(label+'.*'))
                        probe=json.loads(subprocess.check_output([str(bin_dir/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(file)]))
                        assert next(s for s in probe['streams'] if s['codec_type']=='video')['height']==expected
                        assert any(s['codec_type']=='audio' for s in probe['streams'])
                        result['checks'].append(f'{label}: {expected}p HLS download with audio')
                    assert site_browser.session is None,'Helper window leaked'
                    from core.downloader import _download_single
                    from core.format_resolver import get_ydl_opts
                    generic_resolver.cache.pop(origin+'network-frame.html',None)
                    phases=[];held=[]
                    Handler.handoff_check=lambda:held.append(bool(site_browser.handoffs))
                    options=get_ydl_opts('video','source:180:10',str(base),0,False,lambda _:None,str(bin_dir))
                    options.update(ignoreerrors=False,concurrent_fragment_downloads=1,socket_timeout=5)
                    assert _download_single(origin+'network-frame.html',options,str(base),{'format':'video','quality':'source:180:10','_stage':phases.append})
                    assert held==[True],held
                    assert not site_browser.handoffs,'Handoff browser leaked after first media bytes'
                    assert 'validating_source' in phases and 'downloading' in phases,phases
                    result['checks'].append('browser retained through first segment request and released after media bytes')
                    from services.source_operation import source_operation
                    generic_resolver.cache.pop(origin+'network-frame.html',None)
                    with source_operation(retain='preview'):
                        with YoutubeDL({'quiet':True,'no_warnings':True}) as preview:
                            extract_media_info(preview,origin+'network-frame.html')
                    assert site_browser.handoffs,'Preview browser closed before download handoff'
                    held.clear();Handler.handoff_check=lambda:held.append(bool(site_browser.handoffs))
                    assert _download_single(origin+'network-frame.html',options,str(base),{'format':'video','quality':'source:180:10'})
                    assert held==[True] and not site_browser.handoffs
                    result['checks'].append('metadata preview browser handed to cached download and released after first bytes')
                    result['checks'].append('helper windows cleaned up')
                    result['status']='passed'
            except Exception as exc:
                import traceback
                result['status']='failed';result['error']=str(exc);traceback.print_exc()
                if site_browser.session:
                    session=site_browser.session
                    result['diagnostic']={'snapshot':session.get('evaluation_result'),
                        'media_responses':[{'url':item['url'],'referer':item['headers'].get('Referer')} for item in session['candidates']]}
            finally:
                site_browser.close_all()
                main_window.destroy()
        try:
            webview.start(verify,gui='edgechromium',private_mode=True)
        finally:
            server.shutdown();server.server_close()
        print(json.dumps(result,indent=2))
        return 0 if result.get('status')=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
