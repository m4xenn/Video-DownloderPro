"""Recover the publication/history boundary without redownloading or trusting a path from the UI."""
import hashlib
from pathlib import Path
from services.job_lifecycle import file_signature
from services.output_validation import OutputValidationError
from services.media_gate import regular_file,check_media_header


class PublicationChanged(ValueError):
    code='publication_changed'
    def __init__(self):super().__init__('[publication_changed] Saved file changed or destination is occupied; files preserved.')


def validated_intent(job):
    intent=job.publication_intent
    if not isinstance(intent,dict) or intent.get('schema')!=1:return None
    try:
        source,target=Path(intent['source']),Path(intent['target'])
        if source.parent.resolve()!=Path(job.work_path).resolve() or target.parent.resolve()!=Path(job.path).resolve():raise ValueError()
        allowed={'.mp4','.mkv'} if job.options.get('format')=='video' else {'.mp3','.m4a','.wav','.opus'}
        if target.suffix.lower() not in allowed:raise ValueError()
    except (KeyError,TypeError,ValueError,OSError) as error:
        raise OutputValidationError('Invalid saved publication intent; files preserved.') from error
    return source,target


def has_saved_target(job):
    try:
        paths=validated_intent(job)
        return bool(paths and paths[1].is_file())
    except ValueError:return False


def _digest(path,cancelled):
    digest=hashlib.sha256()
    with regular_file(path).open('rb') as stream:
        while chunk:=stream.read(1024**2):
            if cancelled():
                from core.bandwidth import DownloadPaused
                raise DownloadPaused('DOWNLOAD_PAUSED')
            digest.update(chunk)
    return digest.digest()


def recover_saved_file(job,cancelled):
    paths=validated_intent(job)
    if not paths or not paths[1].exists():return None
    source,target=paths
    regular_file(target)
    expected=job.publication_intent.get('target_signature') or job.publication_intent.get('source_signature')
    actual=file_signature(target)
    if actual!=expected:
        # An interrupted cross-volume copy may have created the destination but
        # not committed its new file ID. Verify both complete byte streams.
        if not source.is_file() or source.stat().st_size!=target.stat().st_size or _digest(source,cancelled)!=_digest(target,cancelled):
            raise PublicationChanged()
    check_media_header(target)
    return str(target)
