"""Performance reuse cannot weaken media validation or retain file locks."""
import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from services.output_validation import validate_output,validation_session


class StartupPreloadTests(unittest.TestCase):
 def test_preload_imports_source_support_without_opening_network_connections(self):
  import subprocess
  code="import socket,sys;socket.socket.connect=lambda *a:(_ for _ in ()).throw(AssertionError('preload opened a connection'));import main;main._preload_media();assert 'services.site_resolver' in sys.modules"
  subprocess.run([sys.executable,'-c',code],check=True,capture_output=True,timeout=15)


@unittest.skipUnless(os.name=='nt','Windows deny-write leases')
class ValidationReuseTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='validation-reuse-');self.directory=Path(self.temp.name)
  self.path=self.directory/'media.mp4';self.path.write_bytes(b'fixture-media')
  self.addCleanup(self.temp.cleanup)
 def test_reuses_only_unchanged_locked_file_after_rename(self):
  details={'video':True,'audio':True,'duration':30}
  with patch('services.output_validation._validate_output',return_value=details) as probe:
   with validation_session():
    self.assertEqual(validate_output(self.path,'',True,expect_audio=True,reuse_validation=True),{'video':True,'audio':True})
    moved=self.path.with_name('renamed.mp4');self.path.rename(moved)
    self.assertEqual(validate_output(moved,'',True,expect_audio=True,include_duration=True,reuse_validation=True),details)
    self.assertEqual(probe.call_count,1)
    with self.assertRaises(OSError):
     with moved.open('r+b') as stream:stream.write(b'changed')
   moved.write_bytes(b'new-content')
   with validation_session():validate_output(moved,'',True,expect_audio=True,reuse_validation=True)
   self.assertEqual(probe.call_count,2)
 def test_policy_change_or_file_replacement_needs_full_validation(self):
  with patch('services.output_validation._validate_output',return_value={'video':True,'audio':True,'duration':30}) as probe:
   with validation_session():
    validate_output(self.path,'',True,reuse_validation=True)
    validate_output(self.path,'',True,expect_audio=True,reuse_validation=True)
    replacement=self.directory/'replacement.mp4';replacement.write_bytes(b'new-content')
    self.path.rename(self.directory/'old-locked.mp4');replacement.rename(self.path)
    validate_output(self.path,'',True,expect_audio=True,reuse_validation=True)
   self.assertEqual(probe.call_count,3)
 def test_failed_validation_is_not_reused_and_releases_write_lock(self):
  with patch('services.output_validation._validate_output',side_effect=ValueError('invalid')) as probe:
   with validation_session():
    for _ in range(2):
     with self.assertRaises(ValueError):validate_output(self.path,'',True,reuse_validation=True)
    self.path.write_bytes(b'can-write-after-failure')
   self.assertEqual(probe.call_count,2)
 def test_unavailable_lease_never_reuses_a_result(self):
  with patch('services.output_validation._read_lease',return_value=None),patch('services.output_validation._validate_output',return_value={'video':True,'audio':False,'duration':30}) as probe:
   with validation_session():
    for _ in range(2):validate_output(self.path,'',True,reuse_validation=True)
   self.assertEqual(probe.call_count,2)


if __name__=='__main__':unittest.main()
