"""Retry only the final rename of an already completed yt-dlp merge.

Scoped to this YoutubeDL instance. No global filesystem patches, network retries,
or assumptions that an arbitrary temporary file is a finished download.
"""
import errno
import os
from pathlib import Path
import time

from yt_dlp.postprocessor.ffmpeg import FFmpegMergerPP
from yt_dlp.utils import prepend_extension

from services.output_validation import validate_output


def finish_locked_merge(error, info, location, cancelled, progress=None, timeout=8):
    target = Path(info['filepath']).resolve()
    temporary = Path(prepend_extension(str(target), 'temp'))
    if not isinstance(error, PermissionError) or error.errno not in (errno.EACCES, errno.EPERM):
        raise error
    if not error.filename or not error.filename2 or Path(error.filename).resolve() != temporary or Path(error.filename2).resolve() != target:
        raise error
    if target.exists() or not temporary.is_file() or not info.get('__files_to_merge') or not all(Path(p).is_file() for p in info['__files_to_merge']):
        raise error
    expected = info.get('requested_formats') or []
    streams = validate_output(temporary, location, expect_video=True)
    if any(f.get('acodec') not in (None, 'none') for f in expected) and not streams['audio']:
        raise error
    if progress:
        progress('postprocess')
    deadline = time.monotonic() + timeout
    while True:
        if cancelled():
            from core.bandwidth import DownloadPaused
            raise DownloadPaused('DOWNLOAD_PAUSED')
        if target.exists():
            raise error
        try:
            os.rename(temporary, target)
            return info['__files_to_merge'], info
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.1)


def attach_merge_recovery(ydl, cancelled, progress=None):
    original_run_pp = ydl.run_pp

    def run_pp(pp, info):
        if type(pp) is not FFmpegMergerPP:
            return original_run_pp(pp, info)
        original_run = pp.run

        def run(working):
            try:
                return original_run(working)
            except PermissionError as error:
                result = finish_locked_merge(error, working, ydl.params.get('ffmpeg_location') or '', cancelled, progress)
                # Original run emitted started, but rename failed before finished.
                pp._hook_progress({'status': 'finished'}, pp._copy_infodict(working))
                return result
        pp.run = run
        try:
            return original_run_pp(pp, info)
        finally:
            pp.run = original_run
    ydl.run_pp = run_pp
