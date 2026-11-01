"""Bounded HLS master/rendition evidence for already observed media responses."""
import re,time
from urllib.parse import urljoin
import requests

MAX_MANIFEST_BYTES=96*1024


def variant_links(url,body):
    if len(body)>MAX_MANIFEST_BYTES:return []
    text=body.decode('utf-8-sig',errors='replace')
    if not text.lstrip().startswith('#EXTM3U'):return []
    links=[];pending=False
    for line in text.splitlines()[:2000]:
        line=line.strip()
        if line.startswith('#EXT-X-STREAM-INF:'):pending=True
        elif line.startswith(('#EXT-X-MEDIA:','#EXT-X-I-FRAME-STREAM-INF:')):
            # Alternate audio/video/subtitles and trick-play playlists belong
            # to this presentation only when the master explicitly references them.
            if line.startswith('#EXT-X-MEDIA:') and not re.search(r'(?:^|,)TYPE=(?:AUDIO|VIDEO|SUBTITLES)(?:,|$)',line.split(':',1)[1]):continue
            match=re.search(r'(?:^|,)URI="([^"\r\n]+)"',line.split(':',1)[1])
            if match:links.append(urljoin(url,match[1]))
        elif line and not line.startswith('#'):
            if pending:links.append(urljoin(url,line))
            pending=False
    return list(dict.fromkeys(links))[:32]


def verified_hls_root(sources):
    """Only collapse observed HLS URLs explicitly linked by a fetched master."""
    if len(sources)<2 or any(item.get('kind')!='hls' for item in sources.values()):return None
    nodes=set(sources)
    edges={url:set(item.get('variants') or []) & nodes for url,item in sources.items()}
    incoming={node:0 for node in nodes}
    for children in edges.values():
        for child in children:incoming[child]+=1
    ready=[node for node,count in incoming.items() if count==0];visited=0
    while ready:
        node=ready.pop();visited+=1
        for child in edges[node]:
            incoming[child]-=1
            if incoming[child]==0:ready.append(child)
    if visited!=len(nodes):return None
    roots=[]
    for root in nodes:
        reached=set();pending=[root]
        while pending:
            node=pending.pop()
            if node in reached:continue
            reached.add(node);pending.extend(edges[node]-reached)
        if reached==nodes:roots.append(root)
    # A cycle or competing independent roots never establishes a canonical master.
    return roots[0] if len(roots)==1 else None


class ManifestRelations:
    def __init__(self,fetch=None,clock=time.monotonic):
        self.fetch=fetch or requests.get;self.clock=clock;self.links={};self.attempted=set();self.elapsed=0;self.statistics={}

    def record(self,key):
        self.statistics[key]=self.statistics.get(key,0)+1

    def enrich(self,responses):
        from services.network_media import media_kind
        from services.media_discovery import public_url
        unique={r.get('url'):r for r in responses if media_kind(r.get('url',''),r.get('mime'),r.get('status'))=='hls'}
        if len(unique)>1:
            for url,record in unique.items():
                if record.get('variants'):
                    self.links[url]=list(record['variants']);continue
                if url in self.attempted or len(self.attempted)>=6 or self.elapsed>=3:continue
                self.attempted.add(url);started=self.clock()
                try:
                    if not public_url(url,resolve=True):continue
                    # Exact observed URL only; never forward captured credentials through a redirect.
                    headers={k:str(v) for k,v in (record.get('headers') or {}).items() if k.lower() in ('referer','origin','user-agent','cookie')}
                    timeout=max(.1,min(.8,3-self.elapsed))
                    with self.fetch(url,headers=headers,timeout=(timeout,timeout),stream=True,allow_redirects=False) as response:
                        if response.status_code!=200:
                            self.record('http_'+str(response.status_code));continue
                        mime=response.headers.get('Content-Type','').split(';')[0].lower()
                        if mime in ('text/html','application/json','application/xhtml+xml'):
                            self.record('non_manifest_response');continue
                        body=bytearray()
                        for chunk in response.iter_content(8192):
                            body.extend(chunk)
                            if len(body)>MAX_MANIFEST_BYTES or self.clock()-started>1.5:break
                        else:
                            self.links[url]=[child for child in variant_links(url,bytes(body)) if public_url(child)]
                            self.record('master_parsed' if self.links[url] else 'no_variant_links')
                except (requests.RequestException,OSError,ValueError) as error:self.record(type(error).__name__)
                finally:self.elapsed+=self.clock()-started
        return [dict(record,variants=record.get('variants') or self.links.get(record.get('url'),[])) for record in responses]
