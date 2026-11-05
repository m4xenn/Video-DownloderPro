"""Bounded live capture with FFmpeg reconnect and a graceful finish action."""
from collections import deque
from datetime import datetime, timezone
from functools import lru_cache
import math
from pathlib import Path
import queue
from services import media_process as subprocess
import threading
import time

from core.bandwidth import DownloadPaused


class LiveRecordingGapError(ValueError):
    code='recording_gap'
    def __init__(self):super().__init__('[recording_gap] Live segments are missing; recording stopped and any temporary data preserved.')


class LiveTelemetry:
    """Rolling output rate and media-time pace, including intervals with no data."""
    def __init__(self, started):
        self.samples=deque([(started,0,0.)])

    def sample(self, now, size, elapsed):
        self.samples.append((now,size,elapsed))
        while len(self.samples)>2 and self.samples[1][0]<now-5:
            self.samples.popleft()
        first=self.samples[0];duration=max(.1,now-first[0])
        return (max(0,size-first[1])/duration,
                max(0,elapsed-first[2])/duration if duration>=1 else 0.)


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


def record_live(info, target, bin_dir, options, cancelled, stop_requested, progress=None, *, dvr_router=None):
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
    contexts=[{k:v for k,v in (fmt.get('http_headers') or info.get('http_headers') or {}).items()
               if k in ('User-Agent','Referer','Origin')} for fmt in formats]
    if any('\r' in str(v) or '\n' in str(v) for headers in contexts for v in headers.values()):
        raise ValueError('Invalid live source headers.')
    from services.live_catchup import plan_catchup
    catchup=dvr_router.plan if dvr_router else plan_catchup(formats,contexts,cancelled)
    if cancelled():raise DownloadPaused('DOWNLOAD_PAUSED')
    args=[str(ffmpeg),'-hide_banner','-loglevel','warning','-nostats','-progress','pipe:1']
    from services.media_discovery import public_url
    for input_index,fmt in enumerate(formats):
        url=fmt.get('url')
        if not public_url(url,resolve=True):raise ValueError('Non-public live source.')
        headers={k:v for k,v in (fmt.get('http_headers') or info.get('http_headers') or {}).items() if k in ('User-Agent','Referer','Origin')}
        if any('\r' in str(v) or '\n' in str(v) for v in headers.values()):raise ValueError('Invalid live source headers.')
        args+=reconnect_arguments(str(ffmpeg),ffmpeg.stat().st_mtime_ns)
        if dvr_router or 'm3u8' in fmt.get('protocol','') or '.m3u8' in url.split('?',1)[0]:
            args+=hls_retry_arguments(str(ffmpeg),ffmpeg.stat().st_mtime_ns)
            args+=['-live_start_index',str(catchup.indices[input_index]),'-prefer_x_start','0']
        # DVR's upstream requests already carry these headers. Sending Origin
        # to the native-only loopback view would trip its browser-origin guard.
        if headers and not dvr_router:args+=['-headers',''.join(f'{k}: {v}\r\n' for k,v in headers.items())]
        args+=['-protocol_whitelist','http,https,tcp,tls,crypto,data','-i',url]
    video=next((i for i,f in enumerate(formats) if f.get('vcodec') not in (None,'none')),None)
    if video is None:
        video=next((i for i,f in enumerate(formats) if f.get('vcodec')!='none'),None)
    audio=next((i for i,f in enumerate(formats) if f.get('acodec') not in (None,'none')),None)
    if audio is None:
        # HLS external AUDIO renditions (notably YouTube live) may omit CODECS.
        # vcodec=none still identifies the selected audio-only input. None means
        # unknown codec, not absent audio; require and validate that track.
        audio=next((i for i,f in enumerate(formats)
                    if f.get('vcodec')=='none' and f.get('acodec')!='none'),None)
    if video is None:raise ValueError('Live source has no video stream.')
    if audio is None and formats[video].get('acodec') is None:
        audio=video  # Unknown multiplexed audio must not silently disappear.
    def stream_spec(index,kind):
        fmt=formats[index]
        number=fmt.get('manifest_stream_number')
        if fmt.get('protocol')=='http_dash_segments' and isinstance(number,int) and number>=0:return f'{index}:{number}'
        return f'{index}:{kind}:0'
    args+=['-map',stream_spec(video,'v')]
    if audio is not None:args+=['-map',stream_spec(audio,'a')]
    else:args+=['-map',f'{video}:a:0?']
    args+=['-t',str(limit),'-c','copy','-flush_packets','1','-cluster_time_limit','1000','-f','matroska',str(temporary)]
    if progress and catchup.seconds>catchup.threshold:
        progress({'status':'downloading','downloaded_bytes':0,'recorded_seconds':0,
                  'recording_limit':limit,'recording_speed_bps':0,'recording_phase':'catchup',
                  'catchup_remaining_seconds':catchup.seconds,'catchup_available_seconds':catchup.seconds,
                  'catchup_from_start':bool(dvr_router),
                  'info_dict':info,'_speed_str':'0.00 MB/s'})
    messages=queue.Queue(maxsize=256);errors=deque(maxlen=16);gap_event=threading.Event()
    from services.live_catchup import HLSHistoryProxy
    router=dvr_router or (HLSHistoryProxy(catchup,formats,contexts) if catchup.windows else None)
    gateway=None
    try:
        positions=[i+1 for i,value in enumerate(args) if value=='-i']
        inputs=[args[position] for position in positions]
        if router:
            inputs=router.start()
        if not dvr_router:
            from services.live_network import LiveNetwork
            gateway=LiveNetwork(contexts,owned=inputs if router else ())
            inputs=gateway.start(inputs)
        for position,url in zip(positions,inputs):args[position]=url
        process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                 encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except BaseException:
        if gateway:gateway.close()
        if router:router.close()
        raise
    def read_output():
        for line in iter(lambda:process.stdout.readline(8192), ''):
            try:messages.put_nowait(line.strip())
            except queue.Full:pass
    def read_errors():
        for line in iter(lambda:process.stderr.readline(4096), ''):
            errors.append(line[:1024])
            if 'segment' in line.lower() and 'skipping' in line.lower():gap_event.set()
    workers=[threading.Thread(target=read_output,daemon=True),threading.Thread(target=read_errors,daemon=True)]
    for worker in workers:worker.start()
    start=time.monotonic();finishing=None;paused=False;forced_stop=False;gap=False;elapsed=0.;size=0
    telemetry=LiveTelemetry(start);last_progress=start
    def emit_progress(now):
        nonlocal last_progress
        last_progress=now
        speed,pace=telemetry.sample(now,size,elapsed)
        lag=max(0,catchup.seconds+(now-catchup.observed_at)-elapsed) if catchup.seconds else 0
        if dvr_router:
            lag=dvr_router.remaining_seconds(now)
        if progress:
            progress({'status':'downloading','downloaded_bytes':size,'recorded_seconds':elapsed,
                      'recording_limit':limit,'recording_speed_bps':speed,'recording_pace':pace,
                      'recording_phase':'catchup' if lag>catchup.threshold else 'live',
                      'catchup_remaining_seconds':lag,'catchup_available_seconds':catchup.seconds,
                      'catchup_from_start':bool(dvr_router),
                      'info_dict':info,'_speed_str':f'{speed/1_000_000:.2f} MB/s'})
    try:
        while process.poll() is None:
            if cancelled():paused=True
            if gap_event.is_set():gap=True
            if getattr(router,'error',False):gap=True
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
            except queue.Empty:
                # FFmpeg can be blocked waiting for a segment. Refresh telemetry
                # rather than leaving its previous fast/slow rate frozen onscreen.
                now=time.monotonic()
                if finishing is None and now-last_progress>=1:emit_progress(now)
                continue
            key,_,value=line.partition('=')
            if key=='out_time_us':
                try:elapsed=max(0,float(value)/1_000_000)
                except ValueError:pass
            elif key=='total_size':
                try:size=int(value)
                except ValueError:pass
            elif key=='progress' and progress:
                emit_progress(time.monotonic())
        process.wait(timeout=5)
        for worker in workers:worker.join(timeout=2)
        if paused:raise DownloadPaused('DOWNLOAD_PAUSED')
        if getattr(router,'error',False):
            from services.youtube_dvr import DVRFragmentError
            raise DVRFragmentError()
        if gap or gap_event.is_set():raise LiveRecordingGapError()
        if gateway and gateway.unsafe:
            from services.security_policy import UnsafeLink
            raise UnsafeLink()
        if (process.returncode and not forced_stop) or not temporary.is_file() or temporary.stat().st_size<1024:
            code='403' if any('403' in line for line in errors) else '429' if any('429' in line for line in errors) else 'connection'
            error=ValueError(f'Live recording {code} failure; temporary recording preserved.')
            error.recording_diagnostics={'stop_reason':'process_failure','returncode':process.returncode,
                'recorded_seconds':elapsed,'wall_seconds':time.monotonic()-start,'stderr_tail':list(errors)}
            raise error
        # FFmpeg may return zero after giving up on a stalled live playlist.
        # A clean process exit alone does not establish that the broadcast ended.
        stop_reason='requested' if finishing is not None else 'duration' if elapsed>=limit-1 else 'source_end'
        if finishing is None and elapsed<limit-1:
            from services.live_completion import confirmed_source_end
            if not confirmed_source_end(formats,contexts,router):
                error=LiveRecordingGapError()
                error.recording_diagnostics={'stop_reason':'unconfirmed_eof','returncode':process.returncode,
                    'recorded_seconds':elapsed,'wall_seconds':time.monotonic()-start,'stderr_tail':list(errors)}
                raise error
        if progress:progress({'status':'finished','info_dict':info})
        # Keep the recoverable MKV until MP4 validation and atomic publication succeed.
        staging=target.with_suffix('.live-final.mp4')
        result=subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-i',str(temporary),'-c','copy',
                               '-movflags','+faststart',str(staging)],capture_output=True,timeout=120,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise ValueError('Live recording finalization failed; temporary recording preserved.')
        from services.output_validation import validate_output
        checked=validate_output(staging,bin_dir,True,expect_audio=audio is not None,include_duration=True,reuse_validation=True)
        elapsed=checked.get('duration') or elapsed
        staging.rename(target)
        temporary.unlink()
        return {'recorded_seconds':elapsed,'ended_utc':datetime.now(timezone.utc).isoformat(),
                'stop_reason':stop_reason,'stderr_tail':list(errors)}
    finally:
        if process.poll() is None:process.kill()
        process.wait(timeout=5)
        for worker in workers:worker.join(timeout=2)
        for pipe in (process.stdin,process.stdout,process.stderr):
            if pipe:pipe.close()
        if gateway:gateway.close()
        if router:router.close()
