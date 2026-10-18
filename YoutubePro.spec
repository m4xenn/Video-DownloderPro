# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata


a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('src/templates', 'templates'), ('src/static', 'static'), ('src/core', 'core'), ('src/state', 'state'), ('src/services', 'services'), ('src/utils', 'utils'), ('antigravity_config.py', '.'), ('version.json', '.')] + copy_metadata('yt-dlp'),
    hiddenimports=[],
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
