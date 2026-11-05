"""Only a source end marker establishes a successful early live completion."""
def confirmed_source_end(formats,contexts,router=None):
    if router is not None and getattr(router,'ended',False):return True
    from services.live_catchup import read_window
    try:
        return bool(formats) and all(
            ('m3u8' in fmt.get('protocol','') or '.m3u8' in fmt.get('url','').split('?',1)[0])
            and read_window(fmt['url'],context,allow_discontinuity=True).ended
            for fmt,context in zip(formats,contexts))
    except (ValueError,OSError):return False
