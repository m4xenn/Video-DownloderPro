"""Create a reviewable field report from sanitized probe outputs."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--date',default='2026-10-22');args=parser.parse_args()
base=ROOT/'build';date=args.date
manifest=json.loads((ROOT/'tests/site_matrix_extended.json').read_text(encoding='utf-8'))
generic=json.loads((base/f'field-test-{date}-generic.json').read_text(encoding='utf-8'))
app=json.loads((base/f'field-test-{date}-app.json').read_text(encoding='utf-8'))
by_generic={r['id']:r for r in generic['cases']};by_app={r['id']:r for r in app['cases']}
lines=[f'# Embedded-player field test — {date}','','## Method','',
'Public pages were tested using the current 1.3.0 source, isolated profiles and real Windows WebView2. Each runner visits one page at a time. Two independent passes compare the generic embedded resolver with the actual application `/get-info` flow. No existing browser session is imported. No CAPTCHA is solved and no DRM is removed.','',
'Generic probes read metadata and explicitly request no more than 16 KiB from one accessible HLS segment, parsed DASH fragment or direct media resource. Manifests are bounded to 256 KiB. Player startup may additionally buffer media inside WebView2; the 16 KiB limit applies to the explicit diagnostic sample, not total browser traffic. Samples are never saved. No full downloads, seek/resume, complete playback or long-running token expiry checks are performed.','',
'Player-family labels describe the intended test target. A redirected demo or source-selection form may no longer exercise that player. Observed generic groups are recorded separately; successful application extraction may use yt-dlp without the embedded-browser fallback. Counts describe this handpicked sample, not an internet-wide success rate.','',
'## Results','',
f"Generic metadata: {generic['totals']}. Application metadata: {app['totals']}.",'',
'| Case / public link | Intended family | Generic metadata | Observed groups | Quality heights | Media sample | Application metadata |',
'|---|---|---|---|---|---|---|']
for case in manifest['cases']:
 g=by_generic.get(case['id'],{});a=by_app.get(case['id'],{})
 def result(r):return r.get('outcome','pending')+((' / '+str(r['error_code'])) if r.get('error_code') else '')
 heights=', '.join(str(h)+'p' for h in g.get('heights',[])) or 'not reported'
 sample=g.get('sample_status','not_tested')
 if sample=='passed':sample+=f" / {g.get('sample_bytes',0)} B / {g.get('sample_kind')}"
 elif g.get('sample_error_code'):sample+=' / '+g['sample_error_code']
 elif g.get('sample_detail'):sample+=' / '+g['sample_detail']
 lines.append(f"| [{case['id']}]({case['url']}) | {case.get('player_family','Previous regression')} | {result(g)} | {', '.join(g.get('observed_player_groups',[])) or 'not observed'} | {heights} | {sample} | {result(a)} |")
lines+=['','## Reproduce','','```powershell',f'python scripts/site_matrix.py --manifest tests/site_matrix_extended.json --all --sample --timeout 75 --output build/field-test-{date}-generic.json',f'python scripts/site_matrix.py --manifest tests/site_matrix_extended.json --all --engine app --timeout 75 --output build/field-test-{date}-app.json',f'python scripts/render_field_report.py --date {date}','```','','Use `--case ID` for targeted checks and `--resume` to continue an interrupted report with identical engine/sampling options. Process trees are stopped on timeout. Raw probe output is temporary; persisted JSON exports only allowlisted fields and excludes cookies, request-header values and discovered media URLs.','']
output=ROOT/'docs/testing'/f'EMBEDDED_FIELD_TEST_{date}.md';output.write_text('\n'.join(lines),encoding='utf-8');print(output)
