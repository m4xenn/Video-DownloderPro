"""Windows-only isolated manual fixture for the real hidden WebView2 flow."""
import os
from pathlib import Path
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='site-preview-',dir=ROOT) as temporary:
        os.environ['VIDEO_DOWNLOADER_DATA_DIR']=temporary
        import app
        from utils import file_helpers
        file_helpers.SETTINGS_FILE=str(Path(temporary)/'settings.json')
        file_helpers.LEGACY_SETTINGS_FILE=str(Path(temporary)/'legacy-settings.json')
        app.state['current_download_path']=temporary
        from services.site_browser import site_browser
        import webview
        site_browser.enabled=True
        threading.Thread(target=lambda:app.app.run(host='127.0.0.1',port=5056,use_reloader=False),daemon=True).start()
        window=webview.create_window('Isolated site inspection test', 'http://127.0.0.1:5056',hidden=True)
        try:
            webview.start(gui='edgechromium',private_mode=True)
        finally:
            site_browser.close()
            app.download_manager.close()
