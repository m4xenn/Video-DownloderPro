import os
from pathlib import Path
import subprocess,sys,threading,unittest,uuid
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from services.app_lifecycle import SingleInstance,ShutdownController,lifecycle_text

class LifecycleTests(unittest.TestCase):
 def test_all_locales_have_shutdown_and_duplicate_messages(self):
  for language in ('tr','en','de','es','fr','pt','ru','zh','ja','hi'):
   words=lifecycle_text(language)
   for key in ('alreadyRunning','closeTitle','closeMessage','saving','saveFailed'):
    self.assertTrue(words[key],(language,key))

 @unittest.skipUnless(os.name=='nt','Windows named mutex')
 def test_second_process_is_blocked_and_release_allows_restart(self):
  name='Local\\VDP-Test-'+uuid.uuid4().hex
  lock=SingleInstance(name);self.assertTrue(lock.acquire())
  code="import sys;sys.path.insert(0,sys.argv[1]);from services.app_lifecycle import SingleInstance;l=SingleInstance(sys.argv[2]);print(l.acquire());l.close()"
  try:
   result=subprocess.run([sys.executable,'-c',code,str(ROOT/'src'),name],capture_output=True,text=True,check=True,timeout=10)
   self.assertEqual(result.stdout.strip(),'False')
  finally:lock.close()
  next_lock=SingleInstance(name)
  try:self.assertTrue(next_lock.acquire())
  finally:next_lock.close()

 @unittest.skipUnless(os.name=='nt','Windows named mutex')
 def test_os_releases_mutex_after_abrupt_process_exit(self):
  name='Local\\VDP-Crash-Test-'+uuid.uuid4().hex
  code="import sys,time;sys.path.insert(0,sys.argv[1]);from services.app_lifecycle import SingleInstance;l=SingleInstance(sys.argv[2]);print(l.acquire(),flush=True);time.sleep(30)"
  child=subprocess.Popen([sys.executable,'-u','-c',code,str(ROOT/'src'),name],stdout=subprocess.PIPE,text=True)
  try:
   self.assertEqual(child.stdout.readline().strip(),'True')
   child.kill();child.wait(10)
   lock=SingleInstance(name)
   try:self.assertTrue(lock.acquire())
   finally:lock.close()
  finally:
   if child.poll() is None:child.kill();child.wait(10)
   child.stdout.close()

 def controller(self,busy=True):
  window=Mock();manager=Mock();manager.busy.return_value=busy
  window.create_confirmation_dialog.return_value=True
  cleanup=Mock()
  control=ShutdownController(window,manager,cleanup,lambda:lifecycle_text('tr'))
  return control,window,manager,cleanup

 def test_cancel_leaves_app_and_downloads_running(self):
  c,w,m,cleanup=self.controller();w.create_confirmation_dialog.return_value=False
  self.assertFalse(c.on_closing());m.close.assert_not_called();w.destroy.assert_not_called();cleanup.assert_not_called()

 def test_close_is_vetoed_until_workers_saved(self):
  c,w,m,cleanup=self.controller();entered=threading.Event();release=threading.Event()
  def close():entered.set();release.wait(3)
  m.close.side_effect=close
  try:
   self.assertFalse(c.on_closing());self.assertTrue(entered.wait(2))
   self.assertFalse(c.on_closing());w.destroy.assert_not_called()
   release.set();c.worker.join(3)
   self.assertFalse(c.worker.is_alive());w.destroy.assert_called_once();cleanup.assert_called_once()
   self.assertTrue(c.on_closing());w.create_confirmation_dialog.assert_called_once()
  finally:release.set()

 def test_save_failure_keeps_window_and_allows_retry(self):
  c,w,m,cleanup=self.controller();m.close.side_effect=ValueError('disk full SECRET')
  with patch('services.app_lifecycle.native_notice') as notice:
   self.assertFalse(c.on_closing());c.worker.join(3)
   w.destroy.assert_not_called();cleanup.assert_not_called();self.assertFalse(c.saving)
   self.assertNotIn('SECRET',notice.call_args.args[0])
   m.close.side_effect=None
   self.assertFalse(c.on_closing());c.worker.join(3)
  w.destroy.assert_called_once()

 def test_idle_close_still_saves_without_warning(self):
  c,w,m,cleanup=self.controller(False)
  self.assertFalse(c.on_closing());c.worker.join(3)
  w.create_confirmation_dialog.assert_not_called();m.close.assert_called_once();w.destroy.assert_called_once()

if __name__=='__main__':unittest.main()
