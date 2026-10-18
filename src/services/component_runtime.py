"""Select the verified Python yt-dlp distribution before its first import."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import zipfile

BIN_DIR = Path(os.environ.get('APPDATA', str(Path.home()))) / 'YoutubePro' / 'bin'


def read_manifest(bin_dir=BIN_DIR):
    try:
        data = json.loads((Path(bin_dir) / 'components.json').read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            return {}
        return {name: record for name, record in data.items()
                if name in ('yt-dlp', 'ffmpeg') and isinstance(record, dict)
                and isinstance(record.get('version'), str)}
    except (OSError, ValueError):
        return {}


def verified_engine(bin_dir=BIN_DIR):
    try:
        record = read_manifest(bin_dir).get('yt-dlp', {})
        name = record['file']
        if Path(name).name != name or not name.startswith('yt-dlp-') or not name.endswith('.zip'):
            return None
        path = Path(bin_dir) / name
        if path.stat().st_size > 20 * 1024 * 1024:
            return None
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            return None
        with zipfile.ZipFile(path) as archive:
            if not {'yt_dlp/__init__.py', 'yt_dlp/version.py'}.issubset(archive.namelist()):
                return None
        return path
    except (KeyError, TypeError, OSError, ValueError, zipfile.BadZipFile):
        return None


def activate_engine():
    engine = verified_engine()
    if engine:
        from packaging.version import Version
        try:
            bundled = importlib.metadata.version('yt-dlp')
            pending = read_manifest()['yt-dlp']['version']
            if Version(pending) > Version(bundled):
                sys.path.insert(0, str(engine))
        except (importlib.metadata.PackageNotFoundError, ValueError, KeyError):
            # Never override a bundled engine when its version cannot be established.
            pass


def runtime_version():
    try:
        from yt_dlp.version import __version__
        return __version__
    except ImportError:
        return None
