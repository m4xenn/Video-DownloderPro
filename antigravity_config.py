# ============================================================
#  antigravity_config.py
#  YoutubePro — Uygulama Geneli Sabit Ayarlar
# ============================================================

import os
import sys
import json

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Frozen builds read their bundled metadata, never an older adjacent install file.
RESOURCE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(RESOURCE_DIR, 'version.json'), encoding='utf-8') as version_file:
    CURRENT_VERSION = 'v' + json.load(version_file)['version']
GITHUB_REPO = "m4xenn/Video-DownloderPro"
CONCURRENT_FRAGMENT_DOWNLOADS = 5
AUDIO_PREFERRED_QUALITY = "192"
DEFAULT_CONCURRENT_DOWNLOADS = 3
MAX_CONCURRENT_DOWNLOADS = 10
LEGACY_SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
SETTINGS_FILE = os.path.join(os.environ.get('APPDATA', BASE_DIR), 'YoutubePro', 'settings.json')
