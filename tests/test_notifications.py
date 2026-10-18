import sys
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from services import notification_service as notifications

class NotificationTests(unittest.TestCase):
    def test_source_icon_exists(self):
        self.assertTrue(notifications.notification_icon_path().is_file())
    def test_frozen_icon(self):
        with patch.object(sys,'frozen',True,create=True), patch.object(sys,'_MEIPASS','C:/runtime',create=True):
            self.assertEqual(notifications.notification_icon_path(),Path('C:/runtime/icon.ico'))
    def test_logo_notification_and_cleanup(self):
        gui=Mock();gui.WNDCLASS.side_effect=SimpleNamespace
        gui.CreateWindow.return_value=123;gui.LoadImage.return_value=456
        gui.NIF_ICON=2;gui.NIF_MESSAGE=1;gui.NIF_TIP=4;gui.NIF_INFO=16
        gui.NIM_ADD=0;gui.NIM_MODIFY=1;gui.NIM_DELETE=2
        con=SimpleNamespace(WM_CLOSE=16,WM_DESTROY=2,WM_USER=1024,WS_OVERLAPPED=0,IMAGE_ICON=1,LR_LOADFROMFILE=16)
        api=Mock();api.GetModuleHandle.return_value=789
        timer=Mock()
        with patch.dict(sys.modules,{'win32gui':gui,'win32con':con,'win32api':api}), patch.object(notifications.threading,'Timer',return_value=timer):
            notifications._notify('Completed','Video saved')
        calls=gui.Shell_NotifyIcon.call_args_list
        self.assertEqual(calls[0].args[1][4],456)
        self.assertEqual(calls[1].args[1][-1],4)
        self.assertEqual(calls[1].args[1][4],456)
        self.assertEqual(calls[1].args[1][6],'Video saved')
        self.assertEqual(calls[-1].args,(2,(123,0)))
        gui.DestroyIcon.assert_called_once_with(456)
        timer.start.assert_called_once();timer.cancel.assert_called_once()
    def test_non_windows_skipped(self):
        with patch.object(notifications.platform,'system',return_value='Linux'),patch.object(notifications.threading,'Thread') as thread:
            notifications.show_notification('Done','Saved');thread.assert_not_called()
