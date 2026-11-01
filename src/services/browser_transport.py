"""One optional browser-compatible HTTP retry for an already resolved media URL."""
import re


def enable_browser_transport(ydl,source,error):
    from services.media_discovery import public_url
    message=str(error).lower()
    if not re.search(r'\b403\b',message) or any(word in message for word in ('drm','login required','sign in','private video','copyright')):return False
    if ydl.params.get('_browser_transport_tried') or ydl.params.get('impersonate'):return False
    if not public_url(source,resolve=True):return False
    ydl.params['_browser_transport_tried']=True
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        target=ImpersonateTarget.from_str('chrome')
        if not ydl._impersonate_target_available(target):return False
    except (ImportError,AttributeError,ValueError):return False
    # Rebuild the idle request handlers, retaining the existing scoped cookie jar.
    cookiejar=ydl.cookiejar
    ydl.params['impersonate']=target
    director=vars(ydl).pop('_request_director',None)
    if director is not None:director.close()
    assert ydl.cookiejar is cookiejar
    return True


def download_with_browser_retry(ydl,info,allow_retry,before_retry=None):
    """Retry the identical embedded format once, only before partial media exists."""
    try:return ydl.process_ie_result(info,download=True)
    except Exception as error:
        if info.get('extractor_key') not in ('EmbeddedMedia','FullHDFilmizlesene') or not allow_retry():raise
        source=info.get('url') or next((f.get('url') for f in info.get('requested_formats',[]) if f.get('url')),None)
        if not enable_browser_transport(ydl,source,error):raise
        if before_retry:before_retry()
        return ydl.process_ie_result(info,download=True)
