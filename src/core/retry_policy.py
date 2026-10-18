"""Retry only errors likely to recover; never loop private/deleted/format errors."""
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
