import sys,pathlib,unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'src'))
from services.hls_metadata import inspect_hls,extract_hls,ProtectedMediaError,UnsupportedEncryptionError,MAX_MANIFEST_BYTES
from services.diagnostics import error_code
class HlsEvidenceTests(unittest.TestCase):
 def test_clear_vod_duration(self):
  e=inspect_hls(b'\xef\xbb\xbf#EXTM3U\r\n#EXTINF:1.25,\r\na.ts\r\n#EXTINF:2.5,\r\nb.ts\r\n#EXT-X-ENDLIST\r\n')
  self.assertEqual(e['duration'],3.75);self.assertEqual(e['protection'],'clear');self.assertFalse(e['is_live'])
 def test_live_and_master_not_given_fake_duration(self):
  self.assertTrue(inspect_hls('#EXTM3U\n#EXTINF:1,\na.ts')['is_live'])
  e=inspect_hls('#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",URI="a.m3u8"\n#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="s",URI="s.m3u8"\n#EXT-X-STREAM-INF:RESOLUTION=1280x720\nv.m3u8')
  self.assertTrue(e['master']);self.assertIsNone(e['duration']);self.assertEqual(e['audio_tracks'],1);self.assertEqual(e['subtitle_tracks'],1)
 def test_standard_aes_is_not_drm(self):
  for key in ['METHOD=AES-128,URI="https://cdn.example/drm-key"','METHOD=AES-128,KEYFORMAT="identity",URI="key"']:
   self.assertEqual(inspect_hls('#EXTM3U\n#EXT-X-KEY:'+key)['protection'],'aes128')
 def test_real_systems(self):
  for key,system in [('com.apple.streamingkeydelivery','FairPlay'),('urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed','Widevine'),('com.microsoft.playready','PlayReady')]:
   e=inspect_hls('#EXTM3U\n#EXT-X-SESSION-KEY:METHOD=SAMPLE-AES,KEYFORMAT="'+key+'",URI="secret"')
   self.assertEqual(e['protection'],'drm');self.assertEqual(e['systems'],[system]);self.assertNotIn('secret',str(e))
 def test_unknown_encryption_not_mislabeled_as_drm(self):
  for tag in ['METHOD=SAMPLE-AES,KEYFORMAT="identity",URI="key"','METHOD=AES-128,KEYFORMAT="vendor.unknown",URI="key"']:
   self.assertEqual(inspect_hls('#EXTM3U\n#EXT-X-KEY:'+tag)['protection'],'unknown')
  self.assertEqual(error_code(UnsupportedEncryptionError()),'encrypted_unsupported')
  self.assertEqual(error_code(str(UnsupportedEncryptionError())),'encrypted_unsupported')
 def test_none_does_not_erase_protected_period(self):
  e=inspect_hls('#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,URI="skd://private"\n#EXT-X-KEY:METHOD=NONE')
  self.assertEqual(e['systems'],['FairPlay'])
 def test_malformed_and_bounded(self):
  for body in ['<html>denied</html>','#EXTM3U not valid','#EXTM3U\n#EXTINF:NaN,\nx.ts',b'x'*(MAX_MANIFEST_BYTES+1)]:
   with self.assertRaises((ValueError,UnicodeError)):inspect_hls(body)
 def test_no_key_or_license_requests(self):
  ydl=Mock();ydl.params={};response=ydl.urlopen.return_value.__enter__.return_value if hasattr(ydl.urlopen.return_value,'__enter__') else None
  from unittest.mock import MagicMock
  response=Mock();response.url='https://cdn.example/master';response.read.return_value=b'#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,KEYFORMAT="com.widevine",URI="https://license.example/SENSITIVE"'
  cm=MagicMock();cm.__enter__.return_value=response;ydl.urlopen.return_value=cm
  with patch('services.media_discovery.public_url',return_value=True),self.assertRaises(ProtectedMediaError) as caught:extract_hls(ydl,response.url,'id','Title')
  self.assertEqual(ydl.urlopen.call_count,1);self.assertNotIn('SENSITIVE',str(caught.exception));self.assertEqual(error_code(caught.exception),'drm')
 def test_file_permissions_separate_from_drm(self):
  self.assertEqual(error_code(PermissionError('locked')),'file_access_denied')
  self.assertEqual(error_code('[WinError 5] access is denied'),'file_access_denied')
  self.assertEqual(error_code('No space left on device'),'disk_full')
if __name__=='__main__':unittest.main()
