"""Verify expected streams in a completed embedded file before recording success."""
import json,struct,math
from contextlib import contextmanager
from contextvars import ContextVar
import os
from services import media_process as subprocess
from pathlib import Path
class OutputValidationError(ValueError):
 code='invalid_media'
 def __init__(self,message):super().__init__('[invalid_media] '+message)


_session=ContextVar('media_validation_session',default=None)


@contextmanager
def validation_session():
 """Job-scoped reuse only while Windows prevents writes to validated bytes."""
 if _session.get() is not None:
  yield
  return
 entries={};token=_session.set(entries)
 try:yield
 finally:
  _session.reset(token)
  for _,handle in entries.values():handle.Close()


def _fingerprint(path):
 details=Path(path).stat()
 if not details.st_ino or details.st_nlink!=1 or getattr(details,'st_file_attributes',0)&0x400:return None
 return details.st_dev,details.st_ino,details.st_size,details.st_mtime_ns


def _read_lease(path):
 if os.name!='nt':return None
 import win32file,pywintypes
 try:
  # Deny new data writes, but permit atomic rename/delete. The open file ID
  # cannot be recycled while held; aliases cannot bypass Windows share checks.
  return win32file.CreateFile(str(Path(path).absolute()),0x80000000,1|4,None,3,0,None)
 except (OSError,pywintypes.error):return None

def validate_mp4_extent(path):
 """Check box extents without scanning media; duration alone can describe a truncated VOD."""
 path=Path(path)
 if not path.is_file():return
 with path.open('rb') as media:
  total=path.stat().st_size
  first=media.read(8)
  if len(first)!=8 or first[4:]!=b'ftyp':return
  offset=0
  for _ in range(4096):
   if offset==total:return
   media.seek(offset)
   header=media.read(8)
   if len(header)!=8:raise OutputValidationError('Incomplete MP4 box header; files preserved.')
   size,kind=struct.unpack('>I4s',header);minimum=8
   if size==1:
    extended=media.read(8)
    if len(extended)!=8:raise OutputValidationError('Incomplete extended MP4 header; files preserved.')
    size=struct.unpack('>Q',extended)[0];minimum=16
   elif size==0:size=total-offset
   if size<minimum or offset+size>total:
    raise OutputValidationError('Incomplete MP4 source: declared media exceeds available bytes. A preview may expose only part of the recording; files preserved.')
   offset+=size
  raise OutputValidationError('MP4 box count exceeds validation budget; files preserved.')


def validate_output(path,ffmpeg_location,expect_video,expected_duration=None,expect_audio=None,include_duration=False,reuse_validation=False):
 entries=_session.get() if reuse_validation else None
 if entries is None:
  return _validate_output(path,ffmpeg_location,expect_video,expected_duration,expect_audio,include_duration)
 expected=expected_duration if isinstance(expected_duration,(int,float)) and not isinstance(expected_duration,bool) and math.isfinite(expected_duration) and expected_duration>0 else None
 policy=(str(Path(ffmpeg_location or '').resolve()),bool(expect_video),bool(expect_audio),expected)
 before=_fingerprint(path)
 key=(before,policy)
 if before is not None and key in entries:
  result=entries[key][0]
  return dict(result) if include_duration else {k:result[k] for k in ('video','audio')}
 handle=_read_lease(path)
 try:
  before=_fingerprint(path)
  result=_validate_output(path,ffmpeg_location,expect_video,expected_duration,expect_audio,True)
  after=_fingerprint(path)
  if before!=after:raise OutputValidationError('Media changed during validation; files preserved.')
  if handle and after is not None:
   if len(entries)>=8:
    _,old=entries.pop(next(iter(entries)));old.Close()
   entries[(after,policy)]=(dict(result),handle);handle=None
  return result if include_duration else {k:result[k] for k in ('video','audio')}
 finally:
  if handle:handle.Close()


def _validate_output(path,ffmpeg_location,expect_video,expected_duration=None,expect_audio=None,include_duration=False):
 validate_mp4_extent(path)
 location=Path(ffmpeg_location or '')
 folder=location.parent if location.name.lower().startswith('ffmpeg.') else location
 probe=folder/'ffprobe.exe' if (folder/'ffprobe.exe').is_file() else folder/'ffprobe'
 if not probe.is_file():raise OutputValidationError('Downloaded media cannot be validated: FFprobe component missing.')
 try:
  result=subprocess.run([str(probe.absolute()),'-v','error','-protocol_whitelist','file,pipe','-show_entries','format=duration:stream=codec_type,codec_name,width,height:stream_disposition=attached_pic','-of','json',str(Path(path).absolute())],capture_output=True,timeout=15,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  if len(result.stdout)>65536:raise ValueError()
  details=json.loads(result.stdout);streams=details.get('streams',[])
 except (subprocess.SubprocessError,OSError,ValueError) as error:raise OutputValidationError('Downloaded file does not contain readable media streams; files preserved.') from error
 expected='video' if expect_video else 'audio'
 streams=[s for s in streams if isinstance(s,dict)]
 video=any(s.get('codec_type')=='video' and not s.get('disposition',{}).get('attached_pic') for s in streams)
 audio=any(s.get('codec_type')=='audio' for s in streams)
 if not (video if expect_video else audio):raise OutputValidationError('Expected '+expected+' stream missing from downloaded file; files preserved.')
 if expect_audio and not audio:raise OutputValidationError('Expected audio stream missing; files preserved.')
 try:duration=float((details.get('format') or {}).get('duration') or 0)
 except (ValueError,TypeError):duration=0
 if isinstance(expected_duration,(int,float)) and not isinstance(expected_duration,bool) and math.isfinite(expected_duration) and expected_duration>0:
  if not math.isfinite(duration) or duration<=0 or abs(duration-expected_duration)>max(2,expected_duration*.005):
   raise OutputValidationError('Output duration does not match the source; files preserved.')
 if math.isfinite(duration) and duration>3:
  try:
   tail=subprocess.run([str(probe.absolute()),'-v','error','-protocol_whitelist','file,pipe','-read_intervals',f'{max(0,duration-3):.3f}%+3',
      '-select_streams','v:0' if expect_video else 'a:0','-show_entries','packet=pts_time','-of','json',str(path)],
      capture_output=True,timeout=15,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   if len(tail.stdout)>262144 or not json.loads(tail.stdout).get('packets') or tail.stderr.strip():raise ValueError()
  except (subprocess.SubprocessError,OSError,ValueError) as error:raise OutputValidationError('End of output is not readable; files preserved.') from error
  ffmpeg=folder/'ffmpeg.exe' if (folder/'ffmpeg.exe').is_file() else folder/'ffmpeg'
  if ffmpeg.is_file():
   try:
    decoded=subprocess.run([str(ffmpeg.absolute()),'-nostdin','-hide_banner','-v','error','-xerror','-protocol_whitelist','file,pipe','-ss',f'{max(0,duration-2):.3f}',
      '-i',str(path),'-t','2','-map','0:v:0' if expect_video else '0:a:0','-map','0:a:0?',
      '-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=20,check=True,
      creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if decoded.stderr.strip():raise ValueError()
   except (subprocess.SubprocessError,OSError,ValueError) as error:raise OutputValidationError('End of output could not be decoded; files preserved.') from error
 result={'video':video,'audio':audio}
 if include_duration:result['duration']=duration
 return result
