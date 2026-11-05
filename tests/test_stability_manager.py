import copy,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from core.queue_manager import DownloadManager,Job
from services.download_store import DownloadStore
from state.app_state import state


class StabilityManagerTests(unittest.TestCase):
 def setUp(self):
  self.saved=copy.deepcopy(state);self.temp=tempfile.TemporaryDirectory(dir=ROOT/'build');self.folder=Path(self.temp.name)
  self.store=DownloadStore(self.folder/'queue.sqlite3');self.manager=DownloadManager(store=self.store)
  self.notice=patch('core.queue_manager.show_notification');self.notice.start()
 def tearDown(self):
  self.manager.close();self.notice.stop();self.temp.cleanup();state.clear();state.update(self.saved)
 def job(self):
  job=Job('https://example.com/video',{'format':'video','quality':'max'},str(self.folder),'',status='paused',is_live=True)
  job.recording_parts=[{'id':'b'*32,'state':'interrupted','bytes':100,'workspace':str(self.folder/'.vdp-work'/job.id),'file':'part.mkv'}]
  self.manager.jobs.append(job);return job
 def test_removing_live_job_keeps_recovery_reference_in_history_after_restart(self):
  job=self.job();self.manager.remove(job.url)
  record=self.store.get_history(job.id)
  self.assertTrue(record['recording_archive']);self.assertFalse(record['file_exists']);self.assertEqual(record['recording_parts_count'],1)
  self.assertEqual(self.store.history_track_state(job.id)['recording_parts'],job.recording_parts)
  self.assertEqual(self.store.load_queue(),[])
 def test_archive_commit_failure_rolls_back_queue_and_history_buffer(self):
  job=self.job()
  with patch.object(self.store,'commit_queue',side_effect=OSError('disk full')):
   with self.assertRaises(ValueError):self.manager.remove(job.url)
  self.assertEqual(self.manager.jobs,[job]);self.assertEqual(self.manager.pending_history,[])
 def test_same_history_parent_cannot_run_two_concurrent_recoveries(self):
  job=self.job();self.manager.remove(job.url);release=threading.Event();entered=threading.Event()
  def worker(*args):entered.set();release.wait(5);return []
  try:
   with patch.object(self.manager,'_recover_recording_worker',side_effect=worker):
    self.manager.recover_recording(job.id,'export','',history=True)
    self.assertTrue(entered.wait(2))
    with self.assertRaisesRegex(ValueError,'still running'):self.manager.recover_recording(job.id,'export','',history=True)
  finally:release.set()
 def test_dense_bandwidth_events_keep_bounded_samples_without_losing_bytes(self):
  now=[0.];self.manager.clock=lambda:now[0]
  for n in range(100000):now[0]=n/10000;self.manager.record(7)
  self.assertLessEqual(len(self.manager.samples),101);self.assertEqual(sum(value for stamp,value in self.manager.samples),700000)
  now[0]=21.;self.assertEqual(self.manager._throughput(now[0]),0);self.assertEqual(len(self.manager.samples),0)
 def test_finished_recording_with_older_parts_stays_finished_on_restart(self):
  job=self.job();job.status='finished';target=self.folder/'saved.mp4';target.write_bytes(b'fixture')
  stage=self.folder/'.vdp-work'/job.id
  job.work_path=str(stage);job.publication_intent={'schema':1,'source':str(stage/'saved.mp4'),'target':str(target)}
  self.manager._persist(required=True)
  restored=DownloadManager(store=self.store)
  try:
   restored.restore();self.assertEqual(restored.jobs[0].status,'finished')
   self.assertEqual(restored.snapshot()['recovery_items'][0]['reason'],'parts')
  finally:restored.close()

if __name__=='__main__':unittest.main()
