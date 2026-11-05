import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from services.job_lifecycle import JobLifecycle,file_signature
from services.publication_recovery import recover_saved_file,PublicationChanged
from services.media_gate import staging_directory,publish
from services.media_quality import verify_quality,QualityMismatch,validate_container,ContainerIncompatible
from services.live_quality_policy import choose_recording_source


class StabilityContracts(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'build');self.addCleanup(self.temp.cleanup)
  self.folder=Path(self.temp.name)
 def job(self):
  stage=staging_directory(self.folder,'a'*32)
  return SimpleNamespace(workflow={},phase='queued',path=str(self.folder),work_path=str(stage),options={'format':'video'},publication_intent={})
 def test_lifecycle_accounts_once_and_restarts_without_monotonic_timestamp(self):
  job=self.job();now=[10.];trace=JobLifecycle(job,lambda:now[0]);now[0]=12.;trace.stage('downloading');now[0]=17.;trace.close();trace.close()
  self.assertEqual(job.workflow['stage_seconds'],{'queued':2.,'downloading':5.})
  now[0]=1.;second=JobLifecycle(job,lambda:now[0]);second.close()
  self.assertEqual(job.workflow['attempts'],2);self.assertEqual(job.workflow['stage_seconds']['downloading'],5.)
 def test_lifecycle_rejects_corrupt_persisted_timings(self):
  job=self.job();job.workflow={'attempts':'bad','stage_seconds':{'bad':float('nan'),'negative':-1,'okay':3}}
  JobLifecycle(job,lambda:1.)
  self.assertEqual(job.workflow['stage_seconds'],{'okay':3});self.assertEqual(job.workflow['attempts'],1)
 def publication(self,fail_after=False,fail_before=False):
  job=self.job();source=Path(job.work_path)/'video.mp4';source.write_bytes(b'\0\0\0\x18ftypisom'+b'x'*32)
  def before(source,target):
   job.publication_intent={'schema':1,'source':source,'target':target,'source_signature':file_signature(source)}
   if fail_before:raise RuntimeError('database unavailable')
  def after(source,target):
   if fail_after:raise RuntimeError('process interruption')
   job.publication_intent['target_signature']=file_signature(target)
  with patch('services.windows_sandbox.restore_file_integrity'),patch('services.file_security.mark_internet_file'):
   if fail_after or fail_before:
    with self.assertRaises(RuntimeError):publish(source,self.folder,job.work_path,before,after)
   else:publish(source,self.folder,job.work_path,before,after)
  return job,source
 def test_database_failure_before_move_preserves_source(self):
  job,source=self.publication(fail_before=True)
  self.assertTrue(source.is_file());self.assertIsNone(recover_saved_file(job,lambda:False))
 def test_crash_after_rename_recovers_without_source_or_network(self):
  job,source=self.publication(fail_after=True)
  self.assertFalse(source.exists());self.assertEqual(recover_saved_file(job,lambda:False),job.publication_intent['target'])
 def test_changed_published_file_is_preserved_and_rejected(self):
  job,source=self.publication();target=Path(job.publication_intent['target']);target.write_bytes(target.read_bytes()+b'changed')
  with self.assertRaises(PublicationChanged):recover_saved_file(job,lambda:False)
  self.assertTrue(target.exists())
 def test_uncommitted_cross_volume_identity_requires_identical_bytes(self):
  job=self.job();source=Path(job.work_path)/'a.mp4';source.write_bytes(b'\0\0\0\x18ftypisom'+b'a'*32)
  target=self.folder/'a.mp4';target.write_bytes(source.read_bytes())
  job.publication_intent={'schema':1,'source':str(source),'target':str(target),'source_signature':file_signature(source)}
  self.assertEqual(recover_saved_file(job,lambda:False),str(target))
  target.write_bytes(b'\0\0\0\x18ftypisom'+b'b'*32)
  with self.assertRaises(PublicationChanged):recover_saved_file(job,lambda:False)
 def quality(self,actual,info,options=None):
  with patch('services.media_quality.process.run',return_value=SimpleNamespace(stdout=json.dumps({'streams':[actual]}).encode())):
   return verify_quality(self.folder/'a.mp4',self.folder,info,options or {'format':'video','quality':'max'})
 def test_quality_detects_silent_resolution_codec_fps_and_hdr_loss(self):
  info={'vcodec':'vp09','width':1920,'height':1080,'fps':60,'dynamic_range':'HDR10'}
  actual={'codec_name':'vp9','width':1920,'height':1080,'r_frame_rate':'60/1','color_transfer':'smpte2084'}
  self.assertEqual(set(self.quality(actual,info)['verified_fields']),{'codec','width','height','fps','hdr'})
  for key,value in [('width',1280),('height',720),('codec_name','h264'),('r_frame_rate','30/1'),('color_transfer','bt709')]:
   with self.subTest(key=key),self.assertRaises(QualityMismatch):self.quality(dict(actual,**{key:value}),info)
 def test_unknown_source_still_enforces_requested_height_cap(self):
  with self.assertRaises(QualityMismatch):self.quality({'height':1080},{},{'format':'video','quality':'720p'})
 def test_incompatible_mp4_requires_explicit_mkv_instead_of_reencoding(self):
  with self.assertRaises(ContainerIncompatible):validate_container({'vcodec':'vp8'},{'format':'video'})
  validate_container({'vcodec':'vp8'},{'format':'video','video_container':'mkv'})
 def test_hdr_dvr_fallback_does_not_silently_choose_sdr(self):
  original={'vcodec':'vp9','dynamic_range':'HDR10'};candidate={'vcodec':'h264','dynamic_range':'SDR'};router=Mock()
  selected,active=choose_recording_source(original,candidate,router)
  self.assertIs(selected,original);self.assertIsNone(active);router.close.assert_called_once()
 def test_unknown_dvr_hdr_is_verified_at_output(self):
  selected,active=choose_recording_source({'vcodec':'vp9','dynamic_range':'HDR10'},{'vcodec':'vp9'},Mock())
  self.assertEqual(selected['dynamic_range'],'HDR10')

if __name__=='__main__':unittest.main()
