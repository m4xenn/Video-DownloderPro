"""Bounded YouTube player-country discovery, scoped to one engine instance."""
from copy import deepcopy
import time
from urllib.parse import urlsplit

# Locale preferences, not network exits. Stop at the first playable result.
COUNTRIES=('DE', 'US', 'GB', 'NL', 'FR', 'CA')
SEARCH_SECONDS=45
ATTEMPT_TIMEOUT=8


def _availability_error(error):
    reason=str(error).lower()
    # A retry cannot resolve authentication, removed content or throttling.
    if any(marker in reason for marker in ('private video', 'removed', 'deleted',
            'sign in', 'login required', 'age-restricted', '429', '403', 'copyright')):
        return False
    return any(marker in reason for marker in ('country domain', 'legal complaint',
        'video unavailable', 'not available in your country', 'geo-restricted'))


def _playable(info):
    if not isinstance(info,dict) or info.get('has_drm'):
        return False
    formats=info.get('formats') or info.get('requested_formats') or [info]
    return any(isinstance(f,dict) and (f.get('url') or f.get('manifest_url'))
               and not f.get('has_drm') and f.get('ext')!='mhtml'
               and f.get('protocol')!='mhtml'
               and not (f.get('vcodec')=='none' and f.get('acodec')=='none')
               for f in formats)


def extract_info(ydl, url, download=False):
    from yt_dlp.utils import DownloadError
    from yt_dlp.extractor.youtube import YoutubeIE as OriginalYoutubeIE
    from services.source_operation import current_operation, report_stage
    try:
        host=(urlsplit(url).hostname or '').lower()
    except ValueError:
        host=''
    if host not in ('youtube.com','www.youtube.com','m.youtube.com','music.youtube.com','youtu.be'):
        return ydl.extract_info(url, download=download)
    saved={key:(key in ydl.params,ydl.params.get(key))
           for key in ('ignoreerrors','socket_timeout','extractor_retries')}
    ydl.params['ignoreerrors']=False
    try:
        try:
            return ydl.extract_info(url, download=download)
        except DownloadError as error:
            if not _availability_error(error):raise
            last_error=error
        original=ydl.get_info_extractor('Youtube')
        selected=['']

        class YoutubeIE(OriginalYoutubeIE):
            def _extract_context(self, *args, **kwargs):
                context=deepcopy(super()._extract_context(*args, **kwargs))
                context.setdefault('client', {})['gl']=selected[0]
                return context

        deadline=time.monotonic()+SEARCH_SECONDS
        configured=saved['socket_timeout'][1]
        timeout=min(configured,ATTEMPT_TIMEOUT) if isinstance(configured,(int,float)) and configured>0 else ATTEMPT_TIMEOUT
        ydl.params.update(socket_timeout=timeout,extractor_retries=0)
        report_stage('searching_regions')
        try:
            for country in COUNTRIES:
                operation=current_operation()
                if operation and operation.cancelled():
                    from core.bandwidth import DownloadPaused
                    raise DownloadPaused('DOWNLOAD_PAUSED')
                # Budget is checked between extractor calls; it is not a hard
                # deadline for all of yt-dlp's internal network requests.
                if time.monotonic()>=deadline:break
                selected[0]=country
                # Fresh instance prevents client context from a failed country
                # contaminating the next attempt or concurrent downloads.
                ydl.add_info_extractor(YoutubeIE(ydl))
                try:
                    info=ydl.extract_info(url, download=False)
                except DownloadError as error:
                    if not _availability_error(error):raise
                    last_error=error
                    continue
                if not _playable(info):continue
                info['youtube_player_country']=country
                report_stage('validating_source')
                if download:
                    return ydl.process_ie_result(info,download=True)
                return info
            raise last_error
        finally:
            ydl.add_info_extractor(original)
    finally:
        for key,(present,value) in saved.items():
            if present:ydl.params[key]=value
            else:ydl.params.pop(key,None)
