"""Native launch options without creating a real app window or touching user data."""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, MagicMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import main

class WindowTests(unittest.TestCase):
    def test_launch_maximized_with_shared_app_icon(self):
        webview=Mock()
        webview.create_window.return_value.events.closed=MagicMock()
        application=SimpleNamespace(app=object(),download_manager=Mock(),ensure_download_state=Mock())
        browser=Mock()
        with patch.dict(sys.modules,{'webview':webview,'app':application,'services.site_browser':SimpleNamespace(site_browser=browser)}):
            main.start_window()
        options=webview.create_window.call_args.kwargs
        self.assertTrue(options['maximized'])
        self.assertTrue(options['resizable'])
        self.assertEqual(options['min_size'],(600,500))
        self.assertTrue(Path(webview.start.call_args.kwargs['icon']).is_file())
        application.download_manager.close.assert_called_once()
        browser.close_all.assert_called_once()
