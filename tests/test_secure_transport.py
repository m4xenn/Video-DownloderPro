import unittest
from unittest.mock import Mock,patch
from services.secure_transport import attach_network_guard,pin_requests_session,pin_curl_session,public_addresses
from services.security_policy import UnsafeLink


class SecureTransportTests(unittest.TestCase):
    def test_curl_uses_same_ascii_host_for_dns_pin_and_request(self):
        session=Mock();session.request.return_value=Mock(status_code=200,headers={})
        send=session.request;pin_curl_session(session)
        with patch('services.secure_transport.public_addresses',return_value=['8.8.8.8']) as addresses:
            session.request('GET','https://bücher.example/video')
        addresses.assert_called_once_with('xn--bcher-kva.example',443)
        self.assertEqual(send.call_args.kwargs['url'],'https://xn--bcher-kva.example/video')
    def test_ytdlp_private_url_never_sent(self):
        from yt_dlp import YoutubeDL
        from yt_dlp.networking import Request
        with YoutubeDL({'quiet':True}) as ydl:
            attach_network_guard(ydl)
            with self.assertRaises(Exception):ydl.urlopen(Request('http://127.0.0.1:1/private'))
            self.assertEqual(set(ydl._request_director.handlers),{'Requests','CurlCFFI'})

    def test_requests_pin_socket_to_verified_address(self):
        import requests
        with patch('urllib3.util.connection.create_connection') as connect:
            session=pin_requests_session(requests.Session())
        try:
            pool=session.adapters['https://'].poolmanager.pool_classes_by_scheme['https']
            connection=pool.ConnectionCls('video.example.com',443,timeout=3)
            with patch('services.secure_transport.public_addresses',return_value=['8.8.8.8']):
                connection._new_conn()
            self.assertEqual(connect.call_args.args[0],('8.8.8.8',443))
            self.assertEqual(connection.host,'video.example.com')
            with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('10.0.0.1',443))]):
                with self.assertRaises(UnsafeLink):connection._new_conn()
            self.assertEqual(connect.call_count,1)
        finally:session.close()

    def test_curl_private_redirect_is_not_followed(self):
        response=Mock(status_code=302,headers={'Location':'http://127.0.0.1/private'})
        session=Mock();session.request.return_value=response
        send=session.request
        pin_curl_session(session)
        with patch('services.secure_transport.public_addresses',return_value=['8.8.8.8']):
            with self.assertRaises(UnsafeLink):session.request('GET','https://video.example.com/')
        self.assertEqual(send.call_count,1)
        self.assertFalse(send.call_args.kwargs['allow_redirects'])
        response.close.assert_called_once()

    def test_curl_public_redirect_preserves_method_and_strips_credentials(self):
        response=Mock(status_code=307,headers={'Location':'https://cdn.example.com/video'})
        session=Mock();session.request.side_effect=[response,Mock(status_code=200,headers={})]
        send=session.request;pin_curl_session(session)
        with patch('services.secure_transport.public_addresses',return_value=['8.8.8.8']):
            session.request('POST','https://video.example.com/',data=b'payload',headers={'Cookie':'secret','Authorization':'secret','User-Agent':'browser'})
        self.assertEqual(send.call_args.kwargs['method'],'POST')
        self.assertEqual(send.call_args.kwargs['data'],b'payload')
        self.assertEqual(send.call_args.kwargs['headers'],{'User-Agent':'browser'})
        self.assertEqual(session.curl.setopt.call_count,2)
