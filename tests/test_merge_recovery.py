"""A real Windows sharing lock is released without redoing merge/network work."""
import ctypes
import errno
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from services.merge_recovery import finish_locked_merge
from core.bandwidth import DownloadPaused


class MergeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'build')
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name)/'final.mp4'
        self.part = self.target.with_name('final.temp.mp4'); self.part.write_bytes(b'completed fixture')
        self.source = self.target.with_name('source.m4a'); self.source.write_bytes(b'source')
        self.info = dict(filepath=str(self.target), __files_to_merge=[str(self.source)], requested_formats=[dict(acodec='aac')])
        self.error = PermissionError(errno.EACCES, 'locked', str(self.part), None, str(self.target))

    def test_real_windows_lock_release_preserves_bytes_and_returns_cleanup_list(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateFileW(str(self.part), 0x80000000, 1, None, 3, 0x80, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        timer = threading.Timer(.3, lambda: kernel.CloseHandle(handle)); timer.start()
        try:
            with patch('services.merge_recovery.validate_output', return_value=dict(video=True,audio=True)):
                files, info = finish_locked_merge(self.error, self.info, '', lambda:False)
            self.assertEqual(self.target.read_bytes(), b'completed fixture')
            self.assertEqual(files, [str(self.source)]); self.assertTrue(self.source.exists())
        finally:
            timer.join()

    def test_cancellation_preserves_temporary_and_sources(self):
        with patch('services.merge_recovery.validate_output', return_value=dict(video=True,audio=True)), self.assertRaises(DownloadPaused):
            finish_locked_merge(self.error,self.info,'',lambda:True)
        self.assertTrue(self.part.exists()); self.assertFalse(self.target.exists())

    def test_lock_timeout_preserves_files(self):
        with patch('services.merge_recovery.validate_output',return_value=dict(video=True,audio=True)), patch('services.merge_recovery.os.rename',side_effect=self.error),self.assertRaises(PermissionError):
            finish_locked_merge(self.error,self.info,'',lambda:False,timeout=0)
        self.assertTrue(self.part.exists());self.assertTrue(self.source.exists());self.assertFalse(self.target.exists())

    def test_existing_target_is_never_overwritten(self):
        self.target.write_bytes(b'existing')
        with self.assertRaises(PermissionError): finish_locked_merge(self.error,self.info,'',lambda:False)
        self.assertEqual(self.target.read_bytes(),b'existing');self.assertTrue(self.part.exists())

    def test_unrelated_file_error_or_missing_audio_is_not_finalized(self):
        error = PermissionError(errno.EACCES,'locked',str(self.source),None,str(self.target))
        with self.assertRaises(PermissionError): finish_locked_merge(error,self.info,'',lambda:False)
        with patch('services.merge_recovery.validate_output',return_value=dict(video=True,audio=False)),self.assertRaises(PermissionError):
            finish_locked_merge(self.error,self.info,'',lambda:False)
        self.assertTrue(self.part.exists());self.assertTrue(self.source.exists())

if __name__ == '__main__': unittest.main()
