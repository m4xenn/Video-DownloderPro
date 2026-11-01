"""Exercise real yt-dlp selection, API validation and legacy history migration."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from services.track_selection import apply_tracks, normalize_tracks, track_choices, validate_subtitle_choice
from services.download_store import DownloadStore
from services.media_catalog import MediaCatalog
from services.source_recovery import source_checkpoint, can_resume_embedded
from core.format_resolver import get_ydl_opts
from yt_dlp import YoutubeDL
import app
from state.app_state import state

FORMATS = [dict(format_id='video', url='https://example.com/v', ext='mp4',
                vcodec='avc1', acodec='none', height=720)] + [
    dict(format_id=lang, url='https://example.com/' + lang, ext='m4a',
         vcodec='none', acodec='aac', language=lang, abr=128)
    for lang in ['en', 'tr']]


class TrackSelectionTests(unittest.TestCase):
    def select(self, language, formats=FORMATS):
        opts = get_ydl_opts('video', 'max', str(ROOT), 0, True, lambda _: None, '')
        apply_tracks(opts, dict(audio_language=language, subtitle_language='tr', embed_subs=True))
        with YoutubeDL(dict(quiet=True, logger=Mock(), skip_download=True, format=opts['format'])) as ydl:
            return ydl.process_ie_result(dict(id='fixture', title='Fixture', formats=formats,
                                             extractor_key='EmbeddedMedia', duration=3), download=False)

    def test_actual_selector_honours_each_audio_language(self):
        for language in ['en', 'tr']:
            info = self.select(language)
            self.assertEqual(info['requested_formats'][1]['language'], language)
            self.assertEqual(info['requested_formats'][0]['vcodec'], 'avc1')

    def test_missing_language_fails_without_fallback(self):
        with self.assertRaises(Exception):
            self.select('de')

    def test_language_cannot_inject_selector(self):
        for value in ['en]/best', '', None, ['en'], 'auto/best']:
            with self.assertRaises(ValueError):
                normalize_tracks(dict(audio_language=value))

    def test_choices_are_declared_clear_tracks_only(self):
        choices = track_choices(dict(formats=FORMATS + [dict(FORMATS[-1], language='de', has_drm=True)],
                                    subtitles={'tr': [{'url': 'https://example.com/sub'}], 'en': []}))
        self.assertEqual(choices, dict(audio_languages=['en', 'tr'], subtitle_languages=['tr']))

    def test_resume_rejects_changed_audio_language(self):
        before = self.select('en')
        self.assertTrue(can_resume_embedded(source_checkpoint(before), before))
        self.assertFalse(can_resume_embedded(source_checkpoint(before), self.select('tr')))

    def test_subtitles_use_exact_choice_and_audio_export_resets_subtitles(self):
        opts = {'format': 'bestaudio/best'}
        apply_tracks(opts, dict(embed_subs=True, subtitle_language='tr'))
        self.assertEqual(opts['subtitleslangs'], ['tr'])
        self.assertEqual(normalize_tracks(dict(format='audio', embed_subs=True, subtitle_language='tr'))['subtitle_language'], 'all')

    def test_disappearing_subtitle_fails_before_download(self):
        options=dict(format='video',embed_subs=True,subtitle_language='tr')
        validate_subtitle_choice(dict(subtitles={'tr':[{'url':'https://example.com/sub'}]}),options)
        with self.assertRaises(ValueError):validate_subtitle_choice(dict(subtitles={'en':[{}]}),options)

    def test_api_accepts_only_cached_single_source_languages(self):
        catalog = MediaCatalog(); catalog.remember('https://example.com/a', dict(formats=FORMATS))
        with patch.dict(state, current_download_path=str(ROOT)), patch.object(app, 'ensure_download_state'), patch.object(app, 'media_catalog', catalog), patch.object(app, 'prepare_download', return_value=({'status': 'success'}, 202)) as submit:
            client = app.app.test_client()
            data = dict(urls=['https://example.com/a'], format='video', quality='max', audio_language='tr')
            self.assertEqual(client.post('/download', json=data).status_code, 202)
            self.assertEqual(submit.call_args.args[1]['audio_language'], 'tr')
            for changes in [dict(audio_language='de'), dict(is_playlist=True), dict(urls=['https://example.com/a', 'https://example.com/b'])]:
                self.assertEqual(client.post('/download', json=dict(data, **changes)).status_code, 400)

    def test_history_migrates_old_schema_and_distinguishes_languages(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as folder:
            path = Path(folder)/'history.sqlite3'; output = Path(folder)/'video.mp4'; output.write_bytes(b'fixture')
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE history (id TEXT PRIMARY KEY, media_key TEXT, url TEXT, title TEXT, thumbnail TEXT, format TEXT, quality TEXT, embed_subs INTEGER, path TEXT, size INTEGER, completed_at TEXT)')
                db.execute('INSERT INTO history VALUES (?,?,?,?,?,?,?,?,?,?,?)', ('old','key','https://example.com/a','Title','','video','max',0,str(output),7,'2026-01-01'))
            db.close()
            store = DownloadStore(path)
            self.assertEqual(store.get_history('old')['audio_language'], 'auto')
            record = dict(store.get_history('old'), id='new', track_options=json.dumps(dict(audio_language='tr', subtitle_language='all')))
            store.commit_queue([], completed=[record])
            self.assertEqual(store.get_history('new')['audio_language'], 'tr')
            self.assertEqual([r['id'] for r in store.duplicates('key',record['url'],dict(format='video',quality='max',embed_subs=False,audio_language='tr'))], ['new'])

if __name__ == '__main__':
    unittest.main()
