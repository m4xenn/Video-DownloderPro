"""All advertised languages must ship distinct, valid help screenshots."""
import hashlib
import json
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]/'src/static/help'

class LocalizedHelpTests(unittest.TestCase):
 def test_complete_language_topic_matrix(self):
  manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
  self.assertEqual(set(manifest['languages']),{'tr','en','de','es','fr','pt','ru','zh','ja','hi'})
  self.assertEqual(set(manifest['topics']),{'start','formats','playlist','queue','history','settings','troubleshooting'})
  expected={(lang,topic) for lang in manifest['languages'] for topic in manifest['topics']}
  self.assertEqual({(item['language'],item['topic']) for item in manifest['screenshots']},expected)
  hashes=set()
  for item in manifest['screenshots']:
   with self.subTest(language=item['language'],topic=item['topic']):
    path=ROOT/item['path']
    self.assertEqual(path.parent.name,item['language'])
    data=path.read_bytes()
    self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
    width,height=struct.unpack('>II',data[16:24])
    self.assertGreaterEqual(width,300);self.assertGreater(height,100)
    self.assertLessEqual(abs(width-item['width']),1)
    self.assertLessEqual(abs(height-item['height']),1)
    digest=hashlib.sha256(data).hexdigest()
    self.assertNotIn(digest,hashes,'Every locale/topic should have its own rendered image')
    hashes.add(digest)
  self.assertEqual(len(hashes),70)

if __name__=='__main__':unittest.main()
