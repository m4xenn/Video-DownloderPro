"""Bounded HLS metadata and protection evidence. Never requests keys or licenses."""
import re,math

MAX_MANIFEST_BYTES=2*1024*1024
SYSTEMS={
 'com.apple.streamingkeydelivery':'FairPlay',
 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed':'Widevine',
 'com.widevine':'Widevine',
 'com.widevine.alpha':'Widevine',
 'com.microsoft.playready':'PlayReady',
 'urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95':'PlayReady',
}
class ProtectedMediaError(ValueError):
 code='drm'
 def __init__(self,systems):super().__init__('DRM protected media: '+', '.join(sorted(systems)))
class UnsupportedEncryptionError(ValueError):
 code='encrypted_unsupported'
 def __init__(self):super().__init__('[encrypted_unsupported] Encrypted media scheme unsupported; DRM not established.')

def attributes(line):
 return {m[1]:m[2].strip('"') for m in re.finditer(r'([A-Z0-9-]+)=("[^"\r\n]*"|[^,\r\n]*)',line)}

def inspect_hls(body):
 if isinstance(body,bytes):
  if len(body)>MAX_MANIFEST_BYTES:raise ValueError('HLS manifest exceeds metadata limit')
  text=body.decode('utf-8-sig')
 elif isinstance(body,str):text=body
 else:raise ValueError('Invalid HLS manifest')
 if len(text)>MAX_MANIFEST_BYTES:raise ValueError('HLS manifest exceeds metadata limit')
 lines=text.lstrip('\ufeff').strip().splitlines()
 if not lines or lines[0].strip()!='#EXTM3U':raise ValueError('Invalid HLS manifest; source could not be validated')
 systems=set();methods=set();unknown=False;duration=0.;segments=0;ended=False;master=False;audio=0;subtitles=0
 for raw in lines:
  line=raw.strip()
  if line.startswith(('#EXT-X-KEY:','#EXT-X-SESSION-KEY:')):
   a=attributes(line.split(':',1)[1]);method=a.get('METHOD','').upper();keyformat=a.get('KEYFORMAT','identity').lower()
   if method=='NONE':continue
   methods.add(method)
   if keyformat in SYSTEMS:systems.add(SYSTEMS[keyformat])
   elif a.get('URI','').lower().startswith('skd:'):systems.add('FairPlay')
   elif keyformat!='identity' or method!='AES-128':unknown=True
  elif line.startswith('#EXTINF:'):
   try:value=float(line.split(':',1)[1].split(',')[0])
   except ValueError:raise ValueError('Invalid HLS segment duration')
   if not math.isfinite(value) or value<0:raise ValueError('Invalid HLS segment duration')
   duration+=value;segments+=1
  elif line=='#EXT-X-ENDLIST':ended=True
  elif line.startswith('#EXT-X-STREAM-INF:'):master=True
  elif line.startswith('#EXT-X-MEDIA:'):
   kind=attributes(line.split(':',1)[1]).get('TYPE');audio+=kind=='AUDIO';subtitles+=kind=='SUBTITLES'
 protection='drm' if systems else 'unknown' if unknown else 'aes128' if methods else 'clear'
 return {'protection':protection,'systems':sorted(systems),'duration':duration if ended and segments and not master else None,
         'is_live':not ended and segments>0 and not master,'master':master,'audio_tracks':audio,'subtitle_tracks':subtitles}

def extract_hls(ydl,url,identity,title):
 from yt_dlp.networking import Request
 from yt_dlp.extractor.generic import GenericIE
 from services.media_discovery import public_url
 if not public_url(url,resolve=True):raise ValueError('Non-public HLS source')
 headers=dict(ydl.params.get('http_headers') or {})
 with ydl.urlopen(Request(url,headers=headers)) as response:
  if not public_url(response.url,resolve=True):raise ValueError('Non-public HLS redirect')
  body=response.read(MAX_MANIFEST_BYTES+1);final=response.url
 evidence=inspect_hls(body)
 if evidence['protection']=='drm':raise ProtectedMediaError(evidence['systems'])
 if evidence['protection']=='unknown':raise UnsupportedEncryptionError()
 formats,subtitles=GenericIE(ydl)._parse_m3u8_formats_and_subtitles(body.decode('utf-8-sig'),final,video_id=identity,ext='mp4',m3u8_id='hls',headers=headers)
 children=[];seen={final}
 for fmt in formats[-8:]:
  child=fmt.get('url')
  if not child or child in seen:continue
  seen.add(child)
  if not public_url(child,resolve=True):raise ValueError('Non-public HLS rendition')
  with ydl.urlopen(Request(child,headers=headers)) as response:
   if not public_url(response.url,resolve=True):raise ValueError('Non-public HLS rendition redirect')
   child_evidence=inspect_hls(response.read(MAX_MANIFEST_BYTES+1))
  if child_evidence['protection']=='drm':raise ProtectedMediaError(child_evidence['systems'])
  if child_evidence['protection']=='unknown':raise UnsupportedEncryptionError()
  children.append(child_evidence)
 if children:
  evidence['is_live']=any(c['is_live'] for c in children)
  durations=[c['duration'] for c in children if c['duration'] is not None]
  if durations and not evidence['is_live']:evidence['duration']=max(durations)
  if any(c['protection']=='aes128' for c in children):evidence['protection']='aes128'
  evidence['renditions_checked']=len(children)
 return {'id':identity,'title':title,'formats':formats,'subtitles':subtitles,'duration':evidence['duration'],
         'is_live':evidence['is_live'],'_hls_evidence':evidence}
