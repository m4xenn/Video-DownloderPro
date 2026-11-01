import io,struct,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.media_preflight import inspect_mp4,probe_mp4,preflight_media,PartialSourceError,NonPublicMediaError
from services.source_recovery import source_checkpoint,can_resume_embedded
from services.diagnostics import error_code

def box(kind,body):return struct.pack('>I4s',len(body)+8,kind)+body
def movie(payload=b'payload',declared=None):
    mvhd=bytes(12)+struct.pack('>II',1000,120000)+bytes(20)
    return box(b'ftyp',b'isom0000')+box(b'moov',box(b'mvhd',mvhd))+(struct.pack('>I4sQ',1,b'mdat',declared) if declared else struct.pack('>I4s',len(payload)+8,b'mdat'))+payload

class PreflightTests(unittest.TestCase):
 def test_non_public_source_is_not_downgraded_to_unknown(self):
  ydl=Mock();info={'url':'http://127.0.0.1/private.mp4','protocol':'http','ext':'mp4'}
  with patch('services.media_preflight.public_url',return_value=False),self.assertRaises(NonPublicMediaError):preflight_media(ydl,info)
  ydl.urlopen.assert_not_called()
 def test_preflight_respects_cancellation_without_network_access(self):
  from services.source_operation import source_operation
  from core.bandwidth import DownloadPaused
  ydl=Mock();info={'url':'https://cdn.example/file.mp4','protocol':'https','ext':'mp4'}
  with patch('services.media_preflight.public_url',return_value=True),source_operation(cancelled=lambda:True),self.assertRaises(DownloadPaused):preflight_media(ydl,info)
  ydl.urlopen.assert_not_called()
 def test_content_query_parameters_are_not_discarded_for_resume_identity(self):
  body=movie();ydl=Mock()
  class Response(io.BytesIO):
   status=206
   headers={'Content-Range':f'bytes 0-{len(body)-1}/{len(body)}','ETag':'"same-tag"'}
  def response(request):
   result=Response(body);result.url=request.url;return result
  ydl.urlopen.side_effect=response
  with patch('services.media_preflight.public_url',return_value=True):
   identities=[probe_mp4(ydl,{'url':'https://cdn.example/v.mp4?'+query})['representation']['resource'] for query in ['id=A&token=old','id=A&token=new','id=B&token=new']]
  self.assertEqual(identities[0],identities[1]);self.assertNotEqual(identities[1],identities[2])
 def inspect(self,body):return inspect_mp4(lambda offset,count:body[offset:offset+count],len(body))
 def test_complete_structure_is_checked_without_claiming_full_playback(self):
  result=self.inspect(movie());self.assertEqual(result['status'],'container_checked');self.assertEqual(result['duration'],120)
 def test_full_duration_does_not_hide_truncated_payload(self):
  result=self.inspect(movie(declared=6_400_000_000));self.assertEqual(result['status'],'partial');self.assertEqual(result['duration'],120);self.assertGreater(result['declared_bytes'],result['available_bytes'])
 def test_sparse_large_mdat_is_skipped_without_reading_its_payload(self):
  reads=[];body=movie();mdat=body.index(b'mdat')-4;end=1_000_000_000
  prefix=body[:mdat]+struct.pack('>I4sQ',1,b'mdat',end-mdat)
  def read(offset,count):reads.append(count);return prefix[offset:offset+count].ljust(count,b'\0')
  self.assertEqual(inspect_mp4(read,end)['status'],'container_checked');self.assertLess(sum(reads),65536)
 def test_strong_representation_hash_has_no_tokens(self):
  body=movie();ydl=Mock()
  class Response(io.BytesIO):
   status=206;url='https://cdn.example/file.mp4?token=private'
   headers={'Content-Range':f'bytes 0-{len(body)-1}/{len(body)}','ETag':'"private-representation"'}
  ydl.urlopen.return_value=Response(body)
  with patch('services.media_preflight.public_url',return_value=True):result=probe_mp4(ydl,{'url':Response.url})
  self.assertIn('representation',result);self.assertNotIn('private',str(result));self.assertNotIn('cdn.example',str(result))
 def test_unknown_or_weak_etag_never_authorizes_changed_url_resume(self):
  info={'id':'v','duration':120,'extractor_key':'EmbeddedMedia','url':'https://cdn.example/v?old','protocol':'https','ext':'mp4','language':'tr'}
  old=source_checkpoint(info);self.assertFalse(can_resume_embedded(old,dict(info,url='https://cdn.example/v?new')))
 def test_changed_signed_url_requires_same_strong_resource_tag_size_and_tracks(self):
  representation={'resource':'origin-and-path-hash','etag':'strong-etag-hash','size':1000}
  info={'id':'v','duration':120,'extractor_key':'EmbeddedMedia','url':'https://cdn.example/v?old','protocol':'https','ext':'mp4','language':'tr','_representation':representation}
  old=source_checkpoint(info);renewed=dict(info,url='https://cdn.example/v?new')
  self.assertTrue(can_resume_embedded(old,renewed))
  for key,value in [('resource','different'),('etag','different'),('size',2000)]:
   self.assertFalse(can_resume_embedded(old,dict(renewed,_representation=dict(representation,**{key:value}))))
  self.assertFalse(can_resume_embedded(old,dict(renewed,language='en')))
 def test_typed_partial_error_survives_serialization(self):self.assertEqual(error_code(str(PartialSourceError())),'partial_source')
 def test_live_sources_are_not_range_probed(self):
  ydl=Mock();info={'is_live':True};self.assertIs(preflight_media(ydl,info),info);ydl.urlopen.assert_not_called()

if __name__=='__main__':unittest.main()
