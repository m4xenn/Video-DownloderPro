"""Explicit isolated /get-info probe through the real application's full source flow."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('url');parser.add_argument('--output',default='build/app-info-probe.json')
    args=parser.parse_args()
    from services.media_discovery import public_url
    if not public_url(args.url,resolve=True):parser.error('Public page URL required')
    with tempfile.TemporaryDirectory(prefix='site-preview-app-',dir=ROOT) as folder:
        os.environ['VIDEO_DOWNLOADER_DATA_DIR']=folder
        import app,webview
        from services.site_browser import site_browser
        site_browser.enabled=True
        window=webview.create_window('Isolated application metadata test',html='<html>Metadata probe</html>',hidden=True)
        result={}
        original_extract=app.extract_media_info
        def inspect_extract(*a,**kw):
            try:return original_extract(*a,**kw)
            except Exception as error:
                import traceback
                result['error_functions']=[frame.name for frame in traceback.extract_tb(error.__traceback__)][-12:]
                result['error_phase']=app.source_progress.get(args.url)
                result['handoffs_at_error']=len(site_browser.handoffs)
                raise
        app.extract_media_info=inspect_extract
        def run():
            try:
                response=app.app.test_client().post('/get-info',json={'url':args.url})
                data=response.get_json()
                result.update(status=data.get('status'),duration=data.get('duration'),
                    qualities=[item.get('value') for item in data.get('video_qualities',[])],
                    handoffs=len(site_browser.handoffs),error_code=data.get('error_code'))
            except Exception:
                result['status']='failed'
            finally:
                site_browser.close_all();app.download_manager.close();window.destroy()
        webview.start(run,gui='edgechromium',private_mode=True)
        path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
        return 0 if result.get('status')=='success' else 1


if __name__=='__main__':raise SystemExit(main())
