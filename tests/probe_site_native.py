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
    parser.add_argument('--visible',action='store_true')
    parser.add_argument('--continue-in-browser',action='store_true')
    parser.add_argument('--sample',action='store_true',help='Read at most 16 KiB of the first HLS segment; never save media.')
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
        report['snapshots'][-1]['groups']=[{'kind':item.get('group'),'duration':item.get('duration'),'blob':item.get('blob')} for item in snapshot.get('media',[])]
        probe=(site_browser.session or {}).get('frame_probe')
        if probe:
            report['snapshots'][-1]['native_request_count']=len(probe.requests)
            report['snapshots'][-1]['media_header_names']=sorted({name for item in snapshot.get('media',[]) for source in item.get('sources',[]) for name in probe.requests.get(source,{})})
        return original_choose(snapshot,network)
    snapshot=media_discovery.DISCOVERY_SNAPSHOT.replace('return {title:', '''return {ready:document.readyState,visibility:document.visibilityState,
      raw_frames:[...document.querySelectorAll('iframe')].map(f=>({url:f.src,width:f.getBoundingClientRect().width,height:f.getBoundingClientRect().height})),title:''')
    main_window=webview.create_window('Isolated public-page source diagnostic',html='<html>Video source diagnostic. This window closes when the check finishes.</html>',hidden=not args.continue_in_browser,width=620,height=240)
    site_browser.enabled=True
    def run():
        try:
            create=webview.create_window
            def create_probe(*args,**kwargs):
                if args and 'Kaynak inceleme' in args[0] and parser_args_visible:kwargs['hidden']=False
                return create(*args,**kwargs)
            parser_args_visible=args.visible
            with patch('webview.create_window',side_effect=create_probe),patch.object(media_discovery,'choose_media',side_effect=observe),patch.object(media_discovery,'DISCOVERY_SNAPSHOT',snapshot):
                resolver=GenericResolver(browser=site_browser)
                for attempt in range(4):
                    try:
                        data=resolver.details(args.url)
                        break
                    except BrowserRequired as interaction:
                        if not args.continue_in_browser or attempt==3:raise
                        if not report.get('continued_in_browser'):
                            report['continued_in_browser']=True
                            site_browser.show(interaction.token)
                        report['continue_checks']=attempt+1
                report.update(status='resolved',title=data['title'],source_count=len(data['streams']))
                report['contexts']=[{'host':urlsplit(source).hostname,'headers':sorted(headers),'referer_host':urlsplit(headers.get('Referer','')).hostname}
                    for source,headers in data.get('source_headers',{}).items()]
                if args.metadata:
                    from yt_dlp import YoutubeDL
                    class QuietLog:
                        def debug(self,*args):pass
                        def warning(self,*args):pass
                        def error(self,*args):pass
                    options={'quiet':True,'no_warnings':True,'logger':QuietLog(),'socket_timeout':15}
                    with YoutubeDL(options) as ydl:
                        info=resolver.extract(ydl,args.url)
                        if args.sample:
                            from yt_dlp.networking import Request
                            selected=(info.get('requested_formats') or [info])[0]
                            target=selected['url'];headers=selected.get('http_headers') or info.get('http_headers') or {}
                            for _ in range(3):
                                if not media_discovery.public_url(target,resolve=True):raise ValueError('Non-public sample URL')
                                with ydl.urlopen(Request(target,headers=headers)) as response:
                                    body=response.read(256*1024)
                                    final=response.url
                                if not body.lstrip().startswith(b'#EXTM3U'):raise ValueError('Sample requires an HLS source')
                                text=body.decode('utf-8-sig')
                                uri=next(line.strip() for line in text.splitlines() if line.strip() and not line.startswith('#'))
                                target=urljoin(final,uri)
                                if '#EXT-X-STREAM-INF' not in text:break
                            if not media_discovery.public_url(target,resolve=True):raise ValueError('Non-public segment URL')
                            with ydl.urlopen(Request(target,headers=dict(headers,Range='bytes=0-16383'))) as response:
                                sample=response.read(16384)
                                report.update(sample_bytes=len(sample),sample_http_status=response.status)
                            if not sample:raise ValueError('Empty segment sample')
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
