"""Explicit, sequential public-page checks. No CAPTCHA solving or full downloads."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from services.diagnostics import error_code, source_identity


def summarize(case, raw, seconds):
    status = raw.get('status')
    outcome = {'resolved': 'automatic', 'interaction_required': 'interaction_required'}.get(status, 'failed')
    return {'id': case['id'], 'host': source_identity(case['url'])[0], 'scenario': case.get('scenario', 'unspecified'),
            'outcome': outcome, 'seconds': round(seconds, 1),
            'error_code': error_code(raw.get('error', '')) if outcome == 'failed' else None,
            'source_count': raw.get('source_count', 0), 'format_count': raw.get('format_count', 0),
            'discovery_method':raw.get('discovery_method','unknown'),
            'heights': raw.get('heights', []), 'duration': raw.get('duration'),
            'sample_bytes':raw.get('sample_bytes',0), 'sample_http_status':raw.get('sample_http_status'),
            'full_download': 'not_tested'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default=str(ROOT / 'tests/site_matrix.json'))
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--sample', action='store_true',help='Read at most 16 KiB from one HLS segment; never save media.')
    parser.add_argument('--case', action='append', default=[])
    parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--output', default=str(ROOT / 'build/site-matrix-latest.json'))
    args = parser.parse_args()
    if not args.all and not args.case: parser.error('Choose --all or --case ID explicitly.')
    if not 20 <= args.timeout <= 180: parser.error('Timeout must be 20–180 seconds per page.')
    cases = json.loads(Path(args.manifest).read_text(encoding='utf-8'))['cases']
    ids = [case['id'] for case in cases]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r'[a-z0-9-]{1,64}', value) for value in ids):
        parser.error('Case IDs must be unique lowercase identifiers.')
    if set(args.case) - set(ids): parser.error('Unknown case ID.')
    cases = [case for case in cases if args.all or case['id'] in args.case]
    results = []
    for case in cases:
        started = time.monotonic()
        # Raw probe output is temporary; only explicitly allowlisted fields are exported.
        with tempfile.TemporaryDirectory(prefix='site-matrix-') as folder:
            output = Path(folder) / 'probe.json'
            try:
                command=[sys.executable, str(ROOT / 'tests/probe_site_native.py'),case['url'], '--metadata', '--output', str(output)]
                if args.sample:command.append('--sample')
                run = subprocess.run(command, cwd=ROOT,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=args.timeout)
                raw = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {'status':'failed','error':'probe failed'}
            except subprocess.TimeoutExpired:
                raw = {'status':'failed','error':'timeout'}
            except (OSError, ValueError):
                raw = {'status':'failed','error':'probe failed'}
        result = summarize(case, raw, time.monotonic() - started)
        results.append(result)
        print(f"{case['id']}: {result['outcome']} ({result['seconds']}s)", flush=True)
    report = {'created_at':datetime.now(timezone.utc).isoformat(),
              'scope':'generic source discovery, metadata'+(', bounded HLS sample' if args.sample else '')+'; full downloads not tested', 'cases':results,
              'totals':{key:sum(item['outcome']==key for item in results) for key in ('automatic','interaction_required','failed')}}
    path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report['totals']))
    return 0


if __name__ == '__main__': raise SystemExit(main())
