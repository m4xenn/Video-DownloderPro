"""Durable live parts and explicitly discontinuous, stream-copy recovery exports."""
import hashlib,json,math,os,shutil,uuid,time,threading
from collections import deque
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
from services import media_process as process
from services.media_gate import regular_file,check_media_header,publish,staging_directory
from services.output_validation import validate_output
from services.job_lifecycle import file_signature


class RecordingPartError(ValueError):
    def __init__(self,code='recording_part_missing'):
        self.code=code;super().__init__('['+code+'] Recording parts require attention; original files preserved.')


def utc():return datetime.now(timezone.utc).isoformat()


def part_event(job,event,target,info=None,error_code=''):
    """Called by the owning worker before capture and on every terminal path."""
    target=Path(target)
    if event=='started':
        if len(job.recording_parts)>=256:raise RecordingPartError('recording_part_limit')
        from services.source_recovery import source_checkpoint
        job.recording_parts.append({'id':uuid.uuid4().hex,'state':'recording','workspace':str(target.parent),
            'file':target.with_suffix('.live.mkv').name,'started_utc':utc(),'seconds':0,'bytes':0,
            'continuity':'unknown','source_signature':source_checkpoint(info or {})})
    elif job.recording_parts:
        part=job.recording_parts[-1]
        part['stopped_utc']=utc();part['error_code']=error_code
        part['state']='captured' if event=='captured' else 'interrupted'
        if event=='captured':
            part['file']=target.name
            part['seconds']=(info or {}).get('duration') or part.get('seconds',0)
        path=Path(part['workspace'])/part['file']
        if path.is_file():part['bytes']=path.stat().st_size
    # Contains only the originally submitted link/selection and file IDs, never
    # separately extracted stream URLs, cookies or request headers.
    save_manifest(job,target.parent)


def save_manifest(job,directory):
    payload={'schema':1,'job_id':job.id,'source_page':job.url,'title':job.title,
             'options':job.options,'destination':job.path,'parts':job.recording_parts}
    directory=Path(directory)
    if directory.is_dir():
        pending=directory/'recording-session.tmp'
        pending.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        os.replace(pending,directory/'recording-session.json')


def recoverable_parts(job):
    return [p for p in job.recording_parts if isinstance(p,dict) and p.get('state') in ('recording','interrupted','captured') and isinstance(p.get('bytes'),(int,float)) and p['bytes']>0]


def part_path(job,part):
    workspace=Path(part['workspace'])
    if workspace.name!=job.id or workspace.parent.name not in ('.vdp-work','media-work') or workspace.is_symlink() or getattr(workspace.lstat(),'st_file_attributes',0)&0x400:
        raise RecordingPartError()
    name=part.get('file')
    if not isinstance(name,str) or Path(name).name!=name or Path(name).suffix not in ('.mkv','.mp4'):raise RecordingPartError()
    path=regular_file(workspace/name)
    check_media_header(path)
    return path


def stream_signature(path,bin_dir):
    probe=Path(bin_dir)/'ffprobe.exe'
    fields='codec_type,codec_name,width,height,pix_fmt,profile,level,time_base,sample_rate,channels,channel_layout,color_transfer,color_primaries,color_space,extradata_hash'
    result=process.run([str(probe.absolute()),'-v','error','-protocol_whitelist','file,pipe','-show_data_hash','sha256','-show_entries','stream='+fields,'-of','json',str(Path(path).absolute())],capture_output=True,timeout=15,check=True)
    streams=json.loads(result.stdout).get('streams') or []
    return [{k:s.get(k) for k in fields.split(',')} for s in streams if s.get('codec_type') in ('video','audio')]


def run_copy(args,timeout,cancelled):
    """Cancelable copy; bounded diagnostics cannot fill RAM or the disk."""
    from core.bandwidth import DownloadPaused
    errors=deque(maxlen=8);overflow=threading.Event()
    with process.Popen(args,stdin=process.DEVNULL,stdout=process.DEVNULL,stderr=process.PIPE) as child:
        def read():
            size=0
            while data:=child.stderr.read(4096):
                errors.append(data);size+=len(data)
                if size>1024**2:overflow.set();break
        reader=threading.Thread(target=read,daemon=True);reader.start();deadline=time.monotonic()+timeout
        try:
            while child.poll() is None:
                if cancelled():raise DownloadPaused('DOWNLOAD_PAUSED')
                if overflow.is_set():raise RecordingPartError('recording_incompatible')
                if time.monotonic()>deadline:raise RecordingPartError('processing_timeout')
                time.sleep(.1)
            child.wait()
            if child.returncode:raise RecordingPartError('recording_incompatible')
        finally:
            if child.poll() is None:child.kill()
            child.wait();reader.join(3)


