"""Bounded live capture with FFmpeg reconnect and a graceful finish action."""
from collections import deque
from datetime import datetime, timezone
from functools import lru_cache
import math
from pathlib import Path
import queue
import subprocess
import threading
import time

from core.bandwidth import DownloadPaused


class LiveRecordingGapError(ValueError):
    code='recording_gap'
    def __init__(self):super().__init__('[recording_gap] Live segments are missing; recording stopped and any temporary data preserved.')


@lru_cache(maxsize=4)
def hls_retry_arguments(binary,modified):
    try:
        result=subprocess.run([binary,'-hide_banner','-h','demuxer=hls'],capture_output=True,timeout=5,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if b'-seg_max_retry ' in result.stdout+result.stderr:return ['-seg_max_retry','3']
    except (OSError,subprocess.SubprocessError):pass
    return []


@lru_cache(maxsize=4)
def reconnect_arguments(binary, modified):
    """Use newer retry bounds when the installed FFmpeg advertises them."""
    base=['-reconnect','1','-reconnect_streamed','1','-reconnect_delay_max','5','-rw_timeout','15000000']
    try:
        result=subprocess.run([binary,'-hide_banner','-h','protocol=http'],capture_output=True,timeout=5,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        help_text=(result.stdout+result.stderr).decode('utf-8','replace')
    except (OSError,subprocess.SubprocessError):return base
    for name,value in [('reconnect_on_network_error','1'),('reconnect_on_http_error','500,502,503,504'),
                       ('reconnect_max_retries','3'),('reconnect_delay_total_max','30')]:
        if '-'+name+' ' in help_text:base+=['-'+name,value]
    return base

def live_options(data, now=None):
    minutes=data.get('live_record_minutes',60)
    if isinstance(minutes,bool) or not isinstance(minutes,(int,float)) or not math.isfinite(minutes) or not 1 <= minutes <= 1440:
        raise ValueError('Recording duration must be 1–1440 minutes.')
    until=data.get('live_record_until')
    now=time.time() if now is None else now
    if until is not None:
        if isinstance(until,bool) or not isinstance(until,(int,float)) or not math.isfinite(until) or not now+5 <= until <= now+86400:
            raise ValueError('Recording stop time must be within the next 24 hours.')
    return {'live_record_minutes':minutes,'live_record_until':until}


def record_live(info, target, bin_dir, options, cancelled, stop_requested, progress=None):
    settings=live_options(options)
    limit=settings['live_record_minutes']*60
    if settings['live_record_until'] is not None:limit=min(limit,settings['live_record_until']-time.time())
    location=Path(bin_dir)
    ffmpeg=location if location.name.lower().startswith('ffmpeg.') else location/'ffmpeg.exe'
    if not ffmpeg.is_file():raise ValueError('FFmpeg is required for live recording.')
    if options.get('embed_subs'):raise ValueError('Live subtitle recording is not supported; disable subtitles.')
    if options.get('format','video')!='video':raise ValueError('Live recording currently requires MP4 video output.')
    target=Path(target);temporary=target.with_suffix('.live.mkv')
    if target.exists() or temporary.exists():raise ValueError('Live recording target already exists; files preserved.')
    formats=info.get('requested_formats') or [info]
    if not 1 <= len(formats) <= 2:raise ValueError('Unsupported live source layout.')
    args=[str(ffmpeg),'-hide_banner','-loglevel','warning','-nostats','-progress','pipe:1']
    from services.media_discovery import public_url
    for fmt in formats:
        url=fmt.get('url')
        if not public_url(url,resolve=True):raise ValueError('Non-public live source.')
        headers={k:v for k,v in (fmt.get('http_headers') or info.get('http_headers') or {}).items() if k in ('User-Agent','Referer','Origin')}
        if any('\r' in str(v) or '\n' in str(v) for v in headers.values()):raise ValueError('Invalid live source headers.')
        args+=reconnect_arguments(str(ffmpeg),ffmpeg.stat().st_mtime_ns)
        if 'm3u8' in fmt.get('protocol','') or '.m3u8' in url.split('?',1)[0]:
            args+=hls_retry_arguments(str(ffmpeg),ffmpeg.stat().st_mtime_ns)
        if headers:args+=['-headers',''.join(f'{k}: {v}\r\n' for k,v in headers.items())]
        args+=['-i',url]
    video=next((i for i,f in enumerate(formats) if f.get('vcodec')!='none'),None)
    audio=next((i for i,f in enumerate(formats) if f.get('acodec') not in (None,'none')),None)
    if video is None:raise ValueError('Live source has no video stream.')
    def stream_spec(index,kind):
        fmt=formats[index]
        number=fmt.get('manifest_stream_number')
        if fmt.get('protocol')=='http_dash_segments' and isinstance(number,int) and number>=0:return f'{index}:{number}'
        return f'{index}:{kind}:0'
    args+=['-map',stream_spec(video,'v')]
    if audio is not None:args+=['-map',stream_spec(audio,'a')]
    else:args+=['-map',f'{video}:a:0?']
    args+=['-t',str(limit),'-c','copy','-flush_packets','1','-cluster_time_limit','1000','-f','matroska',str(temporary)]
    messages=queue.Queue(maxsize=256);errors=deque(maxlen=16);gap_event=threading.Event()
    process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                             encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    def read_output():
        for line in process.stdout:
            try:messages.put_nowait(line.strip())
            except queue.Full:pass
    def read_errors():
        for line in process.stderr:
            errors.append(line[:1024])
            if 'segment' in line.lower() and 'skipping' in line.lower():gap_event.set()
    workers=[threading.Thread(target=read_output,daemon=True),threading.Thread(target=read_errors,daemon=True)]
    for worker in workers:worker.start()
    start=time.monotonic();finishing=None;paused=False;forced_stop=False;gap=False;elapsed=0.;size=0
    try:
        while process.poll() is None:
            if cancelled():paused=True
            if gap_event.is_set():gap=True
            deadline=settings['live_record_until']
            if finishing is None and (gap or paused or stop_requested() or time.monotonic()-start>=limit or (deadline is not None and time.time()>=deadline)):
                finishing=time.monotonic()
                try:process.stdin.write('q\n');process.stdin.flush()
                except (OSError,BrokenPipeError):pass
            if finishing is not None and time.monotonic()-finishing>5:
                # A blocked HLS read may not process q. MKV clusters are flushed
                # during capture, so stop the reader and validate/remux locally.
                forced_stop=True;process.kill();break
            try:line=messages.get(timeout=.1)
            except queue.Empty:continue
            key,_,value=line.partition('=')
            if key=='out_time_us':
                try:elapsed=max(0,float(value)/1_000_000)
                except ValueError:pass
            elif key=='total_size':
                try:size=int(value)
                except ValueError:pass
            elif key=='progress' and progress:
                progress({'status':'downloading','downloaded_bytes':size,'recorded_seconds':elapsed,
                          'recording_limit':limit,'info_dict':info,'_speed_str':f'{int(elapsed)} s'})
        process.wait(timeout=5)
        for worker in workers:worker.join(timeout=2)
        if paused:raise DownloadPaused('DOWNLOAD_PAUSED')
        if gap or gap_event.is_set():raise LiveRecordingGapError()
        if (process.returncode and not forced_stop) or not temporary.is_file() or temporary.stat().st_size<1024:
            code='403' if any('403' in line for line in errors) else '429' if any('429' in line for line in errors) else 'connection'
            raise ValueError(f'Live recording {code} failure; temporary recording preserved.')
        if progress:progress({'status':'finished','info_dict':info})
        # Keep the recoverable MKV until MP4 validation and atomic publication succeed.
        staging=target.with_suffix('.live-final.mp4')
        result=subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-i',str(temporary),'-c','copy',
                               '-movflags','+faststart',str(staging)],capture_output=True,timeout=120,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise ValueError('Live recording finalization failed; temporary recording preserved.')
        from services.output_validation import validate_output
        checked=validate_output(staging,bin_dir,True,expect_audio=audio is not None,include_duration=True)
        elapsed=checked.get('duration') or elapsed
        staging.rename(target)
        temporary.unlink()
        return {'recorded_seconds':elapsed,'ended_utc':datetime.now(timezone.utc).isoformat()}
    finally:
        if process.poll() is None:process.kill()
        process.wait(timeout=5)
        for worker in workers:worker.join(timeout=2)
        for pipe in (process.stdin,process.stdout,process.stderr):
            if pipe:pipe.close()
