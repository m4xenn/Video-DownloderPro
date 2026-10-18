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
    def log_message(self,*args):pass
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
        (base/'player.html').write_text('''<div id="player" style="width:640px;height:360px"></div><script>
          if(window.parent!==window) fetch('/master.m3u8',{credentials:'same-origin'}).then(r=>r.text()).then(()=>{
            window.jwplayer=()=>({getPlaylist:()=>[{file:location.origin+'/master.m3u8',duration:2}],getContainer:()=>document.getElementById('player')});
          });</script>''')
        (base/'cookie.html').write_text('<h1>Cookie fixture</h1>'+ (base/'player.html').read_text().replace('if(window.parent!==window) ',''))
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
                    result['checks']+=['native yt-dlp failure -> hidden browser fallback','cross-origin dynamic nested iframe traversal preserving real parent','runtime JW Player API','180p/360p source qualities','scoped native request cookie capture']
                    for route,title in [('html5','HTML5 fixture'),('videojs','Video.js fixture'),('dash','DASH fixture'),('blob','Network blob fixture'),('cookie','Cookie fixture')]:
                        with YoutubeDL(options) as ydl:
                            extra=extract_media_info(ydl,origin+route+'.html')
                        assert extra['title']==title,(route,extra.get('title'))
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
                site_browser.close()
                main_window.destroy()
        try:
            webview.start(verify,gui='edgechromium',private_mode=True)
        finally:
            server.shutdown();server.server_close()
        print(json.dumps(result,indent=2))
        return 0 if result.get('status')=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
