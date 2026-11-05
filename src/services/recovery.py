"""Safe recovery summaries: no raw errors, source tokens or output paths."""


def recovery_items(jobs):
    items = []
    for job in jobs:
        from services.recording_sessions import recoverable_parts
        parts=len(recoverable_parts(job))
        if job.status not in ('paused', 'error', 'pausing') and not parts:
            continue
        reason = 'parts' if job.status=='finished' and parts else 'publication' if job.recovery_reason=='publication' else 'live' if job.is_live else (
            'refresh' if job.error_code in ('access_denied', 'not_found', 'source_mismatch', 'partial_preserved')
            else 'error' if job.status == 'error'
            else job.recovery_reason or ('interrupted' if job.restored else 'paused'))
        actions=[] if reason=='parts' else ['finalize','folder'] if reason=='publication' else ['resume'] if job.is_live else ['resume','refresh']
        if job.error_code in ('disk_full','file_access_denied'):actions.insert(0,'folder')
        if job.error_code=='container_incompatible' and not job.is_live:actions.insert(0,'mkv')
        if job.error_code=='quality_mismatch' and not job.is_live:actions.insert(0,'max_quality')
        items.append({'id': job.id, 'url': job.url, 'title': job.title,'actions':list(dict.fromkeys(actions)),
                      'percent': job.percent, 'downloaded_bytes': job.downloaded_bytes,
                      'reason': reason, 'error_code': job.error_code,
                      'parts_count':parts,'parts_ready':job.future is None and not job.recording_action,
                      'ready': job.future is None and not job.recording_action and job.status in ('paused', 'error') and job.security_status not in ('blocked','review'),
                      'is_live': job.is_live})
    return items
