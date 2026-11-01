import sys,pathlib,json,tempfile,unittest,struct
from unittest.mock import Mock,patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'src'))
from services.output_validation import validate_output,validate_mp4_extent,OutputValidationError
from services.diagnostics import error_code
class OutputTests(unittest.TestCase):
 def extent(self,body):
  with tempfile.TemporaryDirectory(dir='build') as folder:
   file=pathlib.Path(folder)/'fixture.mp4';file.write_bytes(body)
   validate_mp4_extent(file)
 def test_complete_mp4_and_zero_size_terminal_box(self):
  ftyp=struct.pack('>I4s',16,b'ftyp')+b'isom0000'
  self.extent(ftyp+struct.pack('>I4s',12,b'mdat')+b'data')
  self.extent(ftyp+struct.pack('>I4s',0,b'mdat')+b'data')
 def test_truncated_original_with_full_duration_metadata_is_rejected(self):
  ftyp=struct.pack('>I4s',16,b'ftyp')+b'isom0000'
  moov=struct.pack('>I4s',12,b'moov')+b'info'
  for mdat in [struct.pack('>I4s',2000,b'mdat'),struct.pack('>I4sQ',1,b'mdat',6432055465)]:
   with self.assertRaisesRegex(OutputValidationError,'Incomplete MP4 source'):self.extent(ftyp+moov+mdat+b'partial')
 def test_extended_header_and_trailing_header_must_be_complete(self):
  ftyp=struct.pack('>I4s',16,b'ftyp')+b'isom0000'
  for tail in [b'abc',struct.pack('>I4s',1,b'mdat')+b'abc',struct.pack('>I4s',4,b'mdat')]:
   with self.assertRaises(OutputValidationError):self.extent(ftyp+tail)
 def test_other_containers_are_left_for_ffprobe(self):self.extent(b'not an MP4 fixture')
 def probe(self,streams,expect=True):
  with tempfile.TemporaryDirectory(dir='build') as folder:
   probe=pathlib.Path(folder)/'ffprobe.exe';probe.write_bytes(b'test executable')
   with patch('services.output_validation.subprocess.run',return_value=Mock(stdout=json.dumps({'streams':streams}).encode())):
    return validate_output('download.mp4',folder,expect)
 def test_missing_audio_cannot_pass_when_source_promised_audio(self):
  with tempfile.TemporaryDirectory(dir='build') as folder:
   (pathlib.Path(folder)/'ffprobe.exe').write_bytes(b'fixture')
   with patch('services.output_validation.subprocess.run',return_value=Mock(stdout=json.dumps({'streams':[{'codec_type':'video'}]}).encode())),self.assertRaisesRegex(OutputValidationError,'audio'):
    validate_output('download.mp4',folder,True,expect_audio=True)
 def test_remuxed_short_preview_cannot_pass_as_full_recording(self):
  with tempfile.TemporaryDirectory(dir='build') as folder:
   (pathlib.Path(folder)/'ffprobe.exe').write_bytes(b'fixture')
   response=Mock(stdout=json.dumps({'streams':[{'codec_type':'video'},{'codec_type':'audio'}],'format':{'duration':'300'}}).encode())
   with patch('services.output_validation.subprocess.run',return_value=response),self.assertRaisesRegex(OutputValidationError,'duration'):
    validate_output('download.mp4',folder,True,expected_duration=15890,expect_audio=True)
 def test_unreadable_tail_is_rejected(self):
  with tempfile.TemporaryDirectory(dir='build') as folder:
   (pathlib.Path(folder)/'ffprobe.exe').write_bytes(b'fixture')
   responses=[Mock(stdout=json.dumps({'streams':[{'codec_type':'video'}],'format':{'duration':'120'}}).encode()),Mock(stdout=b'{"packets":[]}',stderr=b'')]
   with patch('services.output_validation.subprocess.run',side_effect=responses),self.assertRaisesRegex(OutputValidationError,'End of output'):
    validate_output('download.mp4',folder,True,expected_duration=120)
 def test_video_audio(self):self.assertEqual(self.probe([{'codec_type':'video'},{'codec_type':'audio'}]),{'video':True,'audio':True})
 def test_error_code_survives_queue_serialization(self):self.assertEqual(error_code(str(OutputValidationError('missing video'))),'invalid_media')
 def test_audio_not_falsely_completed_as_video(self):
  with self.assertRaises(OutputValidationError):self.probe([{'codec_type':'audio'}])
 def test_album_art_is_not_video(self):
  with self.assertRaises(OutputValidationError):self.probe([{'codec_type':'audio'},{'codec_type':'video','disposition':{'attached_pic':1}}])
 def test_audio_output_accepts_audio(self):self.assertTrue(self.probe([{'codec_type':'audio'}],False)['audio'])
 def test_empty_streams(self):
  with self.assertRaises(OutputValidationError):self.probe([])
if __name__=='__main__':unittest.main()
