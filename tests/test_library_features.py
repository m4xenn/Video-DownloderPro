"""Durability, bounded retries, playlist authorization and history contracts."""
import copy
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from services.download_store import DownloadStore, media_key
from services.media_catalog import MediaCatalog, estimate_size
from core.queue_manager import DownloadManager
from core.retry_policy import transient_error, retry_delay
from state.app_state import state
import app

OPTIONS = {'format':'video','quality':'720p','embed_subs':False}


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.saved = copy.deepcopy(state)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.folder = Path(self.temp.name)
        self.store = DownloadStore(self.folder / 'downloads.sqlite3')
        self.managers = []
        self.notify = patch('core.queue_manager.show_notification')
        self.notify.start()

    def tearDown(self):
        for manager in self.managers:
            manager.close()
        self.notify.stop()
        self.temp.cleanup()
        state.clear(); state.update(self.saved)

    def manager(self, worker, **kwargs):
        manager = DownloadManager(worker, store=self.store, **kwargs)
        self.managers.append(manager)
        return manager

    def until(self, predicate):
        deadline = time.monotonic() + 4
        while not predicate():
            if time.monotonic() > deadline:
                self.fail('scheduler timed out')
            time.sleep(0.01)

    def record(self, identity='one', key='youtube:abc', kind='video', quality='720p'):
        output = self.folder / (identity + '.mp4')
        output.write_bytes(b'test media')
        record = {'id':identity,'media_key':key,'url':'https://youtube.com/watch?v=abc',
            'title':'A saved video','thumbnail':'','format':kind,'quality':quality,'embed_subs':False,
            'path':str(output),'size':output.stat().st_size,'completed_at':'2026-10-17T00:00:00+00:00'}
        self.store.commit_queue([], [record])
        return record

    def test_history_preview_uses_record_and_supports_seeking(self):
        record = self.record()
        with patch.object(app, 'download_store', self.store):
            client = app.app.test_client()
            response = client.get('/history/one/media?path=evil.exe', headers={'Range':'bytes=0-3'})
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response.data, b'test')
            self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
            response.close()
            self.assertEqual(client.get('/history/unknown/media').status_code, 404)
            Path(record['path']).unlink()
            self.assertEqual(client.get('/history/one/media').status_code, 404)

    def test_history_preview_rejects_non_media(self):
        record = self.record()
        unsafe = self.folder / 'program.exe'
        unsafe.write_bytes(b'executable')
        record['path'] = str(unsafe)
        record['file_exists'] = True
        with patch.object(app.download_store, 'get_history', return_value=record):
            self.assertEqual(app.app.test_client().get('/history/one/media').status_code, 415)

    def test_empty_store_read_does_not_create_database(self):
        self.assertEqual(self.store.load_queue(), [])
        self.assertEqual(self.store.history()['total'], 0)
        self.assertFalse(self.store.path.exists())

    def test_drafts_survive_new_store_instance(self):
        self.store.save_drafts([{'url':'https://x/a','title':'draft','thumbnail':''}])
        self.assertEqual(DownloadStore(self.store.path).load_drafts()[0]['title'],'draft')

    def test_queue_acceptance_clears_only_accepted_drafts(self):
        self.store.save_drafts([{'url':'https://x/a'},{'url':'https://x/b'}])
        self.store.commit_queue([],clear_drafts=['https://x/a'])
        self.assertEqual(self.store.load_drafts(),[{'url':'https://x/b'}])

    def test_queue_and_history_rollback_together(self):
        self.store.commit_queue([{'id':'previous'}])
        with self.assertRaises(sqlite3.Error):
            self.store.commit_queue([{'id':'new'}],[{'id':'broken'}])
        self.assertEqual(self.store.load_queue(),[{'id':'previous'}])

    def test_inflight_queue_recovers_paused_without_auto_network(self):
        self.store.commit_queue([{'url':'https://x/a','options':OPTIONS,'path':str(self.folder),'bin_dir':'',
                                 'id':'stable','status':'downloading','percent':40,'output_template':'stable.%(ext)s'}])
        worker = Mock(return_value=True)
        manager = self.manager(worker)
        manager.restore()
        result = manager.snapshot()
        self.assertEqual(result['status'],'paused')
        self.assertEqual(result['restored_count'],1)
        self.assertEqual(result['items'][0]['id'],'stable')
        worker.assert_not_called()
        manager.resume_restored()
        self.assertEqual(manager.wait(4)['status'],'finished_all')
        self.assertEqual(manager.jobs[0].options,OPTIONS)

    def test_paused_and_retry_wait_records_restore(self):
        for index,status in enumerate(('paused','retry_wait')):
            self.store.commit_queue([{'url':'https://x/'+str(index),'options':OPTIONS,'path':str(self.folder),
                                     'bin_dir':'','status':status,'retry_count':1}])
            manager = self.manager(Mock(return_value=True)); manager.restore()
            self.assertEqual(manager.jobs[0].status,'paused')
            self.assertTrue(manager.jobs[0].restored)

    def test_read_error_does_not_overwrite_original_queue(self):
        self.store.commit_queue([{'id':'original'}])
        self.store.read_error='Cannot recover queue'
        with self.assertRaises(ValueError):
            self.store.commit_queue([])
        self.assertEqual(self.store.load_queue(),[{'id':'original'}])

    def test_transient_classification_is_conservative(self):
        for text in ('HTTP Error 503','connection reset','getaddrinfo failed','timed out','HTTP Error 429'):
            self.assertTrue(transient_error(text),text)
        for text in ('Private video','Video unavailable','HTTP Error 404','Requested format missing',
                     'Permission denied','Disk full','unknown exception'):
            self.assertFalse(transient_error(text),text)
        self.assertEqual([retry_delay(1),retry_delay(2)],[5,10])

    def test_automatic_retry_is_bounded(self):
        clock = [100.0]
        calls = []
        def worker(url, opts, path, request, *_):
            calls.append(1); request['_error']('HTTP Error 503')
            return False
        manager = self.manager(worker,clock=lambda:clock[0])
        manager.submit(['https://x/a'],OPTIONS,str(self.folder))
        self.until(lambda: manager.jobs[0].status=='retry_wait')
        self.assertEqual(manager.jobs[0].retry_count,1)
        clock[0] = 106; manager.tick()
        self.until(lambda: manager.jobs[0].status=='retry_wait' and manager.jobs[0].retry_count==2)
        clock[0] = 117; manager.tick()
        self.until(lambda: manager.jobs[0].status=='error')
        self.assertEqual(len(calls),3)

    def test_pause_cancels_scheduled_retry(self):
        clock = [100.0]
        calls = []
        def worker(url,opts,path,request,*_):
            calls.append(1); request['_error']('connection timeout'); return False
        manager = self.manager(worker,clock=lambda:clock[0])
        manager.submit(['https://x/a'],OPTIONS,str(self.folder))
        self.until(lambda:manager.jobs[0].status=='retry_wait')
        manager.pause('https://x/a')
        clock[0]=1000; manager.tick()
        self.assertEqual(manager.jobs[0].status,'paused')
        self.assertEqual(len(calls),1)

    def test_completion_notifies_once_while_ui_polls(self):
        with patch('core.queue_manager.show_notification') as notify:
            manager = self.manager(lambda *_: True)
            manager.submit(['https://example.com/video'], OPTIONS, str(self.folder))
            self.assertEqual(manager.wait(4)['status'], 'finished_all')
            for _ in range(3):
                manager.tick()
                manager.snapshot()
            self.until(lambda: notify.call_count == 1)
            notify.assert_called_once_with('Video Downloader Pro', 'Tüm indirmeler tamamlandı.')

    def test_success_writes_one_history_record(self):
        def worker(url,opts,path,request,*_):
            output = Path(path)/'out.mp4'; output.write_bytes(b'media')
            request['_metadata']({'id':'abc','extractor_key':'Youtube','title':'Actual title','filesize':100})
            request['_completed'](str(output))
            return True
        manager = self.manager(worker)
        manager.submit(['https://youtube.com/watch?v=abc'],OPTIONS,str(self.folder))
        self.assertEqual(manager.wait(4)['status'],'finished_all')
        self.assertEqual(self.store.history()['total'],1)
        manager.close()
        self.assertEqual(self.store.history()['total'],1)
        record=self.store.history()['items'][0]
        self.assertEqual(record['title'],'Actual title')
        self.assertEqual(record['size'],5)

    def test_failed_download_does_not_enter_history(self):
        manager=self.manager(lambda *_:False)
        manager.submit(['https://x/a'],OPTIONS,str(self.folder))
        self.assertEqual(manager.wait(4)['status'],'error')
        self.assertEqual(self.store.history()['total'],0)

    def test_duplicates_require_same_options_and_existing_file(self):
        record=self.record()
        self.assertEqual(len(self.store.duplicates('youtube:abc','alias',OPTIONS)),1)
        self.assertFalse(self.store.duplicates('youtube:abc','alias',dict(OPTIONS,quality='1080p')))
        self.assertFalse(self.store.duplicates('youtube:abc','alias',dict(OPTIONS,format='audio',quality='mp3')))
        self.assertFalse(self.store.duplicates('youtube:abc','alias',dict(OPTIONS,embed_subs=True)))
        Path(record['path']).unlink()
        self.assertFalse(self.store.duplicates('youtube:abc','alias',OPTIONS))

    def test_deleted_file_stays_in_history_as_missing(self):
        record=self.record(); Path(record['path']).unlink()
        self.assertFalse(self.store.get_history(record['id'])['file_exists'])
        self.assertEqual(self.store.history('saved')['total'],1)

    def test_youtube_aliases_have_same_identity(self):
        self.assertEqual(media_key('https://youtu.be/abc?t=30'),media_key('https://www.youtube.com/watch?v=abc&list=anything'))
        self.assertEqual(media_key('https://youtube.com/shorts/abc'),'youtube:abc')

    def test_generic_media_keys_do_not_collide_across_domains(self):
        info={'extractor_key':'Generic','id':'video'}
        self.assertNotEqual(media_key('https://one/video.mp4',info),media_key('https://two/video.mp4',info))

    def test_estimates_can_be_unknown(self):
        self.assertIsNone(estimate_size({'requested_formats':[{'filesize':10},{}]}))
        self.assertEqual(estimate_size({'requested_formats':[{'filesize':10},{'filesize_approx':20}]}),30)

    def test_preview_selection_is_server_owned(self):
        catalog=MediaCatalog()
        catalog.previews['token']={'created':time.monotonic(),'status':'ready','source_urls':['https://list'],
            'entries':[{'id':'one','url':'https://x/a','available':True},{'id':'private','url':'https://x/b','available':False}]}
        self.assertEqual(catalog.selected('token',['one'],['https://list'])[0]['url'],'https://x/a')
        for selection in ([],['private'],['forged'],['one','one']):
            with self.assertRaises(ValueError): catalog.selected('token',selection,['https://list'])
        with self.assertRaises(ValueError): catalog.selected('token',['one'],['https://other'])

    def test_confirmation_plan_expires_and_is_single_use(self):
        catalog=MediaCatalog()
        token=catalog.plan([{'url':'https://x/a'}],OPTIONS)
        self.assertEqual(catalog.consume_plan(token)['options'],OPTIONS)
        with self.assertRaises(ValueError): catalog.consume_plan(token)
        token=catalog.plan([],OPTIONS); catalog.plans[token]['created']-=301
        with self.assertRaises(ValueError): catalog.consume_plan(token)

    def test_preview_normalizes_youtube_and_disables_private_entries(self):
        catalog = MediaCatalog()
        catalog.previews['preview'] = {'created':time.monotonic(), 'status':'checking', 'source_urls':['https://list']}
        entries = [{'id':'abc', 'url':'abc', 'ie_key':'Youtube', 'title':'First'},
                   {'id':'private', 'url':'private', 'ie_key':'Youtube', 'title':'[Private video]'}, None]
        with patch('yt_dlp.YoutubeDL') as ydl:
            ydl.return_value.__enter__.return_value.extract_info.return_value = {'title':'Collection', 'entries':entries}
            catalog._preview('preview', ['https://list'])
        preview = catalog.preview_status('preview')
        self.assertEqual(preview['status'], 'ready')
        self.assertEqual(preview['entries'][0]['url'], 'https://www.youtube.com/watch?v=abc')
        self.assertTrue(preview['entries'][0]['available'])
        self.assertFalse(preview['entries'][1]['available'])
        self.assertEqual(preview['entries'][0]['group'], 'Collection')

    def test_preview_caps_large_playlists(self):
        catalog = MediaCatalog()
        catalog.previews['preview'] = {'created':time.monotonic(), 'status':'checking', 'source_urls':['https://list']}
        with patch('yt_dlp.YoutubeDL') as ydl:
            ydl.return_value.__enter__.return_value.extract_info.return_value = {
                'entries':({'url':f'https://example.com/{i}', 'title':str(i)} for i in range(2005))}
            catalog._preview('preview', ['https://list'])
        preview = catalog.preview_status('preview')
        self.assertTrue(preview['truncated'])
        self.assertEqual(len(preview['entries']), 2000)

    def test_confirm_again_uses_immutable_server_options(self):
        record = self.record()
        catalog = MediaCatalog()
        specs = [{'url':record['url'], 'path':str(self.folder)}]
        token = catalog.plan(specs, OPTIONS)
        specs[0]['url'] = 'https://evil.example/changed'
        with patch.object(app,'media_catalog',catalog), patch.object(app,'ensure_download_state'), \
             patch.object(app,'start_specs') as start:
            start.return_value = ({'status':'success'}, 202)
            response = app.app.test_client().post('/download/confirm',json={
                'token':token, 'action':'again', 'format':'audio', 'urls':['https://evil.example']})
            self.assertEqual(response.status_code, 202)
            self.assertEqual(start.call_args.args[0][0]['url'], record['url'])
            self.assertEqual(start.call_args.args[1], OPTIONS)

    def test_duplicate_route_needs_confirmation_and_can_skip(self):
        record=self.record()
        catalog=MediaCatalog()
        with patch.object(app,'download_store',self.store),patch.object(app,'media_catalog',catalog), \
             patch.object(app,'download_manager') as manager,patch.object(app,'ensure_download_state'):
            state['current_download_path']=str(self.folder)
            client=app.app.test_client()
            data={'urls':[record['url']],**OPTIONS}
            response=client.post('/download',json=data)
            self.assertEqual(response.status_code,409)
            self.assertEqual(response.json['status'],'duplicate')
            manager.submit_specs.assert_not_called()
            result=client.post('/download/confirm',json={'token':response.json['confirmation_token'],'action':'skip'})
            self.assertEqual(result.json['status'],'skipped')
            manager.submit_specs.assert_not_called()

    def test_missing_file_can_be_repeated_without_duplicate_warning(self):
        record=self.record(); Path(record['path']).unlink()
        with patch.object(app,'download_store',self.store),patch.object(app,'download_manager') as manager,patch.object(app,'ensure_download_state'):
            response=app.app.test_client().post('/history/action',json={'id':record['id'],'action':'repeat'})
            self.assertEqual(response.status_code,202)
            manager.submit_specs.assert_called_once()

    def test_history_open_uses_stored_path_not_client_input(self):
        record=self.record()
        with patch.object(app,'download_store',self.store),patch.object(app,'ensure_download_state'),patch.object(app.os,'startfile') as open_file:
            response=app.app.test_client().post('/history/action',json={'id':record['id'],'action':'open','path':'evil.exe'})
            self.assertEqual(response.status_code,200)
            open_file.assert_called_once_with(record['path'])


if __name__=='__main__': unittest.main()
