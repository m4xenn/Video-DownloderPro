# ============================================================
#  src/services/media_service.py
#  Medya işleme mantıkları (ffmpeg vb.)
# ============================================================

import subprocess
import sys
import platform
import os

def generate_vtt_subtitles(target_path):
    """
    Hedef medya dosyasından (target_path) varsa ilk altyazıyı webvtt formatında 
    ayıklar ve bytes olarak döndürür. Başarısız olursa None döner.
    """
    try:
        cmd = ["ffmpeg", "-i", target_path, "-map", "0:s:0", "-c:s", "webvtt", "-f", "webvtt", "-"]
        if getattr(sys, 'frozen', False) or platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
        else:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
        if result.returncode == 0 and len(result.stdout) > 0:
            return result.stdout
    except Exception:
        pass
    return None

def compress_video(input_path, output_path, crf=28):
    try:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-c:v", "libx265", "-crf", str(crf),
            "-c:a", "copy", output_path
        ]
        
        if getattr(sys, 'frozen', False) or platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
        else:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
        if result.returncode == 0 and os.path.exists(output_path):
            return os.path.getsize(output_path)
    except Exception:
        pass
    return None
