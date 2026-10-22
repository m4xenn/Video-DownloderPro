"""Build one version-consistent executable + Inno Setup installer; never publishes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', help='New stable version, e.g. 1.1.2. Omit to use version.json.')
    parser.add_argument('--iscc', help='Path to Inno Setup 6 ISCC.exe')
    args = parser.parse_args()
    version = args.version or json.loads((ROOT / 'version.json').read_text(encoding='utf-8'))['version']
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', version):
        parser.error('Use a stable major.minor.patch version, without a v prefix.')
    iscc = args.iscc or shutil.which('ISCC.exe')
    if not iscc:
        for env in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA'):
            base = Path(os.environ.get(env, 'C:/'))
            for suffix in ('Inno Setup 6/ISCC.exe', 'Programs/Inno Setup 6/ISCC.exe'):
                candidate = base / suffix
                if candidate.exists():
                    iscc = str(candidate)
                    break
            if iscc:
                break
    if not iscc or not Path(iscc).is_file():
        parser.error('Inno Setup 6 compiler missing. Install it or supply --iscc PATH.')
    output = ROOT / 'releases' / f'v{version}'
    if output.exists():
        parser.error(f'{output} already exists. Use a new version; release files are not overwritten.')
    (ROOT / 'version.json').write_text(json.dumps({'version': version}, indent=2) + '\n', encoding='utf-8')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', 'YoutubePro.spec'], cwd=ROOT, check=True)
    command = [iscc, f'/DMyAppVersion={version}', f'/DProjectRoot={ROOT}', str(ROOT / 'build_assets/YoutubePro_Setup.iss')]
    for attempt in range(3):
        result = subprocess.run(command, cwd=ROOT, capture_output=True)
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        if result.returncode == 0:
            break
        # Windows may temporarily lock a newly created PE during resource updates.
        if attempt == 2 or b'EndUpdateResource failed' not in result.stdout + result.stderr:
            result.check_returncode()
        time.sleep(.5)
    installer = output / 'VideoDownloaderPro_Setup.exe'
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    (output / 'SHA256SUMS.txt').write_text(f'{digest}  {installer.name}\n', encoding='utf-8')
    (output / 'release-info.json').write_text(json.dumps({'tag': f'v{version}', 'version': version,
        'installer': installer.name, 'sha256': digest, 'size': installer.stat().st_size}, indent=2) + '\n', encoding='utf-8')
    print(f'Ready for manual testing and GitHub Release upload: {output}')


if __name__ == '__main__':
    main()
