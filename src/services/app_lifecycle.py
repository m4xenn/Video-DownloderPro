"""Single desktop instance and a vetoable, durable window shutdown."""
import ctypes
import json
import os
from pathlib import Path
import sys
import threading


def lifecycle_text(language=None):
    if language is None:
        from services.language_service import system_language
        from utils.file_helpers import load_settings
        language = load_settings().get('language') or system_language()
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    data = json.loads((root / 'static' / 'recovery-locales.json').read_text(encoding='utf-8'))
    return data.get(language, data['en'])


class SingleInstance:
    """Windows closes the named mutex handle even after a process crash."""
    def __init__(self, name='Local\\VideoDownloaderPro.Desktop'):
        self.name = name
        self.handle = None

    def acquire(self):
        if os.name != 'nt':
            raise OSError('Video Downloader Pro desktop requires Windows.')
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle.restype = ctypes.c_bool
        self.kernel = kernel
        handle = kernel.CreateMutexW(None, False, self.name)
        error = ctypes.get_last_error()
        if not handle:
            raise ctypes.WinError(error)
        if error == 183:  # ERROR_ALREADY_EXISTS
            kernel.CloseHandle(handle)
            return False
        self.handle = handle
        return True

    def close(self):
        if self.handle is not None:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def native_notice(message, error=False):
    ctypes.windll.user32.MessageBoxW(None, message, 'Video Downloader Pro', 0x10 if error else 0x40)


class ShutdownController:
    """Keep the GUI alive until workers stop and their checkpoint is durable."""
    def __init__(self, window, manager, cleanup, text=None):
        self.window, self.manager, self.cleanup = window, manager, cleanup
        self.text = text or lifecycle_text
        self.lock = threading.RLock()
        self.saving = False
        self.allowed = False
        self.worker = None

    def on_closing(self):
        with self.lock:
            if self.allowed:
                return True
            if self.saving:
                return False
            words = self.text()
            if self.manager.busy() and not self.window.create_confirmation_dialog(
                    words['closeTitle'], words['closeMessage']):
                return False
            self.saving = True
            # Never wait for network workers on the native UI thread: a retained
            # browser may need that thread to close its window during cancellation.
            self.worker = threading.Thread(target=self._save_and_close, daemon=False,
                                           name='durable-shutdown')
            self.worker.start()
            return False

    def _save_and_close(self):
        try:
            self.window.evaluate_js('window.setShutdownState && window.setShutdownState(true)')
        except Exception:
            pass
        try:
            self.manager.close()
        except Exception:
            # A failed disk write must not silently close the only visible UI.
            with self.lock:
                self.saving = False
            try:
                self.window.evaluate_js('window.setShutdownState && window.setShutdownState(false, true)')
            except Exception:
                pass
            native_notice(self.text()['saveFailed'], error=True)
            return
        try:
            self.cleanup()
        finally:
            with self.lock:
                self.allowed = True
            self.window.destroy()
