"""Filesystem collisions and simultaneous output reservations."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from core.output_paths import reserve_output


class OutputPathTests(unittest.TestCase):
    def test_existing_other_format_and_intermediate_are_protected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            base = Path(directory) / 'same [id]'
            base.with_suffix('.mp4').write_bytes(b'completed video')
            Path(str(base) + ' (1).webm.part').write_bytes(b'partial media')
            lease = reserve_output(str(base))
            try:
                self.assertEqual(lease.base, str(base) + ' (2)')
            finally:
                lease.release()

    def test_parallel_workers_receive_distinct_stems(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            base = str(Path(directory) / 'same')
            leases = []
            try:
                with ThreadPoolExecutor(max_workers=8) as workers:
                    leases = list(workers.map(lambda _: reserve_output(base), range(16)))
                self.assertEqual(len({lease.base for lease in leases}), 16)
            finally:
                for lease in leases:
                    lease.release()
            lease = reserve_output(base)
            try:
                self.assertEqual(lease.base, base)
            finally:
                lease.release()

    def test_resume_keeps_own_partial_but_rejects_active_owner(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            base = str(Path(directory) / 'same')
            Path(base + '.mp4.part').write_bytes(b'partial')
            lease = reserve_output(base, resume=True)
            try:
                self.assertEqual(lease.base, base)
                with self.assertRaises(ValueError):
                    reserve_output(base, resume=True)
                other = reserve_output(base)
                try:
                    self.assertNotEqual(other.base, base)
                finally:
                    other.release()
            finally:
                lease.release()

    def test_similar_title_does_not_block_unrelated_filename(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            base = str(Path(directory) / 'same')
            Path(base + 'thing.mp4').write_bytes(b'unrelated')
            lease = reserve_output(base)
            try:
                self.assertEqual(lease.base, base)
            finally:
                lease.release()
