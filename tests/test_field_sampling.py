"""Sampling tool contracts: bounded reads, protocol selection and error separation."""
import sys,unittest
from pathlib import Path
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests'),str(ROOT/'scripts')]
from probe_media_sample import sample_media
from site_matrix import summarize

class Reply:
    def __init__(self,body,url='https://media.example/asset',mime='video/mp4'):
        self.body=body;self.url=url;self.headers={'Content-Type':mime};self.status=206;self.reads=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n):self.reads.append(n);return self.body[:n]

class SampleTests(unittest.TestCase):
    def test_direct_read_is_bounded(self):
        response=Reply(b'video'*10000);ydl=Mock();ydl.urlopen.return_value=response
        result=sample_media(ydl,{'url':'https://media.example/video.mp4'},allowed=lambda *a,**kw:True)
        self.assertEqual(result['sample_bytes'],16384);self.assertEqual(response.reads,[16384])
    def test_hls_follows_variant_then_segment(self):
        master=Reply(b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nlow.m3u8\n',url='https://media.example/master.m3u8')
        playlist=Reply(b'#EXTM3U\n#EXTINF:5,\npart.ts\n',url='https://media.example/low.m3u8')
        media=Reply(b'valid media')
        ydl=Mock();ydl.urlopen.side_effect=[master,playlist,media]
        result=sample_media(ydl,{'url':'https://media.example/master.m3u8','protocol':'m3u8_native'},allowed=lambda *a,**kw:True)
        self.assertEqual(result['sample_kind'],'hls-segment');self.assertEqual(media.reads,[16384])
    def test_dash_uses_media_fragment(self):
        ydl=Mock();ydl.urlopen.return_value=Reply(b'fragment')
        result=sample_media(ydl,{'url':'https://media.example/manifest.mpd','fragment_base_url':'https://media.example/','fragments':[{'url':'init.mp4'},{'url':'chunk.m4s','duration':5}]},allowed=lambda *a,**kw:True)
        self.assertEqual(result['sample_kind'],'dash-fragment')
        self.assertEqual(ydl.urlopen.call_args.args[0].url,'https://media.example/chunk.m4s')
    def test_html_response_is_rejected(self):
        ydl=Mock();ydl.urlopen.return_value=Reply(b'<html>denied</html>',mime='text/html')
        with self.assertRaises(ValueError):sample_media(ydl,{'url':'https://media.example/video.mp4'},allowed=lambda *a,**kw:True)
    def test_encrypted_hls_sample_is_not_read(self):
        playlist=Reply(b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\n#EXTINF:5,\npart.ts\n',url='https://media.example/master.m3u8')
        ydl=Mock();ydl.urlopen.return_value=playlist
        with self.assertRaisesRegex(ValueError,'Encrypted sample not inspected'):
            sample_media(ydl,{'url':'https://media.example/master.m3u8','protocol':'m3u8_native'},allowed=lambda *a,**kw:True)
        self.assertEqual(ydl.urlopen.call_count,1)

    def test_non_public_sample_never_requested(self):
        ydl=Mock()
        with self.assertRaises(ValueError):sample_media(ydl,{'url':'http://localhost/video.mp4'},allowed=lambda *a,**kw:False)
        ydl.urlopen.assert_not_called()
    def test_sample_failure_does_not_erase_discovery(self):
        result=summarize({'id':'case','url':'https://example.com/'},{'status':'resolved','sample_status':'failed','sample_error_code':'access_denied'},1)
        self.assertEqual(result['outcome'],'automatic');self.assertEqual(result['sample_status'],'failed')

if __name__=='__main__':unittest.main()
