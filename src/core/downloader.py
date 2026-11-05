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
    from services.output_validation import validation_session
    with validation_session(),source_operation(req_opts.get('_stage'),retain=True,cancelled=lambda:bool(state['cancel_flags'].get(url))):
        return _download_single_impl(url,ydl_opts,save_path,req_opts,folder_id)


def _download_single_impl(url, ydl_opts, save_path, req_opts, folder_id=None):
    from services.diagnostics import diagnostics, DiagnosticLogger
    from services.source_operation import current_operation,report_stage
    from services.source_recovery import forbidden,same_media,has_partial,refresh_source,EMBEDDED,template_has_partial,can_resume_embedded,source_checkpoint
    operation=current_operation()
    output_reservation = None
    phase = ['metadata']
    received=[0]
    denied=[False]
    policy_ticket=None;policy_bytes=0;policy_success=False;policy_failed=False
    policy_streams={};policy_first=None;policy_last=None
    from core.fragment_policy import fragment_policy
    def warning(message):
        nonlocal policy_failed
        from services.diagnostics import error_code
        if error_code(message) in ('access_denied','rate_limited'):
            denied[0]=forbidden(message);policy_failed=True
    def handoff_progress(data):
        nonlocal policy_bytes,policy_first,policy_last
        if data.get('status')=='downloading' and data.get('downloaded_bytes',0)>0:
            policy_streams[data.get('filename') or data.get('tmpfilename') or 'media']=data['downloaded_bytes']
            policy_bytes=sum(policy_streams.values());policy_last=time.monotonic()
            if policy_first is None:policy_first=policy_last
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
            details=data.get('info_dict') or {}
            if details.get('extractor_key') in EMBEDDED:
                # Remuxing can turn a truncated VOD prefix into a valid short
                # MP4. Check the original container before any postprocessor.
                from services.output_validation import validate_mp4_extent
                paths=[details.get('filepath'),*(details.get('__files_to_merge') or [])]
                for path in paths:
                    if path:validate_mp4_extent(path)
    ydl_opts['postprocessor_hooks'] = [*ydl_opts.get('postprocessor_hooks', []), diagnostic_postprocess]
    diagnostics.record('download', url, 'started')
    try:
        from yt_dlp import YoutubeDL
        from services.media_process import install_yt_dlp_guard
        install_yt_dlp_guard()
        with YoutubeDL(ydl_opts) as ydl:
            from services.secure_transport import attach_network_guard
            attach_network_guard(ydl)
            from services.merge_recovery import attach_merge_recovery
            attach_merge_recovery(ydl, lambda: bool(state['cancel_flags'].get(url)), report_stage)
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
                if req_opts.get('_resume_target') and template_has_partial(ydl.params.get('outtmpl')) and not all((req_opts.get('_source_signature') or {}).get('_representations') or [None]):
                    raise ValueError('403: Kısmi dosya korundu. Eski kaynak doğrulanamadığı için yeni kaynağa otomatik devam edilmiyor.') from error
                refreshed=True;operation.release();report_stage('refreshing_source')
                diagnostics.record('metadata',url,'source_refresh')
                info=refresh_source(ydl,url,'FullHDFilmizlesene' if supported_page(url) else 'EmbeddedMedia')
            if not info:
                raise Exception("Video bilgisi alınamadı (Gizli veya kullanılamıyor olabilir).")
            from services.track_selection import validate_subtitle_choice
            validate_subtitle_choice(info, req_opts)
            from services.media_quality import validate_container
            validate_container(info,req_opts)
            if info.get('is_live') and 'live_record_minutes' not in req_opts:
                raise ValueError('Inspect one live source and choose a recording duration before starting.')
            if req_opts.get('live_record_minutes') and not info.get('is_live'):
                raise ValueError('Source is no longer live; inspect it again to download the replay.')
            report_stage('validating_source')
            if info.get('source_status') == 'partial':
                from services.media_preflight import PartialSourceError
                raise PartialSourceError()
            # Embedded CDNs often throttle bursts. Sequential fragments also keep
            # their resume checkpoint aligned with the last appended fragment.
            policy_ticket,fragment_limit=fragment_policy.begin(info,req_opts.get('_transfer_mode','stable'),budget.rate if budget else 0)
            ydl.params['concurrent_fragment_downloads']=fragment_limit
            if info.get('is_live') and budget and budget.rate:
                raise ValueError('Canlı kayıt toplam hız sınırını desteklemiyor. Kayıt için sınırı kaldırın.')
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
                final_ext = req_opts.get('video_container','mp4')
                if final_ext not in ('mp4','mkv'):raise ValueError('Invalid video container.')

            base_name = os.path.splitext(filename)[0]
            final_filename = f"{base_name}.{final_ext}"
            if req_opts.get('_resume_target') and info.get('extractor_key') in EMBEDDED and has_partial(final_filename) and not can_resume_embedded(req_opts.get('_source_signature'),info):
                raise ValueError('Kısmi dosya korundu. Kaynak veya format değiştiği için yeni indirme gerekiyor.')
            if req_opts.get('_metadata'):req_opts['_metadata'](info)

            from core.output_paths import reserve_output
            output_reservation = reserve_output(base_name, resume=bool(req_opts.get('_resume_target')) and not info.get('is_live'))
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
            from services.browser_transport import download_with_browser_retry
            def browser_retry():
                denied[0]=False
                diagnostics.record('download',url,'browser_transport_retry')
            if info.get('is_live'):
                from services.live_recording import record_live
                from services.youtube_dvr import prepare_youtube_dvr
                cancelled=lambda:bool(state['cancel_flags'].get(url))
                live_info,dvr_router=prepare_youtube_dvr(ydl,info,url,cancelled)
                from services.live_quality_policy import choose_recording_source
                live_info,dvr_router=choose_recording_source(info,live_info,dvr_router)
                try:
                    if req_opts.get('_live_part'):req_opts['_live_part']('started',final_filename,live_info)
                    def live_progress(data):
                        for hook in ydl_opts.get('progress_hooks',[]):hook(data)
                        if data.get('status')=='finished':report_stage('recording_finalize')
                    recorded=record_live(live_info,final_filename,ydl_opts.get('ffmpeg_location') or '',req_opts,
                                cancelled,req_opts.get('_stop_recording',lambda:False),
                                live_progress,
                                dvr_router=dvr_router)
                except BaseException as error:
                    if req_opts.get('_live_part'):
                        from services.diagnostics import error_code
                        req_opts['_live_part']('interrupted',final_filename,live_info,error_code(error))
                    raise
                finally:
                    if dvr_router:dvr_router.close()
                info=live_info
                info['duration']=recorded['recorded_seconds']
                if req_opts.get('_live_part'):req_opts['_live_part']('captured',final_filename,info)
                if req_opts.get('_metadata'):req_opts['_metadata'](info)
                result=info
            else:
                result=None
            try:
                if not info.get('is_live'):result = download_with_browser_retry(ydl,info,lambda:not received[0] and not has_partial(final_filename),browser_retry)
            except Exception as error:
                if refreshed or not forbidden(error) or info.get('extractor_key') not in EMBEDDED:raise
                partial=bool(received[0] or has_partial(final_filename))
                if partial and not all(source_checkpoint(info).get('_representations') or [None]):
                    raise ValueError('403: Kısmi dosya korundu. Kaynak değişikliğiyle güvenli devam doğrulanamadı; yeni indirme gerekiyor.') from error
                operation.release();report_stage('refreshing_source')
                diagnostics.record('download',url,'source_refresh')
                renewed=refresh_source(ydl,url,info['extractor_key'])
                validate_subtitle_choice(renewed, req_opts)
                if renewed.get('source_status')=='partial':
                    from services.media_preflight import PartialSourceError
                    raise PartialSourceError()
                if partial and not can_resume_embedded(source_checkpoint(info),renewed):
                    raise ValueError('403: Kısmi dosya korundu. Yenilenen dosya aynı temsil olarak doğrulanamadı.') from error
                if not same_media(info,renewed):
                    raise ValueError('403: Yenilenen kaynağın aynı video ve format olduğu doğrulanamadı.') from error
                # Lock the original output target across a changed signed URL/title.
                template=os.path.splitext(final_filename)[0].replace('%','%%')+'.%(ext)s'
                if isinstance(ydl.params.get('outtmpl'),dict):ydl.params['outtmpl']['default']=template
                else:ydl.params['outtmpl']=template
                report_stage('validating_source')
                denied[0]=False
                info=renewed
                if req_opts.get('_metadata'):req_opts['_metadata'](info)
                result=ydl.process_ie_result(renewed,download=True)
            if result and os.path.isfile(final_filename):
                verified=None
                if req_opts.get('_verify'):
                    verified=req_opts['_verify'](final_filename,info)
                if info.get('extractor_key') in EMBEDDED and not req_opts.get('_verify'):
                    from services.output_validation import validate_output
                    validate_output(final_filename,ydl_opts.get('ffmpeg_location') or '',req_opts.get('format')!='audio',
                                    expected_duration=info.get('duration') if not info.get('is_live') else None,
                                    expect_audio=any(f.get('acodec') not in (None,'none') for f in (info.get('requested_formats') or [info])))
                if req_opts.get('_preview_dir'):
                    report_stage('preview')
                    from services.preview_service import create_preview
                    preview_info=dict(info)
                    if isinstance(verified,dict) and verified.get('duration'):
                        preview_info['duration']=verified['duration']
                    preview=create_preview(ydl,preview_info,final_filename,ydl_opts.get('ffmpeg_location') or '',
                        req_opts['_preview_dir'],req_opts['_preview_id'],req_opts.get('format')!='audio')
                    if req_opts.get('_thumbnail'):
                        req_opts['_thumbnail'](preview)
                if req_opts.get('_completed'):
                    req_opts['_completed'](final_filename)
                # Update status
                state_actions.update_item_progress(url, status="finished")
                diagnostics.record('download', url, 'finished')
                policy_success=True
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
        fragment_policy.finish(policy_ticket,policy_bytes,policy_success and not policy_failed,
                               policy_last-policy_first if policy_first is not None else 0)
        if output_reservation:
            output_reservation.release()
    return False
