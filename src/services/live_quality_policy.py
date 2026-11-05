"""Preserve explicit HDR selection when choosing an available DVR representation."""
from services.media_quality import selected_profile


def choose_recording_source(original,candidate,router):
    before=selected_profile(original)
    parts=candidate.get('requested_formats') or [candidate]
    explicit_sdr=any(str(p.get('dynamic_range') or '').upper()=='SDR' for p in parts if p.get('vcodec') not in (None,'none'))
    if router and before.get('hdr') and explicit_sdr:
        router.close()
        return original,None
    if before.get('hdr') and not selected_profile(candidate).get('hdr'):
        # Missing metadata does not establish a downgrade; require the actual
        # completed output to retain HDR before it can be published.
        candidate=dict(candidate,dynamic_range=original.get('dynamic_range') or 'HDR')
    return candidate,router
