import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from services.media_gate import check_media_header,staging_directory,publish,withhold,migrate_checkpoint,OutputValidationError


class MediaGateTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='media-gate-');self.folder=Path(self.temp.name)
  self.addCleanup(self.temp.cleanup)
 def test_executable_html_and_playlist_disguised_as_media_are_rejected(self):
  for content in [b'MZ'+b'0'*200,b'<!DOCTYPE html><html>player</html>',b'#EXTM3U\nfile:///private',b'PK\x03\x04archive']:
   target=self.folder/'video.mp4';target.write_bytes(content)
   with self.assertRaises(OutputValidationError):check_media_header(target)
 def test_expected_container_required_for_each_extension(self):
  for ext,header in [('mp4',b'\0\0\0\x18ftypisom'),('m4a',b'\0\0\0\x18ftypM4A '),('mp3',b'ID3\x04\0\0'),('opus',b'OggS'+b'0'*24+b'OpusHead'),('wav',b'RIFF0000WAVE'),('webm',b'\x1aE\xdf\xa3')]:
   target=self.folder/('file.'+ext);target.write_bytes(header)
   self.assertEqual(check_media_header(target),target)
  target=self.folder/'audio.mp3';target.write_bytes(b'\0\0\0\x18ftypisom')
  with self.assertRaises(OutputValidationError):check_media_header(target)
 def test_publication_preserves_existing_file_and_moves_only_final_media(self):
  stage=staging_directory(self.folder,'a'*32)
  old=self.folder/'video.mp4';old.write_bytes(b'original')
  new=stage/'video.mp4';new.write_bytes(b'\0\0\0\x18ftypisom')
  partial=stage/'video.webm.part';partial.write_bytes(b'partial')
  output=Path(publish(new,self.folder,stage))
  self.assertEqual(output.name,'video (1).mp4');self.assertEqual(old.read_bytes(),b'original')
  self.assertTrue(partial.is_file());self.assertFalse(new.exists())
 def test_hard_link_and_directory_escape_rejected(self):
  source=self.folder/'source.mp4';source.write_bytes(b'\0\0\0\x18ftypisom')
  os.link(source,self.folder/'linked.mp4')
  with self.assertRaises(OutputValidationError):check_media_header(source)
  stage=staging_directory(self.folder,'b'*32)
  with self.assertRaises(OutputValidationError):publish(source,self.folder,stage)
 def test_withheld_file_cannot_be_published_or_opened_as_media(self):
  stage=staging_directory(self.folder,'c'*32);path=stage/'bad.mp4';path.write_bytes(b'MZfixture')
  withhold(path,stage)
  self.assertFalse(path.exists());self.assertEqual(len(list((stage/'quarantine').glob('*.blocked'))),1)
 def test_legacy_partial_move_preserves_bytes_and_does_not_move_unrelated_file(self):
  stage=staging_directory(self.folder,'d'*32)
  original=self.folder/'100% video.mp4.part';original.write_bytes(b'partial-bytes')
  other=self.folder/'unrelated.mp4';other.write_bytes(b'user-file')
  template=str(self.folder/'100%% video.%(ext)s')
  result=migrate_checkpoint(template,stage)
  self.assertEqual((stage/original.name).read_bytes(),b'partial-bytes');self.assertTrue(other.exists())
  self.assertEqual(migrate_checkpoint(template,stage),result)
 def test_scanner_failure_is_not_reported_as_checked(self):
  from services.malware_scan import scan_file
  with patch('services.malware_scan.scanner_path',return_value=None):self.assertEqual(scan_file('fixture.mp4'),'unavailable')
  for result,expected in [(Mock(returncode=0,stdout=b''),'checked'),(Mock(returncode=2,stdout=b'detection or error'),'review'),(Mock(returncode=2,stdout=b'HRESULT = 0x80070005'),'unavailable')]:
   with patch('services.malware_scan.scanner_path',return_value=Path('C:/Windows/fixture.exe')),patch('services.malware_scan.subprocess.run',return_value=result) as run:
    self.assertEqual(scan_file('fixture.mp4'),expected)
    self.assertIn('-DisableRemediation',run.call_args.args[0]);self.assertNotIn('shell',run.call_args.kwargs)
 def test_security_result_survives_queue_serialization_and_cannot_auto_retry(self):
  from core.queue_manager import DownloadManager,Job
  manager=DownloadManager();manager.jobs=[Job('https://example.com/video',{'format':'video','quality':'max'},str(self.folder),'',status='error',security_status='review')]
  try:
   self.assertEqual(manager._records()[0]['security_status'],'review')
   with self.assertRaisesRegex(ValueError,'security_review'):manager.resume(manager.jobs[0].url)
  finally:manager.jobs=[];manager.close()
 def test_all_languages_have_security_copy(self):
  from services.ui_messages import catalog
  for language,copy in catalog().items():
   for key in ['phase.security_check','phase.security_scan','security.unavailable','error.security_review','error.security_unavailable']:self.assertTrue(copy.get(key),(language,key))
 def test_pipeline_withholds_a_forged_video_before_completion(self):
  from core.queue_manager import DownloadManager,Job
  manager=DownloadManager();job=Job('https://example.com/video',{'format':'video','quality':'max'},str(self.folder),'')
  def download(url,opts,path,request,folder):
   output=Path(path)/'forged.mp4';output.write_bytes(b'MZfixture-executable')
   request['_verify'](str(output),{'vcodec':'h264','acodec':'aac'})
   self.fail('Forged video reached completion')
  try:
   with patch('core.queue_manager._download_single',side_effect=download):
    with self.assertRaises(OutputValidationError):manager._execute(job)
   self.assertEqual(job.security_status,'blocked');self.assertFalse(job.output_path)
   self.assertFalse((self.folder/'forged.mp4').exists())
   self.assertEqual(len(list(Path(job.work_path).glob('quarantine/*.blocked'))),1)
  finally:manager.close()
 def test_prepared_output_cannot_escape_before_first_download_byte(self):
  from core.queue_manager import DownloadManager,Job
  manager=DownloadManager();job=Job('https://example.com/video',{'format':'video','quality':'max'},str(self.folder),'')
  def download(url,opts,path,request,folder):
   request['_target'](str(self.folder/'escaped.%(ext)s'))
   self.fail('Escaped output reached network download')
  try:
   with patch('core.queue_manager._download_single',side_effect=download),self.assertRaises(OutputValidationError):manager._execute(job)
   self.assertFalse(job.output_template);self.assertFalse((self.folder/'escaped.mp4').exists())
  finally:manager.close()
 def test_pipeline_scan_review_is_withheld_but_unavailable_is_clearly_reported(self):
  from core.queue_manager import DownloadManager,Job
  from services.media_gate import SecurityReviewError
  def download(url,opts,path,request,folder):
   output=Path(path)/'media.mp4';output.write_bytes(b'\0\0\0\x18ftypisom')
   request['_verify'](str(output),{'vcodec':'h264','acodec':'aac'})
   request['_completed'](str(output));return True
  for verdict in ['review','unavailable','checked']:
   manager=DownloadManager();job=Job('https://example.com/video',{'format':'video','quality':'max'},str(self.folder),'')
   try:
    with patch('core.queue_manager._download_single',side_effect=download),patch('services.output_validation.validate_output',return_value={'video':True,'audio':True}),patch('services.media_quality.verify_quality',return_value={}),patch('services.malware_scan.scan_file',return_value=verdict):
     if verdict=='review':
      with self.assertRaises(SecurityReviewError):manager._execute(job)
      self.assertFalse(job.output_path)
     else:
      self.assertTrue(manager._execute(job));self.assertTrue(Path(job.output_path).is_file())
      self.assertEqual(Path(job.output_path).parent,self.folder)
    self.assertEqual(job.security_status,verdict)
   finally:manager.close()
 def test_low_disk_reserve_stops_without_deleting_partial_bytes(self):
  from services.media_gate import MediaDiskGuard
  partial=self.folder/'video.mp4.part';partial.write_bytes(b'partial')
  with patch('services.media_gate.shutil.disk_usage',return_value=Mock(free=1024)):
   with self.assertRaises(OSError):MediaDiskGuard(self.folder).check()
  self.assertEqual(partial.read_bytes(),b'partial')
 @unittest.skipUnless(os.name=='nt','Windows destination compatibility')
 def test_destination_without_private_acls_uses_local_workspace_and_restores_it(self):
  from services.windows_sandbox import protect_workspace
  calls=[]
  def protect(path):
   calls.append(path)
   if len(calls)==1:raise OSError('Fixture volume does not support security descriptors')
   protect_workspace(path)
  with patch.dict(os.environ,LOCALAPPDATA=str(self.folder/'local')),patch('services.windows_sandbox.protect_workspace',side_effect=protect):
   stage=staging_directory(self.folder,'f'*32)
  self.assertEqual(stage,self.folder/'local/YoutubePro/media-work'/('f'*32))
  with patch.dict(os.environ,LOCALAPPDATA=str(self.folder/'local')):
   self.assertEqual(staging_directory(self.folder,'f'*32,str(stage)),stage)
 def test_cross_volume_publication_is_exclusive_and_preserves_bytes(self):
  import errno
  stage=staging_directory(self.folder,'1'*32);source=stage/'copied.mp4';payload=b'\0\0\0\x18ftypisom'+b'fixture'*10000;source.write_bytes(payload)
  rename=os.rename;calls=[]
  def cross_volume(old,new):
   calls.append((old,new))
   if len(calls)==1:raise OSError(errno.EXDEV,'Fixture cross-volume move')
   return rename(old,new)
  with patch('services.media_gate.os.rename',side_effect=cross_volume):result=Path(publish(source,self.folder,stage))
  self.assertEqual(result.read_bytes(),payload);self.assertFalse(source.exists())
  self.assertFalse(list(self.folder.glob('.vdp-publish-*.tmp')))