def build_exports(job,bin_dir,action,acknowledge_gaps,progress,cancelled,publish_file):
    from services.output_validation import _read_lease
    with ExitStack() as leases:
        for part in recoverable_parts(job):
            handle=_read_lease(part_path(job,part))
            if handle:leases.callback(handle.Close)
        return _build_exports(job,bin_dir,action,acknowledge_gaps,progress,cancelled,publish_file)


def _build_exports(job,bin_dir,action,acknowledge_gaps,progress,cancelled,publish_file):
    """IDs and paths come only from the server-owned job, never the request."""
    parts=recoverable_parts(job)
    if not parts:raise RecordingPartError()
    if action=='join' and len(parts)<2:raise RecordingPartError('recording_incompatible')
    if action=='join' and not acknowledge_gaps:raise RecordingPartError('recording_ack_required')
    paths=[part_path(job,part) for part in parts]
    signatures=[]
    for index,path in enumerate(paths):
        if cancelled():
            from core.bandwidth import DownloadPaused
            raise DownloadPaused('DOWNLOAD_PAUSED')
        progress('quality_check',index,len(paths));signatures.append(stream_signature(path,bin_dir))
    if action=='join' and any(signature!=signatures[0] for signature in signatures[1:]):raise RecordingPartError('recording_incompatible')
    groups=[list(zip(parts,paths))] if action=='join' else [[pair] for pair in zip(parts,paths)]
    results=[]
    for index,group in enumerate(groups):
        source_signature=signatures[0 if action=='join' else index]
        expected_audio=any(s['codec_type']=='audio' for s in source_signature)
        if cancelled():
            from core.bandwidth import DownloadPaused
            raise DownloadPaused('DOWNLOAD_PAUSED')
        identity=uuid.uuid5(uuid.NAMESPACE_URL,job.id+':'+action+':'+str(Path(job.path).resolve())+':'+':'.join(part['id'] for part,_ in group)).hex
        directory=staging_directory(job.path,identity)
        required=sum(path.stat().st_size for _,path in group)
        if shutil.disk_usage(directory).free<required*1.05+64*1024**2:raise OSError(28,'No space left for recording recovery; parts preserved.')
        output=directory/('recording-'+('joined-' if action=='join' else 'part-')+identity[:8]+'.mkv')
        summary={'continuity':'unknown','joined':action=='join','parts':[p['id'] for p,_ in group],'expected_audio':expected_audio}
        saved=publish_file(output,directory,identity,None,summary)
        if saved:results.append(saved);continue
        # Local aliases keep ffconcat in safe mode and all input names generated.
        aliases=[]
        try:
            for number,(_,path) in enumerate(group):
                alias=directory/('input-'+str(number)+path.suffix)
                if alias.exists():alias.unlink()
                aliases.append(alias)
                try:os.link(path,alias)
                except OSError:
                    if shutil.disk_usage(directory).free<path.stat().st_size+required*1.05+64*1024**2:raise OSError(28,'No space left for recording recovery; parts preserved.')
                    shutil.copyfile(path,alias)
            args=[str(Path(bin_dir)/'ffmpeg.exe'),'-y','-nostdin','-hide_banner','-v','error']
            if action=='join':
                listing=directory/'inputs.ffconcat'
                listing.write_text('ffconcat version 1.0\n'+''.join("file '"+alias.name+"'\n" for alias in aliases),encoding='utf-8')
                args+=['-protocol_whitelist','file,pipe','-f','concat','-safe','1','-i',str(listing)]
            else:args+=['-protocol_whitelist','file,pipe','-i',str(aliases[0])]
            args+=['-map','0:v:0','-map','0:a:0?','-c','copy',str(output)]
            progress('session_join' if action=='join' else 'session_export',index,len(groups))
            run_copy(args,max(120,min(1800,required/(5*1024**2))),cancelled)
            checked=validate_output(output,bin_dir,True,expect_audio=expected_audio,include_duration=True)
            actual=stream_signature(output,bin_dir)
            # Container-specific time bases can differ; encoded stream headers,
            # dimensions, HDR signalling and audio layout must remain identical.
            stable=lambda sig:[{k:v for k,v in stream.items() if k!='time_base'} for stream in sig]
            if stable(actual)!=stable(source_signature):raise RecordingPartError('recording_incompatible')
            results.append(publish_file(output,directory,identity,checked,summary))
        finally:
            for alias in aliases:
                if alias.exists():alias.unlink()
    return results
