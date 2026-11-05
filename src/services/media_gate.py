"""Private, resumable staging and a no-overwrite publication boundary."""
import os
from pathlib import Path
import re
import stat
import uuid
import errno
import shutil
import time

from services.output_validation import OutputValidationError


class SecurityReviewError(ValueError):
    code = 'security_review'
    def __init__(self):
        super().__init__('[security_review] File withheld; the security scan needs attention.')


def regular_file(path):
    path = Path(path)
    details = path.lstat()
    if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1 or getattr(details, 'st_file_attributes', 0) & 0x400:
        raise OutputValidationError('Linked or redirected media file rejected.')
    return path


def check_media_header(path):
    """Reject executables, pages and playlists before invoking a media parser."""
    path = regular_file(path)
    with path.open('rb') as stream:
        header = stream.read(4096)
    suffix = path.suffix.lower()
    iso = len(header) >= 12 and header[4:8] == b'ftyp'
    matches = {
        '.mp4': iso, '.m4a': iso,
        '.webm': header.startswith(b'\x1aE\xdf\xa3'),
        '.mkv': header.startswith(b'\x1aE\xdf\xa3'),
        '.wav': header.startswith((b'RIFF', b'RF64')) and header[8:12] == b'WAVE',
        '.opus': header.startswith(b'OggS') and b'OpusHead' in header,
        '.mp3': header.startswith(b'ID3') or (len(header) >= 2 and header[0] == 255 and header[1] & 0xe0 == 0xe0),
    }
    if not matches.get(suffix, False):
        raise OutputValidationError('File contents do not match the selected media type; file withheld.')
    return path


def _plain_directory(path):
    if path.is_symlink() or (path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400):
        raise OutputValidationError('Redirected download workspace rejected.')
    path.mkdir(exist_ok=True)


def staging_directory(destination, identity, existing=''):
    if not re.fullmatch('[a-f0-9]{32}', identity):
        raise OutputValidationError('Invalid workspace identity.')
    roots = [Path(destination).absolute() / '.vdp-work']
    if os.name == 'nt':
        # FAT/exFAT and some network shares cannot represent private ACLs or
        # integrity labels. Keep that destination usable via a local workspace.
        roots.append(Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData/Local') / 'YoutubePro/media-work')
    if existing:
        matches = [root for root in roots if (root / identity).resolve() == Path(existing).resolve()]
        if not matches:raise OutputValidationError('Invalid saved workspace.')
        roots = matches
    for index, root in enumerate(roots):
        try:
            root.parent.mkdir(parents=True, exist_ok=True)
            _plain_directory(root)
            path = root / identity
            _plain_directory(path)
            if os.name == 'nt':
                import win32api, win32con, pywintypes
                from services.windows_sandbox import protect_workspace
                protect_workspace(path)
                try:win32api.SetFileAttributes(str(root), win32api.GetFileAttributes(str(root)) | win32con.FILE_ATTRIBUTE_HIDDEN)
                except (OSError, pywintypes.error):pass
            else:
                path.chmod(0o700)
            for orphan in path.glob('.vdp-publish-*.tmp'):
                if re.fullmatch(r'\.vdp-publish-[a-f0-9]{32}\.tmp',orphan.name) and not orphan.is_dir():
                    orphan.unlink()
            return path
        except OutputValidationError:
            raise
        except Exception:
            if index == len(roots)-1:
                from services.windows_sandbox import SandboxUnavailable
                raise SandboxUnavailable()


def contained_file(path, directory):
    path = regular_file(path)
    directory = Path(directory)
    if path.parent.resolve() != directory.resolve():
        raise OutputValidationError('Media escaped its private download workspace.')
    _plain_directory(directory)
    return path


def withhold(path, directory):
    """Retain for inspection, with a non-executable extension and no open action."""
    path = contained_file(path, directory)
    quarantine = Path(directory) / 'quarantine'
    _plain_directory(quarantine)
    os.rename(path, quarantine / (uuid.uuid4().hex + '.blocked'))


def migrate_checkpoint(template, directory):
    """Same-volume renames; deterministic paths survive an interrupted move."""
    ending = '.%(ext)s'
    if not template.endswith(ending):
        raise OutputValidationError('Invalid saved output template.')
    base = Path(template[:-len(ending)].replace('%%', '%'))
    if base.parent.resolve() != Path(directory).resolve() and base.parent.is_dir():
        files = [p for p in base.parent.iterdir() if p.name.startswith(base.name + '.')]
        if len(files) > 1000:
            raise OutputValidationError('Saved output has too many companion files.')
        for path in files:
            regular_file(path)
            target = Path(directory) / path.name
            if target.exists():
                raise OutputValidationError('Conflicting recovery files preserved.')
            try:os.rename(path, target)
            except OSError as error:
                if error.errno != errno.EXDEV and getattr(error,'winerror',None) != 17:raise
                _copy_across_volume(path,target)
    return str(Path(directory) / base.name).replace('%', '%%') + ending


def _copy_across_volume(path, target, after_create=None):
    temporary = target.parent / ('.vdp-publish-' + uuid.uuid4().hex + '.tmp')
    try:
        before = path.stat()
        if shutil.disk_usage(target.parent).free < before.st_size + 32*1024**2:
            raise OSError(errno.ENOSPC,'No space left for safe media processing; original preserved.')
        guard = MediaDiskGuard(target.parent)
        with path.open('rb') as source, temporary.open('xb') as output:
            while True:
                chunk = source.read(1024**2)
                if not chunk:break
                guard.check()
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        after = path.stat()
        if (before.st_size,before.st_mtime_ns,before.st_ino) != (after.st_size,after.st_mtime_ns,after.st_ino) or temporary.stat().st_size != after.st_size:
            raise OutputValidationError('Media changed during publication; original preserved.')
        if os.name == 'nt':os.rename(temporary,target)
        else:
            os.link(temporary,target,follow_symlinks=False)
            temporary.unlink()
        if after_create:after_create(str(path),str(target))
        path.unlink()
    finally:
        if temporary.exists():temporary.unlink()


def publish(path, destination, directory, before_publish=None, after_create=None):
    from core.output_paths import reserve_output
    path = contained_file(path, directory)
    if os.name == 'nt':
        from services.windows_sandbox import restore_file_integrity
        restore_file_integrity(path)
    lease = reserve_output(str(Path(destination) / path.stem))
    try:
        target = Path(lease.base + path.suffix)
        if before_publish:before_publish(str(path),str(target))
        # Windows rename is atomic and refuses overwrite. POSIX rename replaces
        # files, so use a same-volume exclusive hard link followed by unlink.
        try:
            if os.name == 'nt':
                os.rename(path, target)
            else:
                os.link(path, target, follow_symlinks=False)
                path.unlink()
            if after_create:after_create(str(path),str(target))
        except OSError as error:
            if error.errno != errno.EXDEV and getattr(error, 'winerror', None) != 17:raise
            _copy_across_volume(path,target,after_create)
        from services.file_security import mark_internet_file
        mark_internet_file(target)
        try:Path(directory).rmdir()
        except OSError:pass  # Partial companions and quarantined files survive.
        return str(target)
    finally:
        lease.release()


class MediaDiskGuard:
    """A tiny free-space reserve, without a file-size or recording-length cap."""
    def __init__(self, directory, clock=time.monotonic):
        self.directory, self.clock, self.next_check = directory, clock, 0
    def check(self):
        now = self.clock()
        if now < self.next_check:return
        self.next_check = now + 2
        if shutil.disk_usage(self.directory).free < 32 * 1024**2:
            raise OSError(errno.ENOSPC, 'No space left for safe media processing; partial files preserved.')

