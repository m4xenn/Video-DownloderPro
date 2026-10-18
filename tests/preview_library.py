"""Isolated, synthetic UI fixture server. Never reads the user's queue/history."""
import os
from pathlib import Path
import sys
import tempfile
import time
import argparse
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--empty', action='store_true')
    parser.add_argument('--black-start', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='library-preview-', dir=ROOT) as temporary:
        folder = Path(temporary)
        os.environ['VIDEO_DOWNLOADER_DATA_DIR'] = str(folder)
        import app
        from utils import file_helpers
        file_helpers.SETTINGS_FILE = str(folder / 'settings.json')
        file_helpers.LEGACY_SETTINGS_FILE = str(folder / 'legacy-settings.json')
        options = {'format':'video','quality':'max','embed_subs':False}
        from flask import send_file
        sample = folder / 'Studio sample.mp4'
        ffmpeg = Path(os.environ['APPDATA']) / 'YoutubePro/bin/ffmpeg.exe'
        if args.black_start:
            subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error',
                '-f','lavfi','-i','color=c=black:s=640x360:r=24:d=1',
                '-f','lavfi','-i','testsrc2=s=640x360:r=24:d=3',
                '-f','lavfi','-i','sine=frequency=440',
                '-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]','-map','2:a',
                '-t','4','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(sample)],check=True)
        else:
            subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=s=640x360:r=24',
                '-f','lavfi','-i','sine=frequency=440','-t','4','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(sample)],check=True)
        @app.app.route('/fixture/sample.mp4')
        def fixture_sample():
            return send_file(sample, mimetype='video/mp4')
        for name,height,width in [('low',180,320),('high',360,640)]:
            subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-i',str(sample),'-vf',f'scale={width}:{height}',
                '-c:v','libx264','-c:a','aac','-hls_time','1','-hls_list_size','0','-hls_segment_filename',
                str(folder/f'{name}-%d.ts'),str(folder/f'{name}.m3u8')],check=True)
        (folder/'master.m3u8').write_text('#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=250000,RESOLUTION=320x180,FRAME-RATE=24\nlow.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=900000,RESOLUTION=640x360,FRAME-RATE=24\nhigh.m3u8\n')
        @app.app.route('/fixture/<path:name>')
        def fixture_media(name):
            from flask import send_from_directory
            return send_from_directory(folder,name)
        media = folder / 'Örnek eğitim videosu.mp4'
        media.write_bytes(b'UI fixture only')
        record = {'id':'example','media_key':'youtube:example','url':'https://youtube.com/watch?v=example',
                  'title':'Örnek eğitim videosu','thumbnail':'','format':'video','quality':'max','embed_subs':False,
                  'path':str(media),'size':134217728,'completed_at':'2026-10-17T00:00:00+00:00'}
        missing = dict(record,id='missing',title='Taşınmış video örneği',path=str(folder/'missing.mp4'))
        from core.queue_manager import Job
        from dataclasses import asdict
        job = Job('https://example.com/paused.mp4',options,str(folder),'',title='Yarım kalan indirme',
                  total_bytes=268435456,percent=42,status='downloading')
        job_record = asdict(job); job_record.pop('future',None)
        app.download_store.commit_queue([] if args.empty else [job_record],[] if args.empty else [record,missing])
        app.download_store.save_drafts([] if args.empty else [{'url':'https://youtube.com/watch?v=example','title':'Örnek eğitim videosu','thumbnail':''}])
        app.state['current_download_path'] = str(folder)
        def preview(token,urls):
            entries = [{'id':str(i),'url':f'https://example.com/video-{i}','title':title,
                'group':'Eğitim Serisi','available':i!=3,'thumbnail':'','media_key':f'fixture:{i}',
                'duration':120+i*35,'total_bytes':(i+1)*33554432} for i,title in enumerate([
                    '01 · Başlangıç ve kurulum','02 · Temel kullanım','03 · İleri seviye ayarlar','Gizli video'])]
            with app.media_catalog.lock:
                app.media_catalog.previews[token].update(status='ready',entries=entries,truncated=False)
        app.media_catalog._preview = preview
        app.ensure_download_state()
        try:
            app.app.config['TEMPLATES_AUTO_RELOAD'] = True
            app.app.run(host='127.0.0.1',port=5056,use_reloader=False)
        finally:
            app.download_manager.close()
