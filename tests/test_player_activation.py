"""Activation chooses a single public player and defers verification to the user."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.player_activation import activation_document,inspection_script
from services.webview_frames import merge_frames

PAGE='https://watch.example/episode'
PLAYER='https://player.example/embed'


class ActivationTests(unittest.TestCase):
    def snapshot(self):
        return {'url':PAGE,'players':[{'document':PLAYER,'area':300000}]}

    def test_one_large_player(self):
        self.assertEqual(activation_document(self.snapshot()),PLAYER)

    def test_verification_and_drm_stop_activation(self):
        for flag in ('verification','drm'):
            self.assertIsNone(activation_document(dict(self.snapshot(),**{flag:True})))

    def test_similar_unrelated_players_are_ambiguous(self):
        snapshot=self.snapshot()
        snapshot['players'].append({'document':PAGE,'area':290000})
        self.assertIsNone(activation_document(snapshot))

    def test_duplicate_same_player_document_is_not_ambiguous(self):
        snapshot=self.snapshot();snapshot['players']*=2
        self.assertEqual(activation_document(snapshot),PLAYER)

    def test_parent_ad_waits_for_larger_embedded_player(self):
        snapshot={'players':[{'document':PAGE,'area':10000}],
                  'embeds':[{'url':PLAYER,'area':300000}]}
        self.assertIsNone(activation_document(snapshot))

    def test_private_and_tiny_players_are_not_started(self):
        for document,area in [('http://127.0.0.1/private',300000),(PLAYER,1)]:
            self.assertIsNone(activation_document({'players':[{'document':document,'area':area}]}))

    def test_child_verification_propagates_before_activation(self):
        root={'url':PAGE,'embeds':[{'url':PLAYER,'area':300000}]}
        frame={'key':1,'parent':None,'snapshot':dict(self.snapshot(),url=PLAYER,verification=True)}
        merged=merge_frames(root,[frame])
        self.assertTrue(merged['verification'])
        self.assertIsNone(activation_document(merged))

    def test_script_target_is_json_encoded(self):
        self.assertIn('https://example.com/\\"',inspection_script('https://example.com/"'))


if __name__=='__main__':unittest.main()
