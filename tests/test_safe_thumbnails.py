import io,unittest
from unittest.mock import MagicMock,patch
from PIL import Image
from services import safe_thumbnails as covers


class SafeThumbnailTests(unittest.TestCase):
    def test_metadata_only_exposes_local_cover_urls(self):
        data={'items':[{'thumbnail':'http://127.0.0.1/private'},{'thumbnail':'https://cdn.example.com/cover.jpg'},{'thumbnail':'/previews/'+'a'*32+'.jpg'}]}
        self.assertTrue(covers.sanitize(data))
        self.assertEqual(data['items'][0]['thumbnail'],'/static/media-placeholder.svg')
        self.assertRegex(data['items'][1]['thumbnail'],r'^/safe-thumbnails/[a-f0-9]{32}\.jpg$')
        self.assertTrue(data['items'][2]['thumbnail'].startswith('/previews/'))

    def test_cover_is_reencoded_and_non_images_are_rejected(self):
        output=io.BytesIO();Image.new('RGB',(900,600),'red').save(output,format='PNG')
        for content,expected in ((output.getvalue(),True),(b'<svg onload="alert(1)"></svg>',False),(b'x'*(4*1024*1024+1),False)):
            local=covers.register('https://cdn.example.com/'+str(len(content))+'.png')
            identity=local.rsplit('/',1)[1][:-4]
            session=MagicMock();session.__enter__.return_value=session
            response=session.get.return_value.__enter__.return_value
            response.headers={};response.raw.read1.side_effect=[content,b'']
            with patch('requests.Session',return_value=session),patch('services.secure_transport.pin_requests_session',side_effect=lambda value:value):
                result=covers.render(identity)
            self.assertEqual(result is not None,expected)
            if expected:
                image=Image.open(io.BytesIO(result));self.assertEqual(image.format,'JPEG');self.assertLessEqual(max(image.size),480)

    def test_unknown_cover_cannot_trigger_network(self):
        with patch('requests.Session') as session:
            self.assertIsNone(covers.render('unknown'));session.assert_not_called()
