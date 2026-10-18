"""Reserve an output stem across formats, including yt-dlp intermediate files."""
import os
from pathlib import Path
import threading

_lock = threading.RLock()
_active = set()


class OutputReservation:
    def __init__(self, base, key):
        self.base, self.key = base, key

    def release(self):
        with _lock:
            _active.discard(self.key)


def reserve_output(base, resume=False):
    """A new audio conversion must never reuse an existing video's stem.

    yt-dlp downloads an intermediate MP4/WebM before converting to audio and
    may delete that intermediate. Reserving only the final extension is unsafe.
    The in-process lease also prevents two workers selecting the same free stem.
    """
    path = Path(base)
    with _lock:
        names = [os.path.normcase(p.name) for p in path.parent.iterdir()] if path.parent.exists() else []
        index = 0
        while True:
            candidate = str(path) if index == 0 else str(path) + f' ({index})'
            key = os.path.normcase(os.path.abspath(candidate))
            stem = os.path.normcase(Path(candidate).name)
            active = key in _active
            if resume:
                if active:
                    raise ValueError('This output is already being used by another download.')
                break
            if not active and not any(name == stem or name.startswith(stem + '.') for name in names):
                break
            index += 1
        _active.add(key)
        return OutputReservation(candidate, key)
