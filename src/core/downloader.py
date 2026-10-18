# ============================================================
#  src/core/downloader.py
#  Temel indirme fonksiyonları ve progress kancaları
#
#  app.py'den taşındı (FAZ 4d)
# ============================================================

import time
import os
import sys

# Kök dizini sys.path'e ekle (modül importları için)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from state.app_state import state, state_actions
    from utils.formatters import clean_ansi
    import shutil
except ImportError:
    pass

def progress_hook(d):
    url = d.get('info_dict', {}).get('webpage_url')
    
    if url and state["cancel_flags"].get(url):
        state_actions.update_item_progress(url, status="paused")
        raise Exception("DOWNLOAD_PAUSED")

    if d['status'] == 'downloading':
        try:
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            percent = 0
            if total:
                percent = round((downloaded / total) * 100, 1)

            speed = d.get('_speed_str', 'Hesaplanıyor...')
            if speed:
                speed = clean_ansi(speed)
            
            if url:
                state_actions.update_item_progress(url, percent=percent, speed=speed, status="downloading")
        except: pass
    elif d['status'] == 'finished':
        if url:
            state_actions.update_item_progress(url, percent=100, status="converting")

def _download_single(url, ydl_opts, save_path, req_opts, folder_id=None):
    from services.source_operation import source_operation
    with source_operation(req_opts.get('_stage'),retain=True,cancelled=lambda:bool(state['cancel_flags'].get(url))):
        return _download_single_impl(url,ydl_opts,save_path,req_opts,folder_id)


