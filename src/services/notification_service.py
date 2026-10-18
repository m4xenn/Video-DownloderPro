# ============================================================
#  src/services/notification_service.py
#  İşletim sistemi tabanlı yerel bildirimler (Windows native)
#
#  app.py'den taşındı (FAZ 4b)
# ============================================================

import platform
import threading
import time

def show_notification(title, message):
    """
    Windows üzerinde native görev çubuğu bildirimi gösterir.
    Mac/Linux üzerinde henüz çalışmıyor, anında döner.
    """
    if platform.system() != "Windows": return
    
    def _notify():
        try:
            import win32gui, win32con, win32api
            wc = win32gui.WNDCLASS()
            hinst = wc.hInstance = win32api.GetModuleHandle(None)
            wc.lpszClassName = "YoutubeProNotifyTaskbar"
            
            def wndproc(hwnd, msg, wparam, lparam):
                if msg == win32con.WM_DESTROY:
                    win32gui.PostQuitMessage(0)
                elif msg == win32con.WM_TIMER:
                    win32gui.DestroyWindow(hwnd)
                return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
                
            wc.lpfnWndProc = wndproc
            try: win32gui.RegisterClass(wc)
            except: pass
            
            hwnd = win32gui.CreateWindow(wc.lpszClassName, "Taskbar", win32con.WS_OVERLAPPED, 0, 0, 0, 0, 0, 0, hinst, None)
            
            try: hicon = win32gui.LoadIcon(hinst, 1)
            except: hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
            
            flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
            nid = (hwnd, 0, flags, win32con.WM_USER+20, hicon, "YoutubePro")
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, (hwnd, 0, win32gui.NIF_INFO, win32con.WM_USER+20, hicon, "Tooltip", message, 200, title, 1))
            
            # Start a timer to kill it securely instead of blocking
            try:
                import win32ui
                win32gui.SetTimer(hwnd, 1, 6000, 0)
            except:
                threading.Thread(target=lambda: (time.sleep(6), win32gui.DestroyWindow(hwnd))).start()
                
            win32gui.PumpMessages()
            
            try: win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 0))
            except: pass
        except Exception as e:
            print("Native Notify Error:", e)
    
    threading.Thread(target=_notify, daemon=True).start()
