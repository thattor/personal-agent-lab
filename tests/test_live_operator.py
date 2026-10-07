import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.live_evidence import EvidenceJournal, verify_journal
from scripts.live_operator import AuditedNative, build_live, clean_candidate
from pal.native import AccessProof


class LiveOperatorTests(unittest.TestCase):
    def test_runner_teardown_continues_when_terminal_evidence_fails(self):
        from scripts.live_runner import MatrixRunner
        runner = object.__new__(MatrixRunner)
        runner.closed = False
        runner.gate = Mock()
        runner.gate.close_run.side_effect = OSError('injected terminal evidence failure')
        runner.watchdog = Mock()
        runner._teardown_host = Mock()
        runner.journal = Mock()
        with self.assertRaisesRegex(OSError, 'injected terminal evidence failure'):
            runner.close()
        runner.watchdog.close.assert_called_once_with()
        runner._teardown_host.assert_called_once_with()
        runner.journal.close.assert_called_once_with()

    def test_config_record_failure_closes_constructed_runner(self):
        root = Path(__file__).resolve().parents[1]
        runner = Mock()
        runner.journal.append.side_effect = OSError('injected evidence failure')
        proof = Mock()
        owner = Mock()
        owner.command.return_value = ['unused-official-cli']
        with patch('pal.runtime.Runtime.PRIMARY_PROTOCOL','legacy'), \
                patch('scripts.live_operator.clean_candidate'), \
                patch('scripts.live_operator.AccessProof.load', return_value=proof), \
                patch('scripts.live_operator.AuditedNative', return_value=owner), \
                patch('scripts.live_operator.subprocess.run', return_value=Mock(stdout='fixture')), \
                patch('scripts.live_operator.MatrixRunner', return_value=runner):
            with self.assertRaisesRegex(OSError, 'injected evidence failure'):
                build_live(root, root/'runtime/unused-failure-fixture', 'unused-proof', 'fixture')
        runner.close.assert_called_once_with()

    def test_old_operator_rejects_primary_before_auth_proof_or_any_process(self):
        with patch('scripts.live_operator.AccessProof.load') as load, \
                patch('scripts.live_operator.subprocess.run') as process:
            with self.assertRaisesRegex(ValueError,'incompatible'):
                build_live(Path('.'),'unused','unused','unused')
            load.assert_not_called()
            process.assert_not_called()

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