def _download_single_impl(url, ydl_opts, save_path, req_opts, folder_id=None):
    from services.diagnostics import diagnostics, DiagnosticLogger
    from services.source_operation import current_operation,report_stage
    from services.source_recovery import forbidden,same_media,has_partial,refresh_source,EMBEDDED,template_has_partial,can_resume_embedded
    operation=current_operation()
    output_reservation = None
    phase = ['metadata']
    received=[0]
    denied=[False]
    def warning(message):
        from services.diagnostics import error_code
        if error_code(message) in ('access_denied','rate_limited'):denied[0]=forbidden(message)
    def handoff_progress(data):
        if data.get('status')=='downloading' and data.get('downloaded_bytes',0)>0:
            received[0]=max(received[0],data['downloaded_bytes'])
            operation.release();report_stage('downloading')
    ydl_opts = dict(ydl_opts, logger=DiagnosticLogger('download', url, req_opts.get('_stage'),warning))
    sleeps=dict(ydl_opts.get('retry_sleep_functions') or {})
    fragment_wait=sleeps.get('fragment')
    if callable(fragment_wait):sleeps['fragment']=lambda n:0 if denied[0] else fragment_wait(n)
    ydl_opts['retry_sleep_functions']=sleeps
    ydl_opts['progress_hooks']=[handoff_progress,*ydl_opts.get('progress_hooks',[])]
    def diagnostic_postprocess(data):
        if data.get('status') == 'started':
            phase[0] = 'postprocess'
            report_stage('postprocess')
    ydl_opts['postprocessor_hooks'] = [*ydl_opts.get('postprocessor_hooks', []), diagnostic_postprocess]
    diagnostics.record('download', url, 'started')
    try:
        from yt_dlp import YoutubeDL
        with YoutubeDL(ydl_opts) as ydl:
            budget = req_opts.get('_budget')
            if budget:
                from core.bandwidth import attach_budget
                attach_budget(ydl, budget, lambda: bool(state['cancel_flags'].get(url)),
                              req_opts.get('_record', lambda _: None))
            # We need to extract info first to get the filename and title!
            from services.site_resolver import extract_media_info
            report_stage('finding_player')
            refreshed=False
            try:info = extract_media_info(ydl, url, fresh=True)
            except Exception as error:
                from services.generic_resolver import generic_resolver
                from services.site_resolver import supported_page
                if not forbidden(error) or not (supported_page(url) or generic_resolver.pending(url)):raise
                if req_opts.get('_resume_target') and template_has_partial(ydl.params.get('outtmpl')):
                    raise ValueError('403: Kısmi dosya korundu. Eski kaynak doğrulanamadığı için yeni kaynağa otomatik devam edilmiyor.') from error
                refreshed=True;operation.release();report_stage('refreshing_source')
                diagnostics.record('metadata',url,'source_refresh')
                info=refresh_source(ydl,url,'FullHDFilmizlesene' if supported_page(url) else 'EmbeddedMedia')
            if not info:
                raise Exception("Video bilgisi alınamadı (Gizli veya kullanılamıyor olabilir).")
            report_stage('validating_source')
            # Embedded CDNs often throttle bursts. Sequential fragments also keep
            # their resume checkpoint aligned with the last appended fragment.
            if info.get('extractor_key') in ('EmbeddedMedia', 'FullHDFilmizlesene'):
                ydl.params['concurrent_fragment_downloads'] = 1
            if budget:
                from yt_dlp.downloader import get_suitable_downloader
                formats = info.get('requested_formats') or [info]
                native = True
                for selected in formats:
                    downloader = get_suitable_downloader(selected, ydl.params)
                    if not downloader or downloader.__name__ not in ('HttpFD', 'HlsFD', 'DashSegmentsFD'):
                        native = False
                if req_opts.get('_protocol_support'):
                    req_opts['_protocol_support'](native)
                if budget.rate and not native:
                    raise ValueError('Bu yayın türü toplam hız sınırını desteklemiyor. Sınırı kaldırarak tekrar deneyin.')
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'Video')
            thumb = info.get('thumbnails', [{'url': ''}])[-1]['url'] if info.get('thumbnails') else ''
            
            # 1. Dosya varsa (1), (2) şeklinde isimlendir
            if req_opts.get("format") == "audio":
                final_ext = req_opts.get("quality", "mp3")
                if final_ext not in ['mp3', 'm4a', 'wav', 'opus']:
                    final_ext = "mp3"
            else:
                final_ext = "mp4"

            base_name = os.path.splitext(filename)[0]
            final_filename = f"{base_name}.{final_ext}"
            if req_opts.get('_resume_target') and info.get('extractor_key') in EMBEDDED and has_partial(final_filename) and not can_resume_embedded(req_opts.get('_source_signature'),info):
                raise ValueError('Kısmi dosya korundu. Kaynak veya format değiştiği için yeni indirme gerekiyor.')
            if req_opts.get('_metadata'):req_opts['_metadata'](info)

            from core.output_paths import reserve_output
            output_reservation = reserve_output(base_name, resume=bool(req_opts.get('_resume_target')))
            if output_reservation.base != base_name:
                new_outtmpl = output_reservation.base.replace('%', '%%') + '.%(ext)s'
                
                if isinstance(ydl.params.get('outtmpl'), dict):
                    ydl.params['outtmpl']['default'] = new_outtmpl
                else:
                    ydl.params['outtmpl'] = new_outtmpl
                
                final_filename = output_reservation.base + '.' + final_ext
                filename = final_filename

            if req_opts.get('_target'):
                template_base = os.path.splitext(final_filename)[0].replace('%', '%%')
                req_opts['_target'](template_base + '.%(ext)s')

            # Reuse the resolved media information rather than extracting the URL again.
            phase[0] = 'download'
            try:result = ydl.process_ie_result(info, download=True)
            except Exception as error:
                if refreshed or not forbidden(error) or info.get('extractor_key') not in EMBEDDED:raise
                if received[0] or has_partial(final_filename):
                    raise ValueError('403: Kısmi dosya korundu. Kaynak değişikliğiyle güvenli devam doğrulanamadı; yeni indirme gerekiyor.') from error
                operation.release();report_stage('refreshing_source')
                diagnostics.record('download',url,'source_refresh')
                renewed=refresh_source(ydl,url,info['extractor_key'])
                if not same_media(info,renewed):
                    raise ValueError('403: Yenilenen kaynağın aynı video ve format olduğu doğrulanamadı.') from error
                # Lock the original output target across a changed signed URL/title.
                template=os.path.splitext(final_filename)[0].replace('%','%%')+'.%(ext)s'
                if isinstance(ydl.params.get('outtmpl'),dict):ydl.params['outtmpl']['default']=template
                else:ydl.params['outtmpl']=template
                report_stage('validating_source')
                denied[0]=False
                result=ydl.process_ie_result(renewed,download=True)
            if result and os.path.isfile(final_filename):
                if req_opts.get('_preview_dir'):
                    from services.preview_service import create_preview
                    preview=create_preview(ydl,info,final_filename,ydl_opts.get('ffmpeg_location') or '',
                        req_opts['_preview_dir'],req_opts['_preview_id'],req_opts.get('format')!='audio')
                    if req_opts.get('_thumbnail'):
                        req_opts['_thumbnail'](preview)
                if req_opts.get('_completed'):
                    req_opts['_completed'](final_filename)
                # Update status
                state_actions.update_item_progress(url, status="finished")
                diagnostics.record('download', url, 'finished')
                return True

    except Exception as e:
        if state['cancel_flags'].get(url) or str(e) == "DOWNLOAD_PAUSED":
            state_actions.update_item_progress(url, status='paused')
            pass # Handled
        else:
            diagnostics.record(phase[0], url, error=e)
            if req_opts.get('_error'):
                req_opts['_error'](str(e))
            state_actions.update_item_progress(url, status="error")
    finally:
        if output_reservation:
            output_reservation.release()
    return False
