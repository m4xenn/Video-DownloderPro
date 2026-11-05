# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata, collect_all
import sys
sys.path.insert(0,SPECPATH)
from vdp_build_runtime import require_secure_python

require_secure_python()

transport_datas, transport_binaries, transport_imports = collect_all("curl_cffi")


a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=transport_binaries,
    datas=[('browser-extension', 'browser-extension'), ('dist/BrowserBridge/VDPBrowserBridge.exe', 'browser-bridge'), ('build_assets/icon.ico', '.'), ('src/templates', 'templates'), ('src/static', 'static'), ('src/core', 'core'), ('src/state', 'state'), ('src/services', 'services'), ('src/utils', 'utils'), ('antigravity_config.py', '.'), ('version.json', '.')] + copy_metadata('yt-dlp') + transport_datas,
    hiddenimports=transport_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='YoutubePro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='build_assets/icon.ico',
)

# Install extracted dependencies once; avoid one-file extraction at every launch.
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name='YoutubePro')
