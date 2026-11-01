"""Sequential public-page checks with isolated profiles and resumable safe reports."""
import argparse
import hashlib
from datetime import datetime, timezone
import json, os, re, subprocess, sys, tempfile, time
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from services.diagnostics import error_code, source_identity


def summarize(case,raw,seconds,engine='generic'):
    status=raw.get('status')
    outcome='automatic' if status in ('resolved','success') else 'interaction_required' if status in ('interaction_required','browser_required') else 'failed'
    groups=sorted({g.get('kind') for s in raw.get('snapshots',[]) for g in s.get('groups',[]) if g.get('kind')})
    result={'id':case['id'],'host':source_identity(case['url'])[0],'scenario':case.get('scenario','unspecified'),
        'player_family':case.get('player_family','unclassified'),'category':case.get('category','previous-regression'),
        'engine':engine,'outcome':outcome,'seconds':round(seconds,1),
        'error_code':(raw.get('error_code') or error_code(raw.get('error',''))) if outcome=='failed' else None,
        'discovery_resolved':raw.get('discovery_status')=='resolved' or outcome=='automatic',
        'source_count':raw.get('source_count',0),'format_count':raw.get('format_count',0),
        'discovery_method':raw.get('discovery_method','unknown'),'observed_player_groups':groups,
        'heights':raw.get('heights',[]),'qualities':raw.get('qualities',[]),'duration':raw.get('duration'),
        'sample_status':raw.get('sample_status','not_tested'),'sample_kind':raw.get('sample_kind'),
        'sample_error_code':raw.get('sample_error_code'),'sample_error_kind':raw.get('sample_error_kind'),'sample_detail':raw.get('sample_detail'),'sample_bytes':raw.get('sample_bytes',0),
        'sample_http_status':raw.get('sample_http_status'),'full_download':'not_tested'}
    return result


def stop_tree(process):
    try: children=psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess: children=[]
    for child in reversed(children):
        try:child.terminate()
        except psutil.NoSuchProcess:pass
    if process.poll() is None:process.terminate()
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
    _,alive=psutil.wait_procs(children,timeout=3)
    for child in alive:
        try:child.kill()
        except psutil.NoSuchProcess:pass


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',default=str(ROOT/'tests/site_matrix.json'))
    parser.add_argument('--all',action='store_true');parser.add_argument('--sample',action='store_true')
    parser.add_argument('--case',action='append',default=[]);parser.add_argument('--timeout',type=int,default=90)
    parser.add_argument('--engine',choices=['generic','app'],default='generic')
    parser.add_argument('--output',default=str(ROOT/'build/site-matrix-latest.json'))
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    if not args.all and not args.case:parser.error('Choose --all or --case ID explicitly.')
    if not 20<=args.timeout<=180:parser.error('Timeout must be 20–180 seconds per page.')
    if args.engine=='app' and args.sample:parser.error('App API checks metadata only; run generic sampling separately.')
    cases=json.loads(Path(args.manifest).read_text(encoding='utf-8'))['cases'];ids=[case['id'] for case in cases]
    if len(set(ids))!=len(ids) or any(not re.fullmatch(r'[a-z0-9-]{1,64}',value) for value in ids):parser.error('Invalid/duplicate case IDs.')
    if set(args.case)-set(ids):parser.error('Unknown case ID.')
    cases=[c for c in cases if args.all or c['id'] in args.case]
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    results=[]
    if args.resume and output.exists():
        saved=json.loads(output.read_text(encoding='utf-8'))
        if saved.get('engine')!=args.engine or saved.get('sampling')!=args.sample:parser.error('Existing report configuration differs.')
        results=saved['cases']
    completed={r['id'] for r in results}
    def save():
        source_hash=hashlib.sha256()
        for name in ['network_media.py','site_browser.py','webview_frames.py','manifest_relations.py','browser_transport.py','site_resolver.py','generic_resolver.py','media_discovery.py','player_activation.py','player_controls.py','poster_navigation.py']:
            source=ROOT/'src/services'/name
            source_hash.update(source.read_bytes() if source.exists() else b'absent')
        report={'source_fingerprint':source_hash.hexdigest(),'created_at':datetime.now(timezone.utc).isoformat(),'engine':args.engine,'sampling':args.sample,
            'scope':'Public page discovery and metadata; explicit sample reads limited to 16 KiB per page; full downloads not tested. Browser playback may buffer additional media.',
            'planned_cases':len(cases),'cases':results,'totals':{k:sum(r['outcome']==k for r in results) for k in ('automatic','interaction_required','failed')}}
        output.write_text(json.dumps(report,indent=2),encoding='utf-8')
        return report
    for case in cases:
        if case['id'] in completed:continue
        started=time.monotonic()
        with tempfile.TemporaryDirectory(prefix='site-matrix-',dir=ROOT/'build') as folder:
            folder=Path(folder);probe_output=folder/'probe.json'
            command=[sys.executable,str(ROOT/'tests'/('probe_app_info_native.py' if args.engine=='app' else 'probe_site_native.py')),case['url'],'--output',str(probe_output)]
            if args.engine=='generic':command.append('--metadata')
            if args.sample:command.append('--sample')
            env=dict(os.environ,VIDEO_DOWNLOADER_DATA_DIR=str(folder/'profile'))
            startup=None
            if os.name=='nt':
                startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
            with (folder/'probe-console.log').open('wb') as log:
                process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup)
                try:
                    process.wait(timeout=args.timeout)
                    raw=json.loads(probe_output.read_text(encoding='utf-8')) if probe_output.exists() else {'status':'failed','error':'probe failed'}
                except subprocess.TimeoutExpired:raw={'status':'failed','error':'timeout'}
                except (OSError,ValueError):raw={'status':'failed','error':'probe failed'}
                finally:stop_tree(process)
        result=summarize(case,raw,time.monotonic()-started,args.engine);results.append(result);save()
        print(f"{case['id']}: {result['outcome']} / sample={result['sample_status']} ({result['seconds']}s)",flush=True)
    print(json.dumps(save()['totals']));return 0

if __name__=='__main__':raise SystemExit(main())