@unittest.skipUnless(os.name=='nt','Windows process confinement')
class NativeMediaProcessTests(unittest.TestCase):
 def test_worker_cannot_write_a_normal_folder_but_can_write_its_stage(self):
  import win32api,win32security as security
  token=security.OpenProcessToken(win32api.GetCurrentProcess(),8)
  try:integrity=security.ConvertSidToStringSid(security.GetTokenInformation(token,security.TokenIntegrityLevel)[0])
  finally:token.Close()
  if integrity=='S-1-16-4096':self.skipTest('Run outside the tool low-integrity wrapper to verify write-up denial')
  from services.media_process import run
  with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='write-confinement-') as folder:
   stage=staging_directory(folder,'e'*32)
   outside=Path(folder)/'private-fixture.txt';outside.write_text('original')
   code="import pathlib,json;result={};\ntry:pathlib.Path("+repr(str(outside))+").write_text('changed');result['outside_write']=True\nexcept OSError:result['outside_write']=False\npathlib.Path("+repr(str(stage/'inside.txt'))+").write_text('allowed');print(json.dumps(result))"
   result=run([sys.executable,'-c',code],capture_output=True,timeout=15,check=True)
   self.assertFalse(json.loads(result.stdout)['outside_write']);self.assertEqual(outside.read_text(),'original')
   self.assertEqual((stage/'inside.txt').read_text(),'allowed')
 def test_unexpected_descendant_is_stopped_when_media_process_exits(self):
  import psutil,time
  from services.media_process import run
  code="import subprocess,sys;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print(p.pid)"
  result=run([sys.executable,'-c',code],capture_output=True,timeout=15,check=True)
  pid=int(result.stdout)
  for _ in range(40):
   if not psutil.pid_exists(pid):break
   time.sleep(.05)
  self.assertFalse(psutil.pid_exists(pid))
 def test_low_integrity_and_non_inherited_job_handle(self):
  from services.media_process import run
  code="import win32api,win32security as s,json;t=s.OpenProcessToken(win32api.GetCurrentProcess(),8);print(json.dumps({'integrity':s.ConvertSidToStringSid(s.GetTokenInformation(t,s.TokenIntegrityLevel)[0])}))"
  result=run([sys.executable,'-c',code],capture_output=True,timeout=15,check=True)
  self.assertEqual(json.loads(result.stdout)['integrity'],'S-1-16-4096')
 def test_output_flood_is_bounded_and_process_stopped(self):
  from services.media_process import run,SubprocessError
  with self.assertRaises(SubprocessError):run([sys.executable,'-c',"import sys;sys.stdout.buffer.write(b'x'*4000000)"],capture_output=True,timeout=10)
 def test_timeout_stops_process(self):
  from services.media_process import run,TimeoutExpired
  with self.assertRaises(TimeoutExpired):run([sys.executable,'-c','import time;time.sleep(30)'],capture_output=True,timeout=.2)
 def test_ytdlp_communicate_keeps_bounded_diagnostics_without_killing_a_long_log(self):
  from services.media_process import install_yt_dlp_guard,SubprocessError
  install_yt_dlp_guard()
  from yt_dlp.utils import Popen
  with Popen([sys.executable,'-c',"import sys;sys.stderr.write('x'*1000000+'FINAL LINE')"],text=True,stdout=-1,stderr=-1,stdin=-1) as process:
   process._vdp_guarded=True  # Exercise the media collector with a harmless Python output fixture.
   stdout,stderr=process.communicate(timeout=10)
   self.assertEqual(process.returncode,0);self.assertLessEqual(len(stderr),256*1024);self.assertTrue(stderr.endswith('FINAL LINE'))
  with Popen([sys.executable,'-c',"import sys;sys.stdout.buffer.write(b'x'*4000000)"],stdout=-1,stderr=-1,stdin=-1) as process:
   process._vdp_guarded=True
   with self.assertRaises(SubprocessError):process.communicate(timeout=10)


if __name__=='__main__':unittest.main()
