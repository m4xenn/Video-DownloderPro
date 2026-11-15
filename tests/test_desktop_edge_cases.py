import sys,tempfile,unittest,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import app
from core.queue_manager import Job
from services.download_store import DownloadStore,completion_record

class DesktopEdgeCases(unittest.TestCase):
 def test_untrusted_nested_html_selector_finishes_with_patched_engine(self):
  from bs4 import BeautifulSoup
  from importlib.metadata import version
  from packaging.version import Version
  self.assertGreaterEqual(Version(version('soupsieve')),Version('4.0'))
  soup=BeautifulSoup('<div>'*200,'html.parser');started=time.monotonic()
  self.assertEqual(soup.select('section div div div'),[])
  self.assertLess(time.monotonic()-started,5)
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'build');self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.client=app.app.test_client()
 def test_directory_opens_itself_not_its_parent(self):
  with patch('app.platform.system',return_value='Windows'),patch('os.startfile') as opened:
   response=self.client.post('/open-folder',json={'path':str(self.base)})
  self.assertEqual(response.status_code,200);opened.assert_called_once_with(str(self.base))
 def test_literal_percent_encoded_name_is_not_url_decoded(self):
  folder=self.base/'literal%41';folder.mkdir();file=folder/'video.mp4';file.write_bytes(b'fixture')
  with patch('app.platform.system',return_value='Windows'),patch('os.startfile') as opened:
   response=self.client.post('/open-folder',json={'path':str(file)})
  self.assertEqual(response.status_code,200);opened.assert_called_once_with(str(folder))
 def test_missing_file_and_shell_failure_do_not_report_success(self):
  response=self.client.post('/open-folder',json={'path':str(self.base/'missing.mp4')})
  self.assertEqual(response.status_code,409);self.assertEqual(response.json['message_key'],'error.local_file_missing')
  with patch('app.platform.system',return_value='Windows'),patch('os.startfile',side_effect=OSError('failure')):
   response=self.client.post('/open-folder',json={'path':str(self.base)})
  self.assertEqual(response.status_code,409);self.assertEqual(response.json['status'],'error')
 def test_malformed_optional_metadata_does_not_hide_history(self):
  file=self.base/'file.mp4';file.write_bytes(b'fixture');store=DownloadStore(self.base/'data.sqlite')
  for index,value in enumerate(['{broken','[]','null','{"recording_parts":null}']):
   job=Job('https://example.com/'+str(index),{'format':'video','quality':'max'},str(self.base),'',output_path=str(file))
   record=completion_record(job);record['track_options']=value;store.commit_queue([],[record])
  result=store.history();self.assertEqual(result['total'],4);self.assertEqual(len(result['items']),4)
  for item in result['items']:self.assertEqual(item['recording_parts_count'],0)
  with store.connection() as connection:
   self.assertEqual({r[0] for r in connection.execute('SELECT track_options FROM history')},{'{broken','[]','null','{"recording_parts":null}'})

if __name__=='__main__':unittest.main()
