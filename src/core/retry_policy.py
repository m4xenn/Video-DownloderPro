"""Retry only errors likely to recover; never loop private/deleted/format errors."""
import time


def fragment_retry_wait(cancelled, sleep=time.sleep, clock=time.monotonic, progress=None):
    """yt-dlp sleep callback: bounded backoff that remains interruptible."""
    def wait(n):
        from core.bandwidth import DownloadPaused
        if progress:progress('waiting_server')
        deadline = clock() + min(60, 5 * 2 ** min(max(0, n), 4))
        while clock() < deadline:
            if cancelled():
                raise DownloadPaused('DOWNLOAD_PAUSED')
            sleep(min(.1, max(0, deadline - clock())))
        return 0  # Waiting was handled here, not by yt-dlp's blocking sleep.
    return wait

def transient_error(message):
    text = (message or '').lower()
    permanent = ('private video', 'deleted', 'not available', 'unavailable', 'unsupported url',
                 'requested format', 'sign in', 'login', 'members-only', 'copyright', 'geo',
                 '403', '404', 'file not found', 'permission denied', 'no space',
                 'hız sınırını desteklemiyor', 'dosya oluşturulamadı')
    if any(word in text for word in permanent):
        return False
    return any(word in text for word in ('timeout', 'timed out', 'connection', 'network', 'temporarily',
                                         'remote end closed', '429', '500', '502', '503', '504',
                                         'name resolution', 'getaddrinfo', 'connection reset'))


def retry_delay(attempt):
    return min(60, 5 * (2 ** max(0, attempt - 1)))
