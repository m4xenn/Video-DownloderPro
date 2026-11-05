"""Alternate two frozen packages, sequentially, with identical isolated profiles."""
import argparse,json,os,statistics,sys,time,types
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--before',required=True);parser.add_argument('--after',required=True);parser.add_argument('--runs',type=int,default=5);parser.add_argument('--inspect-url');parser.add_argument('--label',default='startup-comparison');parser.add_argument('--poll-ms',type=int,default=30)
 args=parser.parse_args();assert 1<=args.runs<=10
 assert args.label.replace('-','').isalnum() and 10<=args.poll_ms<=250
 folder=ROOT/'build/performance'/args.label;folder.mkdir(exist_ok=True)
 assert not (folder/'result.json').exists(),'Preserve previous measurements'
 assert not any((p.info['name'] or '').lower()=='youtubepro.exe' for p in psutil.process_iter(['name'])),'Do not interrupt an existing app'
 helper=types.ModuleType('startup_benchmark');helper.__file__=str(ROOT/'scripts/check_installed_runtime.py')
 code=Path(helper.__file__).read_text(encoding='utf-8')
 assert code.count('time.sleep(.25)')==1
 code=code.replace('time.sleep(.25)',f'time.sleep({args.poll_ms/1000})')
 exec(compile(code,helper.__file__,'exec'),helper.__dict__)
 result={'method':f'sequential alternating frozen API readiness, {args.poll_ms} ms polling; warm filesystem cache','before':[],'after':[],'inspection':{'before':[],'after':[]}}
 for i in range(args.runs):
  for name in (('before','after') if i%2==0 else ('after','before')):
   helper.EXE=Path(getattr(args,name)).resolve();helper.PROFILE=folder/name
   started=time.perf_counter();process,url=helper.launch()
   try:
    result[name].append(time.perf_counter()-started)
    if args.inspect_url:
     inspected=time.perf_counter();status,data=helper.api(url,'/get-info',{'url':args.inspect_url})
     assert status==200 and data['status']=='success',data
     result['inspection'][name].append(time.perf_counter()-inspected)
   finally:helper.stop(process)
   print(name,result[name][-1],flush=True)
 result['medians']={name:statistics.median(result[name]) for name in ('before','after')}
 (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result['medians']))
if __name__=='__main__':main()
