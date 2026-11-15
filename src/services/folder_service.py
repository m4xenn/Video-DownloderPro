# ============================================================
#  src/services/folder_service.py
#  İşletim sistemine özel klasör seçme diyalogları
#
#  app.py'den taşındı (FAZ 4c)
# ============================================================

import platform
import subprocess
import threading

_dialog_lock = threading.Lock()


class FolderDialogError(RuntimeError):
    def __init__(self, key='folder_dialog_failed'):
        self.key = key
        super().__init__(key)

def open_folder_dialog():
    """Use the desktop's owned native picker; None means user cancellation."""
    if not _dialog_lock.acquire(blocking=False):
        raise FolderDialogError('folder_dialog_busy')
    try:
        import webview
        if webview.windows:
            try:
                selected = webview.windows[0].create_file_dialog(webview.FileDialog.FOLDER)
                if not selected:
                    return None
                if not isinstance(selected, (list, tuple)) or len(selected) != 1 or not isinstance(selected[0], str) or not selected[0]:
                    raise FolderDialogError()
                return selected[0]
            except FolderDialogError:
                raise
            except Exception as error:
                raise FolderDialogError() from error
        if platform.system() != 'Darwin':
            raise FolderDialogError('folder_desktop_required')
        # Keep the standalone macOS fallback; selected paths are never code.
        try:
            script = 'POSIX path of (choose folder with prompt "Lütfen İndirme Konumunu Seçin")'
            proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if proc.returncode == 0:
                return proc.stdout.strip() or None
            if '-128' in (proc.stderr or ''):
                return None
            raise FolderDialogError()
        except FolderDialogError:
            raise
        except Exception as error:
            raise FolderDialogError() from error
    finally:
        _dialog_lock.release()
