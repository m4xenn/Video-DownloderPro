"""Real local HLS audio/video/subtitle and ordinary AES-128 acceptance; no DRM licenses."""
import functools,http.server,json,os,pathlib,subprocess,sys,tempfile,threading,unittest
from unittest.mock import Mock,patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from yt_dlp import YoutubeDL
from services.generic_resolver import GenericResolver
from services.hls_metadata import ProtectedMediaError
from core.format_resolver import get_ydl_opts
class HlsCompatibilityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.ffmpeg=pathlib.Path(os.environ['APPDATA'])/'YoutubePro/bin/ffmpeg.exe'
  if not cls.ffmpeg.is_file():raise unittest.SkipTest('Local FFmpeg component required')
  cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='hls-compat-');cls.base=pathlib.Path(cls.temp.name)
  from services.windows_sandbox import protect_workspace
  protect_workspace(cls.base)
  for name in ('v','a','tr','s','enc','fmp4','dash','rotate'): (cls.base/name).mkdir()
  def ff(args):
   args=list(args);cwd=None
   if 'dash' in args:
    destination=pathlib.Path(args[-1]);cwd=destination.parent;args[-1]=destination.name
   subprocess.run([str(cls.ffmpeg),'-hide_banner','-loglevel','error','-y',*args],cwd=cwd,check=True,timeout=35)
  ff(['-f','lavfi','-i','testsrc2=s=640x360:r=10','-t','3','-an','-c:v','libx264','-preset','ultrafast','-g','10','-hls_time','1','-hls_playlist_type','vod',str(cls.base/'v/index.m3u8')])
  ff(['-f','lavfi','-i','sine=frequency=440','-t','3','-vn','-c:a','aac','-hls_time','1','-hls_playlist_type','vod',str(cls.base/'a/index.m3u8')])
  ff(['-f','lavfi','-i','sine=frequency=880','-t','3','-vn','-c:a','aac','-hls_time','1','-hls_playlist_type','vod',str(cls.base/'tr/index.m3u8')])
  (cls.base/'s/segment.vtt').write_text('WEBVTT\n\n00:00.000 --> 00:02.000\nSynthetic subtitle\n',encoding='utf-8')
  (cls.base/'s/index.m3u8').write_text('#EXTM3U\n#EXT-X-TARGETDURATION:3\n#EXTINF:3,\nsegment.vtt\n#EXT-X-ENDLIST\n')
  (cls.base/'video-only.m3u8').write_text('#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=640x360,CODECS="avc1.64001e"\nv/index.m3u8\n')
  (cls.base/'audio-only.m3u8').write_text('#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",NAME="English",LANGUAGE="en",DEFAULT=YES,URI="a/index.m3u8"\n')
  (cls.base/'master.m3u8').write_text('#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",NAME="English",LANGUAGE="en",DEFAULT=YES,AUTOSELECT=YES,URI="a/index.m3u8"\n#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="s",NAME="English",LANGUAGE="en",DEFAULT=YES,AUTOSELECT=YES,URI="s/index.m3u8"\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=640x360,CODECS="avc1.64001e,mp4a.40.2",AUDIO="a",SUBTITLES="s"\nv/index.m3u8\n')
  multilingual=(cls.base/'master.m3u8').read_text().replace('#EXT-X-STREAM-INF:', '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",NAME="Turkish",LANGUAGE="tr",DEFAULT=NO,AUTOSELECT=YES,URI="tr/index.m3u8"\n#EXT-X-STREAM-INF:')
  (cls.base/'multilingual.m3u8').write_text(multilingual)
  (cls.base/'enc/key.bin').write_bytes(bytes(range(16)))
  (cls.base/'enc/keyinfo').write_text('key.bin\n'+str(cls.base/'enc/key.bin')+'\n')
  ff(['-f','lavfi','-i','testsrc2=s=320x180:r=10','-f','lavfi','-i','sine=frequency=660','-t','3','-c:v','libx264','-preset','ultrafast','-g','10','-c:a','aac','-hls_time','1','-hls_playlist_type','vod','-hls_key_info_file',str(cls.base/'enc/keyinfo'),str(cls.base/'enc/index.m3u8')])
  ff(['-i',str(cls.base/'v/index.m3u8'),'-i',str(cls.base/'a/index.m3u8'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','ultrafast','-c:a','aac','-f','dash',str(cls.base/'dash/manifest.mpd')])
  ff(['-i',str(cls.base/'v/index.m3u8'),'-i',str(cls.base/'a/index.m3u8'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','ultrafast','-c:a','aac','-hls_time','1','-hls_segment_type','fmp4','-hls_flags','single_file','-hls_playlist_type','vod',str(cls.base/'fmp4/index.m3u8')])
  from yt_dlp.aes import aes_cbc_encrypt_bytes
  rotate=['#EXTM3U','#EXT-X-VERSION:3','#EXT-X-TARGETDURATION:2','#EXT-X-MEDIA-SEQUENCE:0']
  for i,segment in enumerate(sorted((cls.base/'v').glob('*.ts'))):
   key=bytes([i+1])*16;iv=i.to_bytes(16,'big');(cls.base/f'rotate/key{i}.bin').write_bytes(key)
   encrypted=aes_cbc_encrypt_bytes(segment.read_bytes(),key,iv)
   (cls.base/f'rotate/segment{i}.ts').write_bytes(encrypted)
   rotate.extend([f'#EXT-X-KEY:METHOD=AES-128,URI="key{i}.bin",IV=0x{iv.hex()}','#EXTINF:1,',f'segment{i}.ts'])
  rotate.append('#EXT-X-ENDLIST');(cls.base/'rotate/index.m3u8').write_text('\n'.join(rotate)+'\n')
  (cls.base/'protected.m3u8').write_text('#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,KEYFORMAT="com.widevine",URI="/should-not-contact-license"\n#EXTINF:3,\npayload.ts\n#EXT-X-ENDLIST\n')
  cls.requests=[]
  class Handler(http.server.SimpleHTTPRequestHandler):
   def log_message(self,*args):pass
   def send_error(self,code,*args,**kwargs):
    if code==404:print('Fixture missing:',self.path)
    return super().send_error(code,*args,**kwargs)
   def do_GET(self):cls.requests.append(self.path);super().do_GET()
  cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(cls.base)))
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.origin='http://127.0.0.1:'+str(cls.server.server_port)
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join(3);cls.temp.cleanup()
 def resolve_download(self,paths,name,subs=False,language="auto",subtitle="all"):
  resolver=GenericResolver();streams=[self.origin+p for p in paths]
  resolver.details=Mock(return_value={'stream':streams[0],'streams':streams,'source_types':{u:'dash' if u.endswith('.mpd') else 'hls' for u in streams},'headers':{},'title':'Synthetic HLS','thumbnail':''})
  opts=get_ydl_opts('video','auto',str(self.base),0,subs,lambda _:None,str(self.ffmpeg.parent))
  from services.track_selection import apply_tracks
  apply_tracks(opts,dict(audio_language=language,subtitle_language=subtitle,embed_subs=subs))
  opts.update(quiet=True,logger=Mock(),outtmpl=str(self.base/(name+'.%(ext)s')),ignoreerrors=False,skip_unavailable_fragments=False,fragment_retries=0,concurrent_fragment_downloads=1)
  with patch('services.media_discovery.public_url',return_value=True),YoutubeDL(opts) as ydl:
   from services.merge_recovery import attach_merge_recovery
   attach_merge_recovery(ydl,lambda:False)
   info=resolver.extract(ydl,'https://watch.example/fixture');ydl.process_ie_result(info,download=True)
  output=self.base/(name+'.mp4');self.assertTrue(output.is_file())
  details=json.loads(subprocess.check_output([str(self.ffmpeg.parent/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(output)]))
  return info,details['streams']
 def test_separate_video_audio_are_combined(self):
  info,streams=self.resolve_download(['/video-only.m3u8','/audio-only.m3u8'],'split')
  self.assertTrue(any(s['codec_type']=='video' and s['height']==360 for s in streams));self.assertTrue(any(s['codec_type']=='audio' for s in streams));self.assertEqual(len(info['requested_formats']),2)
 def test_master_audio_subtitle_embed(self):
  info,streams=self.resolve_download(['/master.m3u8'],'master-output',subs=True)
  self.assertTrue(any(s['codec_type']=='video' for s in streams));self.assertTrue(any(s['codec_type']=='audio' for s in streams));self.assertTrue(any(s['codec_type']=='subtitle' for s in streams));self.assertIn('en',info['subtitles'])
 def test_selected_hls_audio_language_and_subtitle_download(self):
  info,streams=self.resolve_download(['/multilingual.m3u8'],'turkish-output',subs=True,language='tr',subtitle='en')
  audio=next(f for f in info['requested_formats'] if f.get('acodec')!='none')
  self.assertEqual(audio['language'],'tr');self.assertIn('/tr/',audio['url'])
  self.assertTrue(any(s['codec_type']=='subtitle' for s in streams))
  self.assertTrue(any(s['codec_type']=='audio' for s in streams))
 def test_locked_merge_finishes_without_rerunning_ffmpeg(self):
  import ctypes
  from yt_dlp.postprocessor.ffmpeg import FFmpegMergerPP
  kernel=ctypes.WinDLL('kernel32',use_last_error=True)
  kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p];kernel.CreateFileW.restype=ctypes.c_void_p
  kernel.CloseHandle.argtypes=[ctypes.c_void_p]
  original=FFmpegMergerPP.run_ffmpeg_multiple_files;calls=[];timers=[]
  def locked(pp,inputs,output,*args,**kwargs):
   result=original(pp,inputs,output,*args,**kwargs);calls.append(output)
   handle=kernel.CreateFileW(str(output),0x80000000,1,None,3,0x80,None)
   self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
   timer=threading.Timer(.6,lambda:kernel.CloseHandle(handle));timers.append(timer);timer.start()
   return result
  try:
   with patch.object(FFmpegMergerPP,'run_ffmpeg_multiple_files',locked):
    info,streams=self.resolve_download(['/master.m3u8'],'locked-output')
   self.assertEqual(len(calls),1);self.assertTrue(any(s['codec_type']=='audio' for s in streams));self.assertTrue(any(s['codec_type']=='video' for s in streams))
  finally:
   for timer in timers:timer.join()
 def test_static_dash_separate_audio_video(self):
  info,streams=self.resolve_download(['/dash/manifest.mpd'],'dash-output')
  self.assertTrue(any(s['codec_type']=='video' for s in streams));self.assertTrue(any(s['codec_type']=='audio' for s in streams))
 def test_fmp4_hls_with_byte_ranges(self):
  info,streams=self.resolve_download(['/fmp4/index.m3u8'],'fmp4-output')
  self.assertTrue(any(s['codec_type']=='video' for s in streams));self.assertTrue(any(s['codec_type']=='audio' for s in streams))
 def test_rotating_publisher_aes128_keys(self):
  info,streams=self.resolve_download(['/rotate/index.m3u8'],'rotate-output')
  self.assertTrue(any(s['codec_type']=='video' for s in streams))
  self.assertTrue(all('/rotate/key'+str(i)+'.bin' in self.requests for i in range(3)))
 def test_ordinary_aes128_hls_download(self):
  info,streams=self.resolve_download(['/enc/index.m3u8'],'aes-output')
  self.assertEqual(info['_hls_evidence']['protection'],'aes128');self.assertAlmostEqual(info['duration'],3,places=1);self.assertTrue(any(s['codec_type']=='audio' for s in streams));self.assertTrue(any(s['codec_type']=='video' for s in streams))
 def test_drm_stops_before_license_or_media_requests(self):
  resolver=GenericResolver();url=self.origin+'/protected.m3u8';resolver.details=Mock(return_value={'stream':url,'source_types':{url:'hls'},'headers':{},'title':'Protected fixture','thumbnail':''})
  before=len(self.requests)
  with patch('services.media_discovery.public_url',return_value=True),YoutubeDL({'quiet':True,'logger':Mock()}) as ydl,self.assertRaises(ProtectedMediaError):resolver.extract(ydl,'https://watch.example/protected')
  self.assertEqual(self.requests[before:],['/protected.m3u8'])
if __name__=='__main__':unittest.main()
