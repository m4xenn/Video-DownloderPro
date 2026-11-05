"""Preserve Windows' Internet-zone treatment without storing signed source URLs."""
import os
from pathlib import Path


def mark_internet_file(path):
    if os.name!='nt':return False
    target=Path(path)
    if not target.is_file():return False
    try:
        with open(str(target)+':Zone.Identifier','w',encoding='ascii') as stream:
            stream.write('[ZoneTransfer]\nZoneId=3\n')
        return True
    except OSError:
        # FAT/exFAT and some shares lack alternate streams. Keep the media file.
        return False
