"""subprocess-compatible entry point for native media parsers only."""
import os
from pathlib import Path
import subprocess as _subprocess
import threading
from collections import deque

PIPE = _subprocess.PIPE
STDOUT = _subprocess.STDOUT
DEVNULL = _subprocess.DEVNULL
CREATE_NO_WINDOW = getattr(_subprocess, 'CREATE_NO_WINDOW', 0)
SubprocessError = _subprocess.SubprocessError
TimeoutExpired = _subprocess.TimeoutExpired
CalledProcessError = _subprocess.CalledProcessError


class MediaPopen(_subprocess.Popen):
    def _execute_child(self, args, executable, preexec_fn, close_fds, pass_fds, cwd, env,
                       startupinfo, creationflags, shell, p2cread, p2cwrite, c2pread, c2pwrite,
                       errread, errwrite, *unused):
        if os.name != 'nt':
            return _subprocess.Popen._execute_child(self, args, executable, preexec_fn, close_fds, pass_fds, cwd, env,
                                                    startupinfo, creationflags, shell, p2cread, p2cwrite,
                                                    c2pread, c2pwrite, errread, errwrite, *unused)
        from services.windows_sandbox import create_media_process, SandboxUnavailable
        if shell or isinstance(args, (str, bytes)) or not args or not Path(args[0]).is_absolute():
            raise SandboxUnavailable()
        try:
            handle, pid, self._media_job = create_media_process(args, (p2cread, c2pwrite, errwrite), env)
        finally:
            self._close_pipe_fds(p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite)
        self._child_created = True
        self._handle = _subprocess.Handle(handle)
        self.pid = pid

    def _close_media_job(self):
        job = getattr(self, '_media_job', None)
        if job:
            job.Close()
            self._media_job = None

    def wait(self, *args, **kwargs):
        result = super().wait(*args, **kwargs)
        self._close_media_job()
        return result

    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self._close_media_job()


Popen = MediaPopen


def bounded_communicate(process, input=None, timeout=None, diagnostic_tail=False):
        buffers = [[], deque(maxlen=4) if diagnostic_tail else []]
        overflow = threading.Event()
        def read(stream, chunks, maximum):
            total = 0
            try:
                while True:
                    chunk = stream.read(65536)
                    if not chunk:break
                    total += len(chunk)
                    if total > maximum:
                        overflow.set()
                        process.kill()
                        break
                    chunks.append(chunk)
            except (OSError, ValueError):
                pass
        threads = []
        for stream, chunks, maximum in ((process.stdout, buffers[0], 2*1024**2), (process.stderr, buffers[1], 64*1024**2 if diagnostic_tail else 256*1024)):
            if stream:
                thread = threading.Thread(target=read, args=(stream, chunks, maximum), daemon=True)
                thread.start()
                threads.append(thread)
        try:
            if input is not None:
                process.stdin.write(input)
            if process.stdin:
                process.stdin.close()
            process.wait(timeout=timeout)
        except BaseException:
            process.kill()
            process.wait()
            raise
        finally:
            for thread in threads:thread.join(timeout=5)
        if overflow.is_set() or any(thread.is_alive() for thread in threads):
            raise SubprocessError('Media process output exceeded its safety budget.')
        empty = '' if process.text_mode else b''
        stdout = empty.join(buffers[0]) if process.stdout else None
        stderr = empty.join(buffers[1]) if process.stderr else None
        return stdout, stderr


def run(*popenargs, input=None, capture_output=False, timeout=None, check=False, **kwargs):
    if input is not None:
        kwargs['stdin'] = PIPE
    if capture_output:
        kwargs['stdout'] = kwargs['stderr'] = PIPE
    kwargs.setdefault('stdin', DEVNULL)
    with Popen(*popenargs, **kwargs) as process:
        stdout, stderr = bounded_communicate(process, input, timeout)
        if check and process.returncode:
            raise CalledProcessError(process.returncode, popenargs[0], stdout, stderr)
        return _subprocess.CompletedProcess(popenargs[0], process.returncode, stdout, stderr)


def install_yt_dlp_guard():
    """Guard yt-dlp's own subprocess class, without patching stdlib globally."""
    from yt_dlp.utils import Popen as YtdlpPopen
    if getattr(YtdlpPopen, '_vdp_media_guard', False):
        return
    original = YtdlpPopen._execute_child
    original_wait = YtdlpPopen.wait
    original_communicate = YtdlpPopen.communicate
    def guarded(self, args, *positional, **kwargs):
        if isinstance(args, (list, tuple)) and args and Path(args[0]).name.lower() in ('ffmpeg', 'ffmpeg.exe', 'ffprobe', 'ffprobe.exe'):
            self._vdp_guarded = True
            return MediaPopen._execute_child(self, args, *positional, **kwargs)
        return original(self, args, *positional, **kwargs)
    YtdlpPopen._execute_child = guarded
    def wait(self, *args, **kwargs):
        result = original_wait(self, *args, **kwargs)
        MediaPopen._close_media_job(self)
        return result
    YtdlpPopen.wait = wait
    def communicate(self, input=None, timeout=None):
        if getattr(self,'_vdp_guarded',False):
            return bounded_communicate(self,input,timeout,diagnostic_tail=True)
        return original_communicate(self,input=input,timeout=timeout)
    YtdlpPopen.communicate = communicate
    YtdlpPopen._vdp_media_guard = True
