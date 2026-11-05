"""Actual yt-dlp remuxer and ffprobe contract, with generated HDR/SDR media."""
import json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from services import media_process
from services.media_quality import verify_quality
from yt_dlp import YoutubeDL
from yt_dlp.postprocessor.ffmpeg import FFmpegVideoRemuxerPP


class QualityRemuxTests(unittest.TestCase):
 def test_hdr_ten_bit_vp9_packets_fps_and_colour_survive_mp4_and_mkv(self):
  binary=Path(os.environ['APPDATA'])/'YoutubePro/bin'
  with tempfile.TemporaryDirectory(dir=ROOT/'build') as temporary:
   base=Path(temporary)
   from services.windows_sandbox import protect_workspace
   protect_workspace(base)
   def packets(path):
    result=media_process.run([str(binary/'ffprobe.exe'),'-v','error','-select_streams','v:0','-show_packets','-show_data_hash','sha256','-show_entries','packet=data_hash','-of','csv=p=0',str(path)],capture_output=True,check=True,timeout=20)
    return result.stdout.splitlines()
   for container in ['mp4','mkv']:
    with self.subTest(container=container):
     source=base/(container+'.webm')
     media_process.run([str(binary/'ffmpeg.exe'),'-v','error','-f','lavfi','-i','testsrc2=s=160x90:r=60000/1001','-t','1','-vf','format=yuv420p10le,setparams=range=limited:color_primaries=bt2020:color_trc=smpte2084:colorspace=bt2020nc',
      '-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','8','-pix_fmt','yuv420p10le','-color_primaries','bt2020','-color_trc','smpte2084','-colorspace','bt2020nc',str(source)],capture_output=True,check=True,timeout=60)
     before=packets(source)
     with YoutubeDL({'quiet':True,'ffmpeg_location':str(binary)}) as ydl:
      old,info=FFmpegVideoRemuxerPP(ydl,preferedformat=container).run({'filepath':str(source),'ext':'webm'})
     output=Path(info['filepath']);self.assertEqual(output.suffix,'.'+container)
     self.assertEqual(before,packets(output));self.assertTrue(source.is_file())
     summary=verify_quality(output,binary,{'vcodec':'vp09','width':160,'height':90,'fps':60000/1001,'dynamic_range':'HDR10'},{'format':'video','quality':'max'})
     self.assertIn('hdr',summary['verified_fields']);self.assertIn('fps',summary['verified_fields']);self.assertEqual(summary['actual']['pix_fmt'],'yuv420p10le')

if __name__=='__main__':unittest.main()
