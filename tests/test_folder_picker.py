import copy,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from services.folder_service import open_folder_dialog,FolderDialogError,_dialog_lock
from services.ui_messages import catalog
from state.app_state import state
import app,webview

class FolderPickerTests(unittest.TestCase):
 def setUp(self):
  self.saved=copy.deepcopy(state);self.addCleanup(self.restore)
 def restore(self):state.clear();state.update(self.saved)
 def test_uses_owned_native_folder_picker_without_tkinter(self):
  window=Mock();window.create_file_dialog.return_value=('C:/Çalışmalar/動画',)
  with patch('webview.windows',[window]):self.assertEqual(open_folder_dialog(),'C:/Çalışmalar/動画')
  window.create_file_dialog.assert_called_once_with(webview.FileDialog.FOLDER)
 def test_cancel_is_distinct_from_failure(self):
  window=Mock();window.create_file_dialog.return_value=None
  with patch('webview.windows',[window]):self.assertIsNone(open_folder_dialog())
  window.create_file_dialog.side_effect=RuntimeError('backend failure')
  with patch('webview.windows',[window]),self.assertRaises(FolderDialogError) as error:open_folder_dialog()
  self.assertEqual(error.exception.key,'folder_dialog_failed')
 def test_malformed_dialog_result_is_not_used_as_a_path(self):
  for result in ['C:/raw-string',('a','b'),(17,),('',)]:
   window=Mock();window.create_file_dialog.return_value=result
   with patch('webview.windows',[window]),self.assertRaises(FolderDialogError):open_folder_dialog()
 def test_browser_only_mode_reports_desktop_requirement(self):
  with patch('webview.windows',[]),patch('services.folder_service.platform.system',return_value='Windows'),self.assertRaises(FolderDialogError) as error:open_folder_dialog()
  self.assertEqual(error.exception.key,'folder_desktop_required')
 def test_concurrent_request_does_not_create_another_dialog(self):
  _dialog_lock.acquire()
  try:
   with self.assertRaises(FolderDialogError) as error:open_folder_dialog()
   self.assertEqual(error.exception.key,'folder_dialog_busy')
  finally:_dialog_lock.release()
  window=Mock();window.create_file_dialog.return_value=None
  with patch('webview.windows',[window]):self.assertIsNone(open_folder_dialog())
 def test_cancel_and_failure_preserve_existing_destination(self):
  state['current_download_path']='C:/Previous destination';client=app.app.test_client()
  with patch('app.open_folder_dialog',return_value=None):
   response=client.post('/select-folder');self.assertEqual(response.json['status'],'cancel')
  self.assertEqual(state['current_download_path'],'C:/Previous destination')
  with patch('app.open_folder_dialog',side_effect=FolderDialogError()):
   response=client.post('/select-folder');self.assertEqual(response.status_code,503)
   self.assertEqual(response.json['message_key'],'folder_dialog_failed')
  self.assertEqual(state['current_download_path'],'C:/Previous destination')
 def test_selected_path_is_committed_only_after_success(self):
  with patch('app.open_folder_dialog',return_value='C:/選択されたフォルダー'):
   response=app.app.test_client().post('/select-folder')
  self.assertEqual(response.json['path'],'C:/選択されたフォルダー');self.assertEqual(state['current_download_path'],response.json['path'])
 def test_dialog_failures_follow_all_ten_application_languages(self):
  for lang,copy in catalog().items():
   state.update(current_lang=lang,ui_language_selected=True)
   with patch('app.open_folder_dialog',side_effect=FolderDialogError()):response=app.app.test_client().post('/select-folder')
   self.assertEqual(response.json['message'],copy['folder_dialog_failed'])
   with patch('app.open_folder_dialog',side_effect=FolderDialogError('folder_dialog_busy')):response=app.app.test_client().post('/select-folder')
   self.assertEqual(response.status_code,409);self.assertEqual(response.json['message_key'],'folder_dialog_busy')

if __name__=='__main__':unittest.main()
