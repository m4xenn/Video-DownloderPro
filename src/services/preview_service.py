"""Small local previews: source cover first, useful middle frame as fallback."""
import io
import json
import os
import re
from pathlib import Path
import subprocess
import time
from PIL import Image, ImageOps, ImageStat

MAX_COVER_BYTES = 8 * 1024 * 1024


def cover_urls(info):
    values = [info.get('thumbnail')]
    thumbnails = sorted((item for item in info.get('thumbnails') or [] if isinstance(item, dict)),
                        key=lambda item: (item.get('preference') or 0, (item.get('width') or 0)*(item.get('height') or 0)), reverse=True)
    values.extend(item.get('url') for item in thumbnails)
    return list(dict.fromkeys(value for value in values if isinstance(value,str) and value.startswith(('https://','http://'))))[:3]


def useful_image(data):
    """Reject empty/dark frames, but allow portrait covers and letterboxing."""
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.width * source.height > 20_000_000:
                return None
            image = ImageOps.exif_transpose(source).convert('RGB')
            center = ImageOps.fit(image,(32,32)).convert('L')
            pixels=list(center.getdata())
            if ImageStat.Stat(center).mean[0] < 16 and sum(value > 25 for value in pixels) < len(pixels)*.12:
                return None
            image.thumbnail((400,400),Image.Resampling.LANCZOS)
            return image
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


def middle_frame(path, bin_dir, duration=None, deadline=None):
    deadline=deadline or time.monotonic()+12
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    if not isinstance(duration,(int,float)) or duration <= 0:
        try:
            result=subprocess.run([str(Path(bin_dir)/'ffprobe.exe'),'-v','error','-show_entries','format=duration','-of','json',str(path)],
                                  capture_output=True,timeout=max(.1,min(5,deadline-time.monotonic())),creationflags=flags,check=True)
            duration=float(json.loads(result.stdout)['format']['duration'])
        except (OSError,ValueError,KeyError,subprocess.SubprocessError):
            return None
    for fraction in (.5,.35,.65):
        if time.monotonic() >= deadline: break
        try:
            result=subprocess.run([str(Path(bin_dir)/'ffmpeg.exe'),'-hide_banner','-loglevel','error','-ss',str(max(0,duration*fraction)),
                '-i',str(path),'-frames:v','1','-vf',"scale=400:400:force_original_aspect_ratio=decrease",'-f','image2pipe','-vcodec','mjpeg','pipe:1'],
                capture_output=True,timeout=max(.1,min(4,deadline-time.monotonic())),creationflags=flags,check=True)
            image=useful_image(result.stdout)
            if image is not None:
                return image
        except (OSError,subprocess.SubprocessError):
            continue
    return None


def create_preview(ydl, info, output, bin_dir, cache_dir, identity, video=True):
    """Failure never turns a successful media download into an error."""
    try:
        if not re.fullmatch(r'[a-f0-9]{32}',str(identity)):
            return ''
        image=None
        deadline=time.monotonic()+12
        from yt_dlp.networking import Request
        for url in cover_urls(info):
            if time.monotonic() >= deadline: break
            try:
                with ydl.urlopen(Request(url,headers=info.get('http_headers') or {},extensions={'timeout':3})) as response:
                    data=response.read(MAX_COVER_BYTES+1)
                if len(data) <= MAX_COVER_BYTES:
                    image=useful_image(data)
                    if image is not None: break
            except Exception:
                continue
        if image is None and video:
            image=middle_frame(output,bin_dir,info.get('duration'),deadline)
        if image is None:
            return ''
        directory=Path(cache_dir);directory.mkdir(parents=True,exist_ok=True)
        destination=directory/(identity+'.jpg');temporary=destination.with_suffix('.tmp')
        image.save(temporary,format='JPEG',quality=86)
        os.replace(temporary,destination)
        return '/previews/'+destination.name
    except Exception:
        return ''
