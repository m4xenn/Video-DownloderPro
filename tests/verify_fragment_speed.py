"""Controlled per-connection throttle benchmark, not a prediction of public-CDN speed."""
import functools,http.server,json,os
from pathlib import Path
import subprocess,sys,tempfile,threading,time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from yt_dlp import YoutubeDL
from services.hls_metadata import extract_hls
from services.output_validation import validate_output

def main():
    binaries=Path(os.environ['APPDATA'])/'YoutubePro/bin'
    with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='fragment-speed-') as folder:
        base=Path(folder)
        subprocess.run([str(binaries/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=s=640x360:r=30',
            '-f','lavfi','-i','sine=frequency=440','-t','6','-c:v','libx264','-preset','ultrafast','-crf','12','-g','30',
            '-c:a','aac','-hls_time','1','-hls_playlist_type','vod',str(base/'index.m3u8')],check=True,timeout=30)
        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
            def copyfile(self,source,output):
                while True:
                    part=source.read(8192)
                    if not part:return
                    try:output.write(part);output.flush()
                    except (OSError,BrokenPipeError):return
                    if self.path.endswith('.ts'):time.sleep(len(part)/180000)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(base)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        results=[]
        try:
            for fragments in (1,2):
                output=base/f'run-{fragments}.mp4'
                options=dict(quiet=True,no_warnings=True,ffmpeg_location=str(binaries),concurrent_fragment_downloads=fragments,
                             ignoreerrors=False,fragment_retries=0,skip_unavailable_fragments=False,outtmpl=str(output))
                with patch('services.media_discovery.public_url',return_value=True),YoutubeDL(options) as ydl:
                    info=extract_hls(ydl,f'http://127.0.0.1:{server.server_port}/index.m3u8','fixture','Fixture')
                    start=time.monotonic();ydl.process_ie_result(info,download=True);elapsed=time.monotonic()-start
                validate_output(output,str(binaries),True,expected_duration=6,expect_audio=True)
                results.append(dict(fragments=fragments,seconds=round(elapsed,3),bytes=output.stat().st_size,verified_audio_video=True))
        finally:server.shutdown();server.server_close();thread.join(3)
        report=dict(environment='synthetic per-connection throttle at 180000 bytes/s',runs=results,
                    speedup=round(results[0]['seconds']/results[1]['seconds'],2),public_cdn_claim=False)
        (ROOT/'build/fragment-speed-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))

if __name__=='__main__':main()
