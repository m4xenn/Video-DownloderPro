# ============================================================
#  src/utils/file_helpers.py
#  Dosya okuma/yazma yardımcıları
#
#  app.py'den taşındı (FAZ 1):
#    - load_settings()          (orijinal L54-60)
#    - save_settings_to_file()  (orijinal L62-64)
#    - load_history()           (orijinal L66-72)
#    - save_history()           (orijinal L74-76)
#    - add_to_history()         (orijinal L78-82)
#
#  Not: SETTINGS_FILE ve HISTORY_FILE sabitleri FAZ 2'de
#       antigravity.config.py'e taşınacak.
# ============================================================

import os
import sys
import json
import uuid

# Kök dizini sys.path'e ekle ki antigravity_config'i bulabilelim
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from antigravity_config import SETTINGS_FILE, LEGACY_SETTINGS_FILE, DEFAULT_CONCURRENT_DOWNLOADS
except ImportError:
    SETTINGS_FILE = "settings.json"
    DEFAULT_CONCURRENT_DOWNLOADS = 3
    LEGACY_SETTINGS_FILE = "settings.json"



from utils.download_settings import DEFAULTS, normalize_settings


def load_settings():
    for filename in (SETTINGS_FILE, LEGACY_SETTINGS_FILE):
        if os.path.exists(filename):
            try:
                with open(filename, encoding='utf-8') as source:
                    return normalize_settings(json.load(source))
            except (ValueError, OSError, TypeError):
                continue
    return dict(DEFAULTS)


def save_settings_to_file(data):
    normalized = normalize_settings(data)
    from pathlib import Path
    import tempfile
    path = Path(SETTINGS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix='.json.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as destination:
            json.dump(normalized, destination, ensure_ascii=False, indent=4)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
