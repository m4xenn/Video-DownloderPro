"""Explicit isolated packaged startup check; does not install or publish."""
import json, os, subprocess, tempfile, time, urllib.request
from pathlib import Path
import psutil

root = Path(__file__).resolve().parents[1]
exe = root / 'dist/YoutubePro/YoutubePro.exe'
with tempfile.TemporaryDirectory(prefix='package-smoke-', dir=root / 'build') as temp:
    env = dict(os.environ, APPDATA=temp)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    proc = subprocess.Popen([str(exe)], env=env, startupinfo=startup)
    result = {'status': 'failed'}
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError('Packaged application exited: ' + str(proc.returncode))
            for conn in psutil.Process(proc.pid).net_connections(kind='tcp'):
                if conn.status == psutil.CONN_LISTEN and conn.laddr.ip in ('127.0.0.1', '::1'):
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:' + str(conn.laddr.port) + '/', timeout=2) as response:
                            html = response.read().decode('utf-8')
                        if 'Video Downloader Pro' in html and '1.2.13' in html:
                            result = {'status': 'passed', 'checks': ['packaged process running', 'local HTTP UI served', 'bundled version 1.2.13 rendered'], 'limits': 'No visual UI or installer upgrade verification.'}
                            break
                    except (OSError, UnicodeError):
                        pass
            if result['status'] == 'passed':
                break
            time.sleep(0.5)
        if result['status'] != 'passed':
            raise RuntimeError('Packaged UI did not serve the expected title/version')
    finally:
        parent = psutil.Process(proc.pid) if proc.poll() is None else None
        children = parent.children(recursive=True) if parent else []
        for child in reversed(children):
            try: child.terminate()
            except psutil.NoSuchProcess: pass
        if proc.poll() is None: proc.terminate()
        proc.wait(timeout=10)
        psutil.wait_procs(children, timeout=5)
    print(json.dumps(result, indent=2))
    (root / 'build/packaged-startup-1.2.13.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
