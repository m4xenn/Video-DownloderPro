import copy,json,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from core.queue_manager import DownloadManager,Job
from services.download_store import DownloadStore
from services.recovery import recovery_items
from state.app_state import state
import app
OPTIONS={'format':'video','quality':'720p','embed_subs':False}
URL='https://example.com/video'

class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.saved=copy.deepcopy(state);self.temp=tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='recovery-unit-')
  self.base=Path(self.temp.name);self.store=DownloadStore(self.base/'queue.sqlite3');self.managers=[]
  self.notification=patch('core.queue_manager.show_notification');self.notification.start()
 def tearDown(self):
  for manager in self.managers:manager.close()
  self.notification.stop();self.temp.cleanup();state.clear();state.update(self.saved)
 def manager(self,worker=None):
  manager=DownloadManager(worker,store=self.store);self.managers.append(manager);return manager
 def until(self,predicate):
  deadline=time.monotonic()+5
  while not predicate():
   self.assertLess(time.monotonic(),deadline);time.sleep(.01)
 def test_close_cancels_worker_and_restores_original_job_and_options(self):
  started=threading.Event()
  def worker(url,*args):
   started.set()
   while not state['cancel_flags'].get(url):time.sleep(.01)
   return False
  m=self.manager(worker);m.configure('manual',1);m.submit([URL],OPTIONS,str(self.base))
  self.assertTrue(started.wait(3));m.jobs[0].downloaded_bytes=512000;m.jobs[0].percent=45
  identity=m.jobs[0].id;m.close()
  self.assertIsNone(m.jobs[0].future);self.assertEqual(m.jobs[0].status,'paused')
  r=self.manager(Mock(return_value=True));r.restore();job=r.jobs[0]
  self.assertEqual(job.id,identity);self.assertEqual(job.options,OPTIONS)
  self.assertEqual(job.downloaded_bytes,512000);self.assertEqual(job.recovery_reason,'shutdown')
  self.assertTrue(job.restored);self.assertEqual(r.snapshot()['recovery_items'][0]['reason'],'shutdown')
  r.recover(URL);self.until(lambda:job.status=='finished')
 def test_conversion_is_allowed_to_finish_before_close(self):
  entered=threading.Event();release=threading.Event();output=self.base/'complete.mp4'
  def worker(url,opts,path,request,*args):
   opts['postprocessor_hooks'][0]({'status':'started'})
   entered.set();release.wait(4)
   self.assertFalse(state['cancel_flags'].get(url))
   output.write_bytes(b'completed');request['_completed'](str(output))
   opts['postprocessor_hooks'][0]({'status':'finished'})
   return True
  m=self.manager(worker);m.submit([URL],OPTIONS,str(self.base));self.assertTrue(entered.wait(3))
  closer=threading.Thread(target=m.close);closer.start()
  try:
   time.sleep(.05);self.assertTrue(closer.is_alive());release.set();closer.join(4)
   self.assertFalse(closer.is_alive());self.assertEqual(m.jobs[0].status,'finished')
   self.assertEqual(self.store.history()['total'],1)
  finally:release.set();closer.join(4)
 def test_initial_save_failure_does_not_close_manager(self):
  m=self.manager()
  with patch.object(self.store,'commit_queue',side_effect=OSError('disk full')):
   with self.assertRaises(ValueError):m.close()
  self.assertFalse(m.closed.is_set())
 def test_resume_save_failure_rolls_back_and_does_not_dispatch(self):
  m=self.manager(Mock(return_value=True));job=Job(URL,copy.deepcopy(OPTIONS),str(self.base),'',status='paused',restored=True)
  m.jobs=[job];state['cancel_flags'][URL]=True
  with patch.object(self.store,'commit_queue',side_effect=OSError('disk full')):
   with self.assertRaises(ValueError):m.resume(URL)
  self.assertEqual(job.status,'paused');self.assertTrue(job.restored);self.assertTrue(state['cancel_flags'][URL]);self.assertIsNone(m.thread)
 def test_resume_all_does_not_restart_live_capture_implicitly(self):
  m=self.manager();m.jobs=[Job(URL,OPTIONS,str(self.base),'',status='paused',restored=True,is_live=True)]
  m.resume_restored();self.assertEqual(m.jobs[0].status,'paused')
 def test_target_identity_is_persisted_before_transfer(self):
  m=self.manager();job=Job(URL,OPTIONS,str(self.base),'');m.jobs=[job]
  def transfer(url,opts,path,request,*args):
   request['_metadata']({'id':'fixture','title':'fixture','duration':12})
   request['_target'](str(self.base/'fixture.%(ext)s'))
   record=self.store.load_queue()[0]
   self.assertEqual(record['output_template'],str(self.base/'fixture.%(ext)s'))
   self.assertEqual(record['source_signature']['id'],'fixture')
   return False
  with patch('core.queue_manager._download_single',side_effect=transfer):m._execute(job)
 def test_refresh_keeps_source_signature_and_output_target(self):
  m=self.manager(Mock(return_value=True));job=Job(URL,OPTIONS,str(self.base),'',status='paused',source_signature={'id':'original'},output_template='original.%(ext)s')
  m.jobs=[job]
  from services.site_resolver import site_resolver
  from services.generic_resolver import generic_resolver
  with patch.object(m,'_start_scheduler'),patch.dict(site_resolver.cache,{URL:('expired',{})},clear=True),patch.dict(generic_resolver.cache,{URL:('expired',{})},clear=True):
   m.recover(URL,refresh=True)
   self.assertNotIn(URL,site_resolver.cache);self.assertNotIn(URL,generic_resolver.cache)
  self.assertEqual(job.source_signature,{'id':'original'});self.assertEqual(job.output_template,'original.%(ext)s')
 def test_recovery_summary_excludes_raw_error_and_output_paths(self):
  job=Job(URL,OPTIONS,str(self.base),'',status='error',error='SECRET',output_template='SECRET',error_code='access_denied')
  data=recovery_items([job]);self.assertNotIn('SECRET',json.dumps(data));self.assertEqual(data[0]['reason'],'refresh')
 def test_recovery_endpoint_origin_validation_and_action(self):
  c=app.app.test_client()
  with patch.object(app,'ensure_download_state'),patch.object(app.download_manager,'recover') as recover:
   self.assertEqual(c.post('/queue/recover',json={'url':URL,'action':'resume'},headers={'Origin':'https://evil.example'}).status_code,403)
   self.assertEqual(c.post('/queue/recover',json={'url':URL,'action':'delete'}).status_code,400)
   self.assertEqual(c.post('/queue/recover',json={'url':URL,'action':'refresh'}).get_json()['status'],'success')
   recover.assert_called_once_with(URL,refresh=True)

if __name__=='__main__':unittest.main()
