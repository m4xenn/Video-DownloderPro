"""Native Windows completion notifications using the application logo."""
import platform
from pathlib import Path
import sys
import threading
import uuid


def notification_icon_path():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'icon.ico'
    return Path(__file__).resolve().parents[2] / 'build_assets' / 'icon.ico'


def _notify(title, message):
    import win32gui, win32con, win32api
    hwnd = hicon = timer = None
    added = False
    classname = 'VideoDownloaderProNotify_' + uuid.uuid4().hex
    hinst = win32api.GetModuleHandle(None)
    registered = False
    try:
        wc = win32gui.WNDCLASS()
        wc.hInstance = hinst
        wc.lpszClassName = classname

        def wndproc(window, msg, wparam, lparam):
            if msg == win32con.WM_CLOSE:
                win32gui.DestroyWindow(window)
                return 0
            if msg == win32con.WM_DESTROY:
                win32gui.PostQuitMessage(0)
                return 0
            return win32gui.DefWindowProc(window, msg, wparam, lparam)

        wc.lpfnWndProc = wndproc
        win32gui.RegisterClass(wc)
        registered = True
        hwnd = win32gui.CreateWindow(classname, 'Video Downloader Pro', win32con.WS_OVERLAPPED,
                                     0, 0, 0, 0, 0, 0, hinst, None)
        hicon = win32gui.LoadImage(0, str(notification_icon_path()), win32con.IMAGE_ICON,
                                  32, 32, win32con.LR_LOADFROMFILE)
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        callback = win32con.WM_USER + 20
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD,
                                 (hwnd, 0, flags, callback, hicon, 'Video Downloader Pro'))
        added = True
        # NIIF_USER uses our hIcon instead of the standard information/warning icon.
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY,
            (hwnd, 0, win32gui.NIF_INFO, callback, hicon, 'Video Downloader Pro',
             str(message)[:255], 6000, str(title)[:63], 0x04))

        def request_close():
            try:
                # DestroyWindow must run on the window's owning notification thread.
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass

        timer = threading.Timer(6, request_close)
        timer.daemon = True
        timer.start()
        win32gui.PumpMessages()
    except Exception as exc:
        print('Native Notify Error:', exc)
    finally:
        if timer:
            timer.cancel()
        if added:
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 0))
            except Exception:
                pass
        if hwnd and win32gui.IsWindow(hwnd):
            win32gui.DestroyWindow(hwnd)
        if hicon:
            win32gui.DestroyIcon(hicon)
        if registered:
            win32gui.UnregisterClass(classname, hinst)


def show_notification(title, message):
    if platform.system() != 'Windows':
        return
    threading.Thread(target=_notify, args=(title, message), daemon=True).start()
