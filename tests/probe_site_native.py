"""Explicit Windows diagnostic: read one public page; never download a full video.

Usage: python tests/probe_site_native.py URL --output build/site-probe.json
Only counts, document/frame URLs without query strings, and metadata are saved.
Request headers, cookies and media URLs are never printed or written.
"""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit,urlunsplit,urljoin
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))


def clean_url(value):
    parsed=urlsplit(str(value or ''))
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,'',''))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('url');parser.add_argument('--output',default='build/site-probe.json')
    parser.add_argument('--metadata',action='store_true')
    parser.add_argument('--audit-inline',action='store_true',help='Diagnostic only: save bounded public iframe script text locally and stop; not an acceptance test.')
    parser.add_argument('--test-play-cover',action='store_true',help='Diagnostic only: use normal input on a sole visible Oynat or enabled Reklamı geç button, never links or verification controls.')
    parser.add_argument('--visible',action='store_true')
    parser.add_argument('--browser-transport',action='store_true',help='Diagnostic only: use available yt-dlp Chrome-compatible HTTP transport.')
    parser.add_argument('--continue-in-browser',action='store_true')
    parser.add_argument('--human-check',action='store_true',help='Keep the visible test browser available for normal human verification, up to twenty minutes.')
    parser.add_argument('--sample',action='store_true',help='Read at most 16 KiB from one HLS/DASH/direct media sample; never save media.')
    args=parser.parse_args()
    if args.sample and not args.metadata:parser.error('--sample requires --metadata')
    import webview
    from services import media_discovery
    from services.generic_resolver import GenericResolver
    from services.site_browser import site_browser,BrowserRequired
    if not media_discovery.public_url(args.url,resolve=True):parser.error('Use a public HTTP/HTTPS URL.')
    report={'page':clean_url(args.url),'snapshots':[]}
    original_choose=media_discovery.choose_media
    def observe(snapshot,network=()):
        report['snapshots'].append({'document':clean_url(snapshot.get('url')),'ready':snapshot.get('ready'),'visibility':snapshot.get('visibility'),
            'frames':[dict(f,url=clean_url(f.get('url'))) for f in snapshot.get('raw_frames',[])],
            'embeds':len(snapshot.get('embeds',[])),'players':len(snapshot.get('media',[])),
            'network_media':len(network),'interaction':snapshot.get('interaction')})
        from services.network_media import media_kind
        kinds=[media_kind(item.get('url',''),item.get('mime',''),item.get('status')) for item in network]
        report['snapshots'][-1]['network_kinds']={kind:kinds.count(kind) for kind in ('hls','dash','file')}
        player_sources={source for item in snapshot.get('media',[]) for source in item.get('sources',[])}
        report['snapshots'][-1]['variant_edges']=sum(len(item.get('variants') or []) for item in network)
        report['snapshots'][-1]['network_exact_matches']=sum(item.get('url') in player_sources for item in network)
        report['snapshots'][-1]['player_areas']=[item.get('area',0) for item in snapshot.get('media',[])]
        relations=(site_browser.session or {}).get('manifest_relations')
        if relations:report['snapshots'][-1]['manifest_evidence']=dict(relations.statistics)
        report['snapshots'][-1]['verification']=bool(snapshot.get('verification'))
        report['snapshots'][-1]['outline']=snapshot.get('outline',{})
        report['snapshots'][-1]['groups']=[{'kind':item.get('group'),'duration':item.get('duration'),'blob':item.get('blob')} for item in snapshot.get('media',[])]
        probe=(site_browser.session or {}).get('frame_probe')
        if probe:
            report['snapshots'][-1]['native_request_count']=len(probe.requests)
            report['snapshots'][-1]['opaque_response_types']=[{'mime':v.get('mime'),'type':v.get('resource_type')} for v in probe.opaque_responses.values()]
            report['snapshots'][-1]['opaque_body_reads']=len(probe.opaque_body_requests)
            report['snapshots'][-1]['opaque_body_diagnostics']=list(probe.opaque_body_diagnostics)
            report['snapshots'][-1]['failed_response_counts']=list(probe.response_failures)
            report['snapshots'][-1]['frame_documents']=[clean_url((entry.get('snapshot') or {}).get('url')) for entry in probe.frames.values() if entry.get('snapshot')]
            report['snapshots'][-1]['frame_states']=[{'document':clean_url((entry.get('snapshot') or {}).get('url')),'outline':(entry.get('snapshot') or {}).get('outline',{}),'verification':(entry.get('snapshot') or {}).get('verification'),'players':len((entry.get('snapshot') or {}).get('media',[]))} for entry in probe.frames.values() if entry.get('snapshot')]
            report['snapshots'][-1]['media_header_names']=sorted({name for item in snapshot.get('media',[]) for source in item.get('sources',[]) for name in probe.requests.get(source,{})})
        if args.audit_inline and probe and probe.frames:
            records=probe.read('''(() => ({url:location.href,inline:[...document.scripts].filter(s=>!s.src).map(s=>s.textContent.slice(0,120000)).filter(Boolean).slice(0,6)}))()''')
            if any((r.get('snapshot') or {}).get('inline') for r in records):
                Path(args.output).with_suffix('.inline.json').write_text(json.dumps(records,ensure_ascii=True),encoding='utf-8')
                report['inline_audited']=True
                raise ValueError('Bounded public iframe script audit completed; not a source acceptance test.')
        if args.human_check:
            # Small live checkpoint for human-assisted tests, no credentials/media URLs.
            progress=Path(args.output).with_suffix('.progress.json')
            progress.write_text(json.dumps(report['snapshots'][-1],ensure_ascii=True),encoding='utf-8')
        if args.test_play_cover and not snapshot.get('verification'):
            session=site_browser.session or {}
            if session.get('window') and session.get('_test_play_clicks',0)<8:
                clicked=session['window'].evaluate_js('''(() => {const buttons=[...document.querySelectorAll('button')].filter(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);const play=e.getAttribute('aria-label')==='Oynat' && r.width>=100 && r.height>=60;const skip=(e.textContent||'').trim()==='Reklamı geç' && r.width>=20 && r.height>=20;return (play||skip) && !e.disabled && Date.now()-Number(e.getAttribute('data-vdp-test-play')||0)>3000 && s.display!=='none' && s.visibility!=='hidden' && !e.closest('a[href],form')});if(buttons.length!==1)return false;buttons[0].scrollIntoView({block:'center'});const r=buttons[0].getBoundingClientRect();buttons[0].setAttribute('data-vdp-test-play',String(Date.now()));return {x:r.left+r.width/2,y:r.top+r.height/2}})()''')
                if isinstance(clicked,dict) and probe and probe.active:
                    from System import Func,Object
                    def send_test_input():
                        core=probe.control.CoreWebView2
                        for kind in ('mousePressed','mouseReleased'):
                            core.CallDevToolsProtocolMethodAsync('Input.dispatchMouseEvent',json.dumps({'type':kind,'x':clicked['x'],'y':clicked['y'],'button':'left','clickCount':1}))
                    probe.control.Invoke(Func[Object](send_test_input))
                    session['_test_play_clicks']=session.get('_test_play_clicks',0)+1

        selected=original_choose(snapshot,network)
        if selected:report['discovery_method']=selected.get('discovery_method','dom')
        return selected
    snapshot=media_discovery.DISCOVERY_SNAPSHOT.replace('return {title:', '''return {ready:document.readyState,visibility:document.visibilityState,
      outline:{title:document.title,verification_state:{turnstile_response:Boolean(document.querySelector('input[name="cf-turnstile-response"]')?.value),captcha_frames:document.querySelectorAll('iframe[src*="challenges.cloudflare"]').length},body_excerpt:(document.body?.innerText||'').slice(0,3500),play_gates:[...document.querySelectorAll('button,[role="button"]')].filter(e=>/^(play|oynat)/i.test(e.getAttribute('aria-label')||e.textContent||'')).slice(0,8).map(e=>({label:(e.getAttribute('aria-label')||e.textContent||'').trim().slice(0,90),started:e.hasAttribute('data-vdp-started'),rect:{w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height},ancestors:(()=>{let a=e.parentElement,r=[];for(let i=0;a&&i<4;i++,a=a.parentElement)r.push({tag:a.tagName,classes:String(a.className).slice(0,80),frames:a.querySelectorAll('iframe').length,w:a.getBoundingClientRect().width,h:a.getBoundingClientRect().height});return r})()})),scripts:[...document.scripts].map(e=>e.src).filter(Boolean).map(v=>{const u=new URL(v);return u.origin+u.pathname}).slice(0,20),
      player_structure:[...document.querySelectorAll('.player-container,.player-container *')].slice(0,40).map(e=>({tag:e.tagName,classes:String(e.className).slice(0,120),attributes:e.getAttributeNames(),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height})),
      controls:[...document.querySelectorAll('button,[role="button"],[class*="player"],[id*="player"]')].slice(0,40).map(e=>({tag:e.tagName,id:e.id,classes:String(e.className).slice(0,120),label:(e.getAttribute('aria-label')||e.textContent||'').trim().slice(0,80)}))},
      raw_frames:[...document.querySelectorAll('iframe')].map(f=>({url:f.src,width:f.getBoundingClientRect().width,height:f.getBoundingClientRect().height})),title:''')
    main_window=webview.create_window('Isolated public-page source diagnostic',html='<html>Video source diagnostic. This window closes when the check finishes.</html>',hidden=args.human_check or not args.continue_in_browser,width=620,height=240)
    site_browser.enabled=True
    def run():
        try:
            create=webview.create_window
            def create_probe(*window_args,**kwargs):
                if window_args and 'Kaynak inceleme' in window_args[0]:
                    if parser_args_visible:
                        kwargs['hidden']=False;kwargs['focus']=True
                        if site_browser.session:site_browser.session['shown']=True
                    if args.human_check:window_args=(window_args[0]+' - '+urlsplit(args.url).hostname,*window_args[1:])
                return create(*window_args,**kwargs)
            parser_args_visible=args.visible
            with patch('webview.create_window',side_effect=create_probe),patch.object(media_discovery,'choose_media',side_effect=observe),patch.object(media_discovery,'DISCOVERY_SNAPSHOT',snapshot):
                resolver=GenericResolver(browser=site_browser)
                for attempt in range(70 if args.human_check else 4):
                    try:
                        data=resolver.details(args.url)
                        break
                    except BrowserRequired as interaction:
                        if not args.continue_in_browser or attempt==(69 if args.human_check else 3):raise
                        if not report.get('continued_in_browser'):
                            report['continued_in_browser']=True
                            site_browser.show(interaction.token)
                            if args.human_check:
                                import threading
                                session=site_browser.session
                                if session and session.get('timer'):session['timer'].cancel()
                                timer=threading.Timer(1200,lambda token=interaction.token:site_browser.close(token))
                                timer.daemon=True;session['timer']=timer;timer.start()
                        report['continue_checks']=attempt+1
                report.update(content_scope=data.get('content_scope','unknown'),status='resolved',discovery_status='resolved',title=data['title'],source_count=len(data['streams']))
                report.setdefault('discovery_method',data.get('discovery_method','unknown'))
                report['contexts']=[{'host':urlsplit(source).hostname,'headers':sorted(headers),'referer_host':urlsplit(headers.get('Referer','')).hostname}
                    for source,headers in data.get('source_headers',{}).items()]
                if args.metadata:
                    from yt_dlp import YoutubeDL
                    class QuietLog:
                        def debug(self,*args):pass
                        def warning(self,*args):pass
                        def error(self,*args):pass
                    options={'quiet':True,'no_warnings':True,'logger':QuietLog(),'socket_timeout':15}
                    if args.browser_transport:
                        from yt_dlp.networking.impersonate import ImpersonateTarget
                        options['impersonate']=ImpersonateTarget.from_str('chrome')
                    with YoutubeDL(options) as ydl:
                        info=resolver.extract(ydl,args.url)
                        report.update(source_status=info.get('source_status','unknown'),source_available_bytes=info.get('source_available_bytes'),source_declared_bytes=info.get('source_declared_bytes'),metadata_status='passed',duration=info.get('duration'),heights=sorted({f['height'] for f in info.get('formats',[]) if f.get('height')}),format_count=len(info.get('formats',[])))
                        if args.sample:
                            from probe_media_sample import sample_media
                            from services.diagnostics import error_code
                            try:
                                try:report.update(sample_media(ydl,info))
                                except Exception as first_sample_error:
                                    from services.browser_transport import enable_browser_transport
                                    if not enable_browser_transport(ydl,data['streams'][0],first_sample_error):raise
                                    report['sample_browser_retry']=True
                                    report.update(sample_media(ydl,info))
                            except Exception as sample_error:
                                report.update(sample_status='failed',sample_error_code=error_code(sample_error),sample_error_kind=type(sample_error).__name__)
                                if isinstance(sample_error,ValueError) and str(sample_error) in ('Encrypted sample not inspected','DASH format has no parsed fragments','No unprotected video format to sample','No fragment URL to sample','Manifest exceeds diagnostic budget'):
                                    report['sample_detail']=str(sample_error)
                                    if str(sample_error)=='Encrypted sample not inspected':report.update(sample_status='not_tested',sample_error_code=None)
                    report.update(duration=info.get('duration'),heights=sorted({f['height'] for f in info.get('formats',[]) if f.get('height')}),format_count=len(info.get('formats',[])))
        except BrowserRequired:
            report['status']='interaction_required'
        except Exception as exc:
            import re
            message=re.sub(r'https?://\S+','[remote URL]',str(exc))
            message=re.sub(r'\?[^\s:]+','?[redacted]',message)
            report.update(status='failed',error=message[:300])
        finally:
            site_browser.close();main_window.destroy()
    webview.start(run,gui='edgechromium',private_mode=True)
    Path(args.output).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=True))
    return 0 if report.get('status')=='resolved' else 1


if __name__=='__main__':raise SystemExit(main())
