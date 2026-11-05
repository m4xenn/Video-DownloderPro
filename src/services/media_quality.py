"""Selected-stream quality contract. Never silently encode video to fit a container."""
import json,math
from pathlib import Path
from services import media_process as process


class QualityMismatch(ValueError):
    code='quality_mismatch'
    def __init__(self,expected=None,actual=None):
        self.expected,self.actual=expected or {},actual or {}
        super().__init__('[quality_mismatch] Output does not preserve the selected source quality; file preserved.')


class ContainerIncompatible(ValueError):
    code='container_incompatible'
    def __init__(self):super().__init__('[container_incompatible] Selected streams cannot be copied to MP4; choose MKV to preserve quality.')


def container_option(data):
    value=data.get('video_container','mp4')
    if value not in ('mp4','mkv') or data.get('format')=='audio' and value!='mp4':raise ValueError('Invalid video container.')
    return value


def codec(value):
    value=str(value or '').lower()
    for prefix,name in [('avc','h264'),('h264','h264'),('h265','hevc'),('hev','hevc'),('hvc','hevc'),('vp09','vp9'),('vp9','vp9'),('vp8','vp8'),('av01','av1'),('av1','av1'),('mpeg4','mpeg4'),('theora','theora')]:
        if value.startswith(prefix):return name
    return None


def selected_profile(info):
    parts=info.get('requested_formats') or [info]
    video=next((p for p in parts if p.get('vcodec') not in (None,'none')),info)
    result={}
    for key in ('width','height','fps'):
        value=video.get(key)
        if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0:result[key]=value
    if codec(video.get('vcodec')):result['codec']=codec(video['vcodec'])
    value=video.get('dynamic_range') or info.get('dynamic_range')
    if isinstance(value,str) and value.upper() in ('HDR','HDR10','HDR10+','HLG','DV','DOLBY VISION'):result['hdr']=True
    return result


def validate_container(info,options):
    if options.get('format')=='audio' or options.get('video_container','mp4')=='mkv':return
    for part in info.get('requested_formats') or [info]:
        if codec(part.get('vcodec')) in ('vp8','theora') or part.get('acodec') in ('vorbis','speex'):raise ContainerIncompatible()


def _rate(value):
    try:
        a,b=str(value).split('/');return float(a)/float(b)
    except (ValueError,ZeroDivisionError):return None


def verify_quality(path,bin_dir,info,options):
    expected=selected_profile(info)
    cap={'720p':720,'1080p':1080,'4k':2160,'8k':4320}.get(options.get('quality'))
    if cap:expected['height_cap']=cap
    summary={'container':Path(path).suffix.lower().lstrip('.'),'video_reencoded':False,'expected':expected}
    if options.get('format')=='audio':
        summary.update(video_reencoded=None,audio_conversion='selected_format',verified_fields=[])
        return summary
    if not expected:
        summary['verified_fields']=[];return summary
    folder=Path(bin_dir);folder=folder.parent if folder.name.lower().startswith('ffmpeg.') else folder
    probe=folder/('ffprobe.exe' if (folder/'ffprobe.exe').is_file() else 'ffprobe')
    result=process.run([str(probe.absolute()),'-v','error','-protocol_whitelist','file,pipe','-select_streams','v:0',
        '-show_entries','stream=codec_name,width,height,r_frame_rate,pix_fmt,color_transfer,color_primaries:stream_disposition=attached_pic:stream_side_data=side_data_type','-of','json',str(Path(path).absolute())],capture_output=True,timeout=15,check=True)
    streams=json.loads(result.stdout).get('streams') or []
    if not streams or not isinstance(streams[0],dict):raise QualityMismatch()
    actual=streams[0];facts={k:actual.get(k) for k in ('width','height','codec_name','pix_fmt','color_transfer','color_primaries')}
    fps=_rate(actual.get('r_frame_rate'))
    if fps and math.isfinite(fps):facts['fps']=round(fps,3)
    def mismatch():return QualityMismatch(expected,facts)
    if cap and (not actual.get('height') or actual['height']>cap):raise mismatch()
    verified=[]
    for key in ('width','height'):
        if key in expected:
            if actual.get(key)!=expected[key]:raise mismatch()
            verified.append(key)
    if expected.get('codec'):
        if actual.get('codec_name')!=expected['codec']:raise mismatch()
        verified.append('codec')
    if expected.get('fps') and fps:
        if fps+.1<expected['fps']:raise mismatch()
        verified.append('fps')
    if expected.get('hdr'):
        hdr=actual.get('color_transfer') in ('smpte2084','arib-std-b67') or any('DOVI' in p.get('side_data_type','') for p in actual.get('side_data_list',[]))
        if not hdr:raise mismatch()
        verified.append('hdr')
    summary.update(actual=facts,verified_fields=verified)
    return summary
