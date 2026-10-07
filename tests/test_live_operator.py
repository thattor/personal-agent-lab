import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.live_evidence import EvidenceJournal, verify_journal
from scripts.live_operator import AuditedNative, clean_candidate
from pal.native import AccessProof


class LiveOperatorTests(unittest.TestCase):
    def test_live_owner_cannot_bypass_operator_proof_consumption(self):
        import time
        from scripts.live_runner import MatrixRunner
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            owner = AuditedNative(AccessProof(time.time(),True))
            with self.assertRaises(ValueError):
                MatrixRunner(root,Path(directory)/'run',
                             root/'tests/fixtures/p002_real_ui_v1.json',owner,
                             scope='live_synthetic',candidate='unverified')
            self.assertFalse((Path(directory)/'run').exists())

    def test_dirty_or_wrong_candidate_rejected_before_auth(self):
        with patch('scripts.live_operator.git_read', side_effect=['expected',' M pal/runtime.py']):
            with self.assertRaises(ValueError): clean_candidate(Path('.'),'expected')
        with patch('scripts.live_operator.git_read', return_value='other'):
            with self.assertRaises(ValueError): clean_candidate(Path('.'),'expected')

    def test_supervisor_lifecycle_is_observation_not_cli_pid_or_human_proof(self):
        import os
        import time
        class Process:
            pid = 12345
            returncode = 0
        with tempfile.TemporaryDirectory() as directory:
            journal = EvidenceJournal(Path(directory)/'events.jsonl','scripted')
            owner = AuditedNative(AccessProof(time.time(),True),max_calls=20)
            owner.sink = journal.append
            read, write = os.pipe()
            try:
                owner.register(Process(),write)
                # Use the same owned object, as supervised_text does.
                process = next(iter(owner._calls))
                owner.unregister(process)
                owner.stop()
            finally:
                os.close(read); os.close(write); journal.close()
            records = verify_journal(Path(directory)/'events.jsonl')
            self.assertEqual([r['event'] for r in records],
                             ['native.supervisor.started','native.supervisor.finished'])
            self.assertEqual(records[0]['supervisor_pid'],12345)
            self.assertNotIn('cli_pid',records[0])
            self.assertEqual(records[0]['native_slot_attempt'],0)
