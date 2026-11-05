import re
import unittest
from unittest.mock import patch
from services import notification_service as notifications
from services.ui_messages import catalog, message
from utils.download_settings import normalize_settings
from state.app_state import state
import app


class NotificationPreferencesTests(unittest.TestCase):
    def test_notification_policy(self):
        for mode in ('always','background','never'):
            for foreground in (True,False):
                with self.subTest(mode=mode,foreground=foreground), \
                     patch.object(notifications.platform,'system',return_value='Windows'), \
                     patch('utils.file_helpers.load_settings',return_value={'notification_mode':mode}), \
                     patch.object(notifications,'is_app_foreground',return_value=foreground), \
                     patch.object(notifications.threading,'Thread') as thread:
                    expected=mode=='always' or mode=='background' and not foreground
                    self.assertEqual(notifications.show_notification('App','Done'),expected)
                    self.assertEqual(thread.called,expected)
                    if expected:thread.return_value.start.assert_called_once()

    def test_catalog_complete_and_placeholders_match(self):
        copies=catalog()
        self.assertEqual(len(copies),10)
        for language,copy in copies.items():
            self.assertEqual(set(copy),set(copies['en']),language)
            for key,text in copy.items():
                self.assertEqual(set(re.findall(r'\{\w+\}',text)),set(re.findall(r'\{\w+\}',copies['en'][key])),(language,key))

    def test_foreground_owner_and_other_process(self):
        from unittest.mock import Mock
        for owner_pid,expected in ((notifications.os.getpid(),True),(notifications.os.getpid()+1,False)):
            api=Mock()
            api.GetForegroundWindow.return_value=123
            api.GetAncestor.return_value=456
            def pid(handle,pointer):
                pointer._obj.value=owner_pid if handle==456 else notifications.os.getpid()+1
            api.GetWindowThreadProcessId.side_effect=pid
            with patch('ctypes.WinDLL',return_value=api):self.assertEqual(notifications.is_app_foreground(),expected)

    def test_notification_uses_latest_ui_language(self):
        saved=dict(state)
        try:
            state.update(ui_language_selected=True,current_lang='fr')
            self.assertEqual(message('downloads_complete'),catalog()['fr']['downloads_complete'])
            state['current_lang']='de'
            self.assertEqual(message('downloads_complete'),catalog()['de']['downloads_complete'])
        finally:state.clear();state.update(saved)

    def test_api_errors_follow_active_language(self):
        saved=dict(state)
        try:
            state.update(ui_language_selected=True,current_lang='fr')
            response=app.app.test_client().post('/save-settings',json=[])
            self.assertEqual(response.status_code,400)
            self.assertEqual(response.json['message'],message('invalid_settings','fr'))
            self.assertEqual(response.json['message_key'],'invalid_settings')
            state['current_lang']='de'
            self.assertEqual(app.app.test_client().post('/save-settings',json=[]).json['message'],message('invalid_settings','de'))
        finally:state.clear();state.update(saved)

    def test_settings_preserve_and_validate_preference(self):
        self.assertEqual(normalize_settings({})['notification_mode'],'always')
        for mode in ('always','background','never'):
            self.assertEqual(normalize_settings({'notification_mode':mode,'language':'fr'})['notification_mode'],mode)
        for invalid in ('sometimes',[],None):
            with self.assertRaises(ValueError):normalize_settings({'notification_mode':invalid})

    def test_settings_api_round_trip(self):
        settings=normalize_settings({'language':'fr'})
        with patch.object(app,'load_settings',side_effect=lambda:dict(settings)), \
             patch.object(app,'save_settings_to_file',side_effect=lambda value:settings.update(value)), \
             patch.object(app.download_manager,'check_configuration'), \
             patch.object(app.download_manager,'configure'):
            client=app.app.test_client()
            self.assertEqual(client.post('/save-settings',json={'notification_mode':'background'}).status_code,200)
            self.assertEqual(client.get('/get-settings').json['notification_mode'],'background')
            self.assertEqual(settings['language'],'fr')
            self.assertEqual(client.post('/save-settings',json={'notification_mode':'wrong'}).status_code,400)
            self.assertEqual(settings['notification_mode'],'background')
