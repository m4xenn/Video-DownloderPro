import http.server,threading,unittest,urllib.request,urllib.error
from unittest.mock import patch
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from services.live_network import LiveNetwork,rewrite_dash,rewrite_hls
from services.security_policy import UnsafeLink


class LiveNetworkSecurityTests(unittest.TestCase):
    def test_manifest_rewriting_and_private_references(self):
        make=lambda value:'http://127.0.0.1:1234/token/'+value.rsplit('/',1)[-1]
        manifest=b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key.bin"\n#EXTINF:6,\nsegment.ts\n'
        body=rewrite_hls(manifest,'https://cdn.example.com/live/index.m3u8',make)
        self.assertIn(b'URI="http://127.0.0.1:1234/token/key.bin"',body)
        self.assertIn(b'http://127.0.0.1:1234/token/segment.ts',body)
        mpd=b'<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"><BaseURL>https://cdn.example.com/live/</BaseURL><Period><SegmentTemplate media="segment-$Number%05d$.m4s" initialization="init.mp4"/></Period></MPD>'
        body=rewrite_dash(mpd,'https://video.example.com/manifest.mpd',make)
        self.assertIn(b'$Number%05d$',body);self.assertNotIn(b'https://cdn.example.com',body)
        self.assertTrue(ET.fromstring(body).tag.endswith('MPD'))
        self.assertIn(b'<MPD ',body)  # FFmpeg's DASH probe expects an unprefixed root.
        gateway=LiveNetwork([{}]);gateway.server=type('Server',(),{'server_port':1234})()
        key='data:application/octet-stream;base64,AAAAAAAAAAAAAAAAAAAAAA=='
        self.assertEqual(gateway.url(key,0),key)
        with self.assertRaises(UnsafeLink):rewrite_hls(b'#EXTM3U\nhttp://127.0.0.1/admin\n','https://video.example.com/live',lambda value:gateway.url(value,0))

    def test_real_gateway_blocks_redirects_and_sniffs_opaque_hls(self):
        seen=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                seen.append(self.path)
                if self.path=='/redirect':
                    self.send_response(302);self.send_header('Location',f'http://127.0.0.1:{self.server.server_port}/private');self.end_headers();return
                if self.path=='/opaque':body=b'#EXTM3U\nhttp://127.0.0.1/private.ts\n';mime='application/octet-stream'
                elif self.path=='/normal.m3u8':body=b'#EXTM3U\n#EXTINF:2,\nsegment.ts\n';mime='application/vnd.apple.mpegurl'
                else:body=b'fixture-media-bytes';mime='video/mp2t'
                self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        source=f'http://fixture.example:{server.server_port}'
        gateway=LiveNetwork([{}])
        try:
            # Only the test's simulated public host maps to the owned server.
            # Redirect validation remains enabled and rejects private addresses.
            with patch('services.secure_transport.public_addresses',return_value=['127.0.0.1']):
                normal=gateway.start([source+'/normal.m3u8'])[0]
                with urllib.request.urlopen(normal,timeout=6) as response:body=response.read().decode()
                segment=next(line for line in body.splitlines() if line and not line.startswith('#'))
                self.assertTrue(segment.startswith('http://127.0.0.1:'))
                with urllib.request.urlopen(segment,timeout=6) as response:self.assertEqual(response.read(),b'fixture-media-bytes')
                for path in ('/redirect','/opaque'):
                    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(gateway.url(source+path,0),timeout=6)
                    self.assertEqual(error.exception.code,502)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(urllib.request.Request(normal,headers={'Sec-Fetch-Site':'cross-site'}),timeout=6)
                self.assertEqual(error.exception.code,404)
            self.assertNotIn('/private',seen)
            self.assertTrue(gateway.unsafe)
        finally:gateway.close();server.shutdown();server.server_close()
