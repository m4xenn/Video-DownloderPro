# ============================================================
#  src/services/folder_service.py
#  İşletim sistemine özel klasör seçme diyalogları
#
#  app.py'den taşındı (FAZ 4c)
# ============================================================

import platform
import subprocess

def open_folder_dialog():
    """
    Kullanıcının klasör seçebilmesi için OS native diyalog penceresi açar.
    Windows için Tkinter, macOS için AppleScript (osascript) kullanır.
    """
    system_name = platform.system()
    if system_name == "Darwin": # macOS
        try:
            script = 'POSIX path of (choose folder with prompt "Lütfen İndirme Konumunu Seçin")'
            proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if proc.returncode == 0:
                return proc.stdout.strip()
        except Exception as e:
            print(f"Mac Dialog Hatası: {e}")
            return None
    else: # Windows
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            folder_selected = filedialog.askdirectory()
            root.destroy()
            return folder_selected
        except Exception as e:
            print(f"Windows Dialog Hatası: {e}")
            return None
    return None
