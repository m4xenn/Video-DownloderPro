import concurrent.futures
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.diagnostics import Diagnostics, error_code
import app


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.path=Path(self.temp.name)/'diagnostics.sqlite3'
        self.store=Diagnostics(self.path,limit=5)
    def tearDown(self):self.temp.cleanup()

    def test_restart_and_safe_export(self):
        secret='Cookie: session=VERYPRIVATE https://user:password@cdn.example/token/path?sig=VERYPRIVATE C:\\Users\\salih\\private.mp4'
        self.store.record('download','https://user:password@watch.example/private?token=VERYPRIVATE',error='HTTP Error 429 '+secret)
        report=Diagnostics(self.path).report()
        text=report['text']
        for value in ('VERYPRIVATE','password','session=','private.mp4','/private','/token/path','salih'):
            self.assertNotIn(value,text)
            self.assertNotIn(value,self.path.read_bytes().decode('latin1'))
        self.assertIn('rate_limited',text);self.assertIn('watch.example',text)
        self.assertEqual(report['count'],1)

    def test_bound_and_coalesce(self):
        for _ in range(20):self.store.record('download','https://example.com/a',error='429')
        self.assertIn('x20',self.store.report()['text'])
        for i in range(10):self.store.record('metadata',f'https://example.com/{i}','started')
        self.assertEqual(self.store.report()['count'],5)

    def test_concurrent_events(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(lambda _:self.store.record('download','https://example.com','started'),range(25)))
        self.assertIn('x25',self.store.report()['text'])

    def test_disk_failure_is_nonfatal_and_visible(self):
        store=Diagnostics(Path(self.temp.name))
        store.record('metadata',error='429')
        self.assertFalse(store.report()['available'])

    def test_empty_report_does_not_create_database(self):
        self.assertEqual(self.store.report()['count'],0);self.assertFalse(self.path.exists())
    def test_report_filtered_to_one_download_and_progress_same_origin(self):
        self.store.record('download','https://one.example/a','started')
        self.store.record('download','https://two.example/b','started')
        self.assertEqual(self.store.report('https://one.example/a')['count'],1)
        self.assertNotIn('two.example',self.store.report('https://one.example/a')['text'])
        client=app.app.test_client()
        app.source_progress.set('https://one.example/a','validating_source')
        data=client.post('/source-progress',json={'url':'https://one.example/a'}).get_json()
        self.assertEqual(data['phase'],'validating_source')
        self.assertEqual(client.post('/source-progress',json={'url':'x'},headers={'Origin':'https://evil.example'}).status_code,403)

    def test_endpoint_same_origin_and_safe_report(self):
        self.store.record('browser','https://example.com','interaction_required')
        with patch.object(app,'diagnostics',self.store):
            client=app.app.test_client()
            self.assertEqual(client.post('/diagnostics',headers={'Origin':'https://evil.example'}).status_code,403)
            data=client.post('/diagnostics',json={},headers={'Origin':'http://localhost'}).get_json()
            self.assertEqual(data['status'],'success');self.assertIn('interaction_required',data['text'])

    def test_matrix_summary_excludes_raw_secrets(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        from site_matrix import summarize
        data=summarize({'id':'case','url':'https://example.com/private?token=SECRET'},
                       {'status':'failed','error':'403 SECRET','title':'SECRET','contexts':[{'Cookie':'SECRET'}]},2)
        self.assertNotIn('SECRET',json.dumps(data));self.assertEqual(data['error_code'],'access_denied')
        self.assertEqual(data['full_download'],'not_tested')

    def test_known_error_codes(self):
        for message,code in [('HTTP Error 429','rate_limited'),('fragment 15 failed','fragment_failed'),
                             ('No such file or directory','local_file_missing'),('random secret','unexpected')]:
            self.assertEqual(error_code(message),code)
    def test_metadata_error_does_not_echo_signed_urls(self):
        with patch.object(app,'extract_media_info',side_effect=RuntimeError('403 https://cdn.example/private?sig=SECRET')):
            data=app.app.test_client().post('/get-info',json={'url':'https://example.com/video'}).get_json()
        self.assertEqual(data['status'],'error');self.assertEqual(data['error_code'],'access_denied')
        self.assertNotIn('SECRET',json.dumps(data))


if __name__=='__main__':unittest.main()
