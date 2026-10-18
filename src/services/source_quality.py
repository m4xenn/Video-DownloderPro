"""Portable quality choices derived from the source, never arbitrary yt-dlp selectors."""
import math
import re


def parse_source_quality(value):
    match = re.fullmatch(r'source:(\d{1,5}):(\d{1,3}(?:\.\d{1,3})?)', str(value))
    if not match:
        return None
    height, fps = int(match[1]), float(match[2])
    return (height, fps) if 1 <= height <= 16384 and 0 <= fps <= 240 else None


def source_qualities(info):
    choices = {}
    for item in info.get('formats') or [info]:
        if item.get('has_drm') or item.get('vcodec') in ('none', 'images') or item.get('protocol') == 'mhtml' or not item.get('height'):
            continue
        height, fps = item.get('height'), item.get('fps') or 0
        if not isinstance(height, (int, float)) or not isinstance(fps, (int, float)):
            continue
        if not math.isfinite(height) or not math.isfinite(fps):
            continue
        value = f'source:{int(height)}:{round(fps, 3):g}'
        if not parse_source_quality(value):
            continue
        size = item.get('filesize') or item.get('filesize_approx')
        # Video-only stream size is not a complete output size. Do not advertise it as one.
        size = size if item.get('acodec') not in (None, 'none') else None
        choices[value] = {'value':value, 'height':int(height), 'fps':round(fps,3),
                          'label':f'{int(height)}p' + (f' · {fps:g} FPS' if fps else ''),
                          'total_bytes':size}
    return sorted(choices.values(), key=lambda choice:(choice['height'],choice['fps']), reverse=True)
