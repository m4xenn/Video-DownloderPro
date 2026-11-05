import hashlib,os,sys,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from services.recording_sessions import build_exports,RecordingPartError,run_copy
from services.media_gate import staging_directory,publish
from services import media_process
from core.bandwidth import DownloadPaused


class RecordingSessionsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.bin=Path(os.environ['APPDATA'])/'YoutubePro/bin'
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'build');self.addCleanup(self.temp.cleanup)
  self.folder=Path(self.temp.name);self.identity=uuid.uuid4().hex
  self.stage=staging_directory(self.folder,self.identity)
  self.job=SimpleNamespace(id=self.identity,path=str(self.folder),recording_parts=[])
 def part(self,width=160,audio=True):
  path=self.stage/(uuid.uuid4().hex+'.mkv')
  args=[str(self.bin/'ffmpeg.exe'),'-v','error','-nostdin','-f','lavfi','-i',f'color=c=blue:s={width}x90:r=24']
  if audio:args+=['-f','lavfi','-i','sine=frequency=440:sample_rate=48000']
  args+=['-t','1','-c:v','libx264','-preset','ultrafast']
  if audio:args+=['-c:a','aac']
  media_process.run(args+[str(path)],capture_output=True,check=True,timeout=30)
  part={'id':uuid.uuid4().hex,'workspace':str(self.stage),'file':path.name,'bytes':path.stat().st_size,'state':'interrupted'}
  self.job.recording_parts.append(part)
  return path
 def packets(self,path):
  result=media_process.run([str(self.bin/'ffprobe.exe'),'-v','error','-show_packets','-show_data_hash','sha256','-show_entries','packet=stream_index,data_hash','-of','csv=p=0',str(path)],capture_output=True,check=True,timeout=15)
  return result.stdout.splitlines()
 def export(self,action='export',ack=False):
  saved=[]
  def commit(output,directory,identity,checked,summary):
   if checked is None:return None
   path=publish(output,self.folder,directory);saved.append((path,checked,summary));return identity
  build_exports(self.job,self.bin,action,ack,lambda *args:None,lambda:False,commit)
  return saved
 def test_export_preserves_encoded_packets_and_original_bytes(self):
  original=self.part();before=hashlib.sha256(original.read_bytes()).digest();packets=self.packets(original)
  saved=self.export()
  self.assertEqual(len(saved),1);self.assertEqual(packets,self.packets(saved[0][0]));self.assertEqual(before,hashlib.sha256(original.read_bytes()).digest())
  self.assertEqual(saved[0][2]['continuity'],'unknown');self.assertTrue(saved[0][1]['audio'])
 def test_join_requires_acknowledgement_and_preserves_two_parts(self):
  first=self.part();second=self.part()
  with self.assertRaises(RecordingPartError) as caught:self.export('join')
  self.assertEqual(caught.exception.code,'recording_ack_required')
  saved=self.export('join',True);self.assertTrue(saved[0][2]['joined']);self.assertTrue(first.exists() and second.exists())
  self.assertGreater(saved[0][1]['duration'],1.8)
 def test_join_rejects_incompatible_actual_streams(self):
  self.part();self.part(width=320)
  with self.assertRaises(RecordingPartError) as caught:self.export('join',True)
  self.assertEqual(caught.exception.code,'recording_incompatible')
 def test_separate_exports_support_different_dimensions_and_audio_presence(self):
  self.part();self.part(width=320,audio=False)
  saved=self.export();self.assertEqual(len(saved),2)
  self.assertTrue(saved[0][1]['audio']);self.assertFalse(saved[1][1]['audio'])
 def test_cancellation_stops_process_without_deleting_original(self):
  original=self.part()
  with self.assertRaises(DownloadPaused):run_copy([str(self.bin/'ffmpeg.exe'),'-v','error','-re','-stream_loop','-1','-i',str(original),'-f','null','-'],10,lambda:True)
  self.assertTrue(original.is_file())
 def test_saved_recording_recovery_revalidates_real_media_without_downloading(self):
  from core.queue_manager import DownloadManager,Job
  from services.job_lifecycle import file_signature
  from unittest.mock import patch,Mock
  original=self.part();target=self.folder/'saved.mkv';original.rename(target)
  job=Job('https://example.com/interrupted',{'format':'video','quality':'max','video_container':'mkv'},str(self.folder),str(self.bin),work_path=str(self.stage))
  job.publication_intent={'schema':1,'source':str(original),'target':str(target),'source_signature':file_signature(target)}
  job.source_signature={'requested_formats':[{'vcodec':'h264','acodec':'aac','width':160,'height':90,'fps':24}]}
  worker=Mock(side_effect=AssertionError('Recovery attempted network download'));manager=DownloadManager(worker=worker);manager.jobs=[job]
  try:
   with patch('services.malware_scan.scan_file',return_value='unavailable'):
    self.assertTrue(manager._execute(job))
   worker.assert_not_called();self.assertEqual(job.output_path,str(target));self.assertIn('codec',job.quality_summary['verified_fields'])
  finally:manager.close()

if __name__=='__main__':unittest.main()
