from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.source_validation import validate_embedded_info,validate_media_sample


class SourceValidationTests(unittest.TestCase):
    def source(self):return {'url':'https://cdn.example/video.mp4','ext':'mp4','vcodec':'h264','acodec':'aac','duration':120}
    def test_valid_source(self):
        info=self.source();self.assertIs(validate_embedded_info(info),info)
    def test_audio_only_source_is_supported(self):
        info=dict(self.source(),vcodec='none',acodec='aac',ext='m4a');validate_embedded_info(info)
    def test_missing_duration_and_live_are_supported(self):
        info=self.source();info.pop('duration');validate_embedded_info(info)
        validate_embedded_info(dict(info,is_live=True,duration=0))
    def test_drm_and_all_protected_formats_rejected(self):
        for info in [dict(self.source(),has_drm=True),{'formats':[dict(self.source(),has_drm=True)]}]:
            with self.assertRaisesRegex(ValueError,'DRM'):validate_embedded_info(info)
    def test_clear_format_among_protected_is_accepted(self):
        validate_embedded_info({'formats':[dict(self.source(),has_drm=True),self.source()]})
    def test_empty_and_non_http_and_storyboard_rejected(self):
        for info in [{},{'url':'blob:local'},dict(self.source(),ext='mhtml'),dict(self.source(),vcodec='none',acodec='none')]:
            with self.assertRaises(ValueError):validate_embedded_info(info)
    def test_invalid_duration_rejected(self):
        for value in (0,-1,float('inf'),float('nan'),True,'120'):
            with self.assertRaises(ValueError):validate_embedded_info(dict(self.source(),duration=value))
    def test_playlist_cannot_be_promoted_to_one_embedded_video(self):
        with self.assertRaises(ValueError):validate_embedded_info(dict(self.source(),_type='playlist'))
    def test_sample_rejects_html_error_even_with_http_200(self):
        for body,mime in [(b'',''),(b'<html>denied</html>','application/octet-stream'),(b'{}','application/json'),(b'error','text/html')]:
            with self.assertRaises(ValueError):validate_media_sample(body,mime)
    def test_sample_accepts_binary_and_encrypted_media(self):
        self.assertEqual(validate_media_sample(b'\x47\x00\x11\x44','video/mp2t'),4)
        self.assertEqual(validate_media_sample(b'\xa3\x17\x89\xff','application/octet-stream'),4)


if __name__=='__main__':unittest.main()
