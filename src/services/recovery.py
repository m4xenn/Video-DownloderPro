"""Safe recovery summaries: no raw errors, source tokens or output paths."""


def recovery_items(jobs):
    items = []
    for job in jobs:
        if job.status not in ('paused', 'error', 'pausing'):
            continue
        reason = 'live' if job.is_live else (
            'refresh' if job.error_code in ('access_denied', 'not_found', 'source_mismatch', 'partial_preserved')
            else 'error' if job.status == 'error'
            else job.recovery_reason or ('interrupted' if job.restored else 'paused'))
        items.append({'id': job.id, 'url': job.url, 'title': job.title,
                      'percent': job.percent, 'downloaded_bytes': job.downloaded_bytes,
                      'reason': reason, 'error_code': job.error_code,
                      'ready': job.future is None and job.status in ('paused', 'error'),
                      'is_live': job.is_live})
    return items
