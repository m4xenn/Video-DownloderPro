"""Chrome/Edge stdio native host. Never writes logs to stdout."""
import json,os,sys,struct
from pathlib import Path
from urllib.request import Request,urlopen,build_opener,ProxyHandler

def run():
    if os.name=='nt':
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY);msvcrt.setmode(sys.stdout.fileno(),os.O_BINARY)
    opener=build_opener(ProxyHandler({}))
    while True:
        header=sys.stdin.buffer.read(4)
        if not header:return
        if len(header)!=4:return
        n=struct.unpack('<I',header)[0]
        if not 0<n<=65536:return
        raw=sys.stdin.buffer.read(n)
        if len(raw)!=n:return
        try:
            cfg=json.loads((Path(os.environ['APPDATA'])/'YoutubePro/extension-endpoint.json').read_text())
            port=int(cfg['port'])
            if not 1<=port<=65535:raise ValueError()
            req=Request(f'http://127.0.0.1:{port}/exchange',data=raw,headers={'Authorization':'Bearer '+cfg['token'],'Content-Type':'application/json'})
            with opener.open(req,timeout=3) as r:result=json.loads(r.read(65536))
        except Exception:result={'error':'app_unavailable','jobs':[]}
        data=json.dumps(result).encode();sys.stdout.buffer.write(struct.pack('<I',len(data))+data);sys.stdout.buffer.flush()
if __name__=='__main__':run()
