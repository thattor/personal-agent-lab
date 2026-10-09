import json
import hashlib
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pal.runtime import MockProvider, Runtime
from pal.store import InvalidTransition
from pal.native import AccessProof, NativeClaude, ProviderUnavailable
from scripts.live_evidence import verify_journal
from scripts.live_runner import RunRejected, product_rel_paths
from scripts.live_cancel_probe import (CancelProbe, DeliveryHold, build_live,
                                      serve_operator, HARNESS, PRODUCT_FREEZE,
                                      REQUEST, CANCEL)


class CompleteExecutor:
    def execute(self, order):
        return {'goal_id': order.goal_id, 'attempt_id': order.attempt_id,
                'epoch': order.epoch, 'proposal': {'kind': 'complete',
                'content': 'A local fixture draft.', 'citations': []}}

    def stop(self):
        pass


class QuestionExecutor(CompleteExecutor):
    def execute(self, order):
        return {'goal_id': order.goal_id, 'attempt_id': order.attempt_id,
                'epoch': order.epoch, 'proposal': {'kind': 'needs_input',
                'question': 'Which date?', 'citations': []}}


class CancelProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def start(self, executor=None, cleanup=True):
        probe = CancelProbe(self.root / 'run', MockProvider(),
                            executor=executor or CompleteExecutor())
        if cleanup:
            self.addCleanup(probe.close)
        result = probe.runtime.submit('draft', 'Make a draft, do not send it')
        result['response'].result(timeout=3)
        self.assertTrue(probe.hold.held.wait(3))
        return probe

    def cancel(self, probe):
        goal = probe.runtime.store.inspect()['goals'][0]
        result = probe.runtime.submit('cancel', 'Stop that', goal_id=goal['id'],
                                      control={'action': 'cancel', 'epoch': goal['epoch']})
        self.assertEqual(result['goal']['state'], 'cancelled')

    def test_hold_filters_primary_and_only_blocks_first_worker_point(self):
        hold = DeliveryHold()
        class Health:
            def health(self):
                return {'stopping': False}
        hold.runtime = Health()
        for point in ('primary.before_model', 'primary.after_model_before_apply'):
            hold(point)
        self.assertFalse(hold.held.is_set())
        thread = threading.Thread(target=hold, args=('worker.after_executor_before_apply',))
        thread.start()
        try:
            self.assertTrue(hold.held.wait(1))
            self.assertTrue(thread.is_alive())
            hold('primary.before_model')
            hold.released.set()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            second = threading.Thread(target=hold, args=('worker.after_executor_before_apply',))
            hold.released.clear()
            second.start()
            second.join(1)
            self.assertFalse(second.is_alive())
        finally:
            hold.released.set()
            thread.join(2)

    def test_premature_release_leaves_result_held_and_no_artifact(self):
        probe = self.start()
        probe.bind()
        self.assertFalse(probe.release())
        self.assertFalse(probe.hold.released.is_set())
        data = probe.runtime.store.inspect()
        self.assertEqual(data['goals'][0]['state'], 'running')
        self.assertEqual(data['receipts'], [])
        self.assertEqual(data['artifacts'], [])

    def test_binding_refuses_two_goals_instead_of_guessing_running_target(self):
        probe = self.start()
        probe.runtime.store.create_goal('other', 'Other fixture work',
                                       {'kind': 'local_draft', 'max_bytes': 4096})
        with self.assertRaises(RunRejected):
            probe.bind()
        probe.close_run('binding-refused')
        self.assertEqual(probe.runtime.store.inspect()['receipts'], [])

    def test_cancel_then_release_retains_exact_stale_artifact_without_receipt(self):
        probe = self.start()
        probe.bind()
        initial = probe.runtime.store.inspect()
        attempt = initial['attempts'][0]
        self.cancel(probe)
        self.assertTrue(probe.release())
        self.assertEqual(probe.result(timeout=2)['status'], 'PASS')
        data = probe.runtime.store.inspect()
        self.assertEqual([(r['attempt_id'], r['reason']) for r in data['rejections']],
                         [(attempt['id'], 'stale artifact')])
        self.assertEqual(data['goals'][0]['state'], 'cancelled')
        self.assertEqual(data['attempts'][0]['status'], 'fenced')
        self.assertEqual(data['revisions'], initial['revisions'])
        self.assertEqual(data['acceptances'], initial['acceptances'])
        self.assertEqual(data['receipts'], [])
        self.assertEqual(data['artifacts'], [])
        self.assertEqual(data['outcomes'], [])

    def test_needs_input_is_not_complete_result_pass(self):
        probe = self.start(QuestionExecutor())
        probe.bind()
        self.cancel(probe)
        self.assertTrue(probe.release())
        self.assertEqual(probe.result(timeout=2)['status'], 'NOT_VERIFIED')
        data = probe.runtime.store.inspect()
        self.assertEqual(data['receipts'], [])
        self.assertFalse(any(x['reason'] == 'stale artifact' for x in data['rejections']))

    def stale_ready(self):
        probe = self.start()
        bound = probe.bind()
        self.cancel(probe)
        self.assertTrue(probe.release())
        self.assertTrue(probe.runtime.idle.wait(2))
        self.assertEqual([(x['attempt_id'], x['reason']) for x in probe.snapshot()['rejections']],
                         [(bound['attempts'][0]['id'], 'stale artifact')])
        return probe

    def assert_no_published_pass(self, probe):
        records = verify_journal(probe.directory / 'journal.jsonl')
        self.assertFalse(any(r['event'] == 'result.observed' and
                             r.get('result', r).get('status') == 'PASS' for r in records))
        self.assertEqual(probe.runtime.store.inspect()['artifacts'], [])
        self.assertEqual(probe.runtime.store.inspect()['receipts'], [])

    def test_close_wins_after_stale_observation_before_pass_publication(self):
        probe = self.stale_ready()
        snapshot = probe.snapshot
        calls = 0
        def close_after_first_observation():
            nonlocal calls
            data = snapshot()
            calls += 1
            if calls == 1:
                # First observation is outside result's finalization lock.
                probe.close_run('wall_deadline')
            return data
        with patch.object(probe, 'snapshot', side_effect=close_after_first_observation):
            with self.assertRaises(RunRejected):
                probe.result(timeout=2)
        self.assertEqual(calls, 1)
        self.assertTrue(probe.closed.is_set())
        self.assert_no_published_pass(probe)

    def test_expiry_during_final_snapshot_never_publishes_pass(self):
        probe = self.stale_ready()
        snapshot = probe.snapshot
        calls = 0
        def expire_during_second_snapshot():
            nonlocal calls
            data = snapshot()
            calls += 1
            if calls == 2:
                probe.deadline = time.monotonic() - 1
            return data
        with patch.object(probe, 'snapshot', side_effect=expire_during_second_snapshot):
            with self.assertRaises(RunRejected):
                probe.result(timeout=2)
        self.assertEqual(calls, 2)
        self.assert_no_published_pass(probe)

    def test_pause_cannot_satisfy_cancel_release_gate(self):
        probe = self.start()
        probe.bind()
        goal = probe.runtime.store.inspect()['goals'][0]
        probe.runtime.submit('pause', 'Pause', goal_id=goal['id'],
                             control={'action': 'pause', 'epoch': goal['epoch']})
        with self.assertRaises(RunRejected):
            probe.release()
        self.assertFalse(probe.hold.released.is_set())
        self.assertEqual(probe.runtime.store.inspect()['receipts'], [])

    def test_wrong_target_cancel_cannot_release_bound_attempt(self):
        probe = self.start()
        probe.bind()
        other = probe.runtime.store.create_goal('other', 'Unrelated fixture work',
                                                {'kind': 'local_draft', 'max_bytes': 4096})
        probe.runtime.submit('other-cancel', 'Cancel', goal_id=other['id'],
                             control={'action': 'cancel', 'epoch': other['epoch']})
        with self.assertRaises(RunRejected):
            probe.release()
        self.assertFalse(probe.hold.released.is_set())
        self.assertEqual(probe.runtime.store.inspect()['receipts'], [])

    def test_live_invalid_preflight_never_constructs_native_owner(self):
        # Invalid source/contract cannot reach the provider, even with a proof path.
        with patch('scripts.live_cancel_probe.build_provider') as native:
            with self.assertRaises(RunRejected):
                build_live(self.root, self.root / 'live', self.root / 'proof.json',
                           '0' * 40, self.root / 'missing-contract.json')
            native.assert_not_called()
        self.assertFalse((self.root / 'live').exists())

    def test_stale_cancel_is_rejected_and_cannot_release_result(self):
        probe = self.start()
        probe.bind()
        goal = probe.runtime.store.inspect()['goals'][0]
        with self.assertRaises(InvalidTransition):
            probe.runtime.submit('stale', 'Cancel', goal_id=goal['id'],
                                 control={'action': 'cancel', 'epoch': goal['epoch'] - 1})
        self.assertFalse(probe.release())
        self.assertEqual(probe.runtime.store.inspect()['goals'][0]['state'], 'running')
        self.assertEqual(probe.runtime.store.inspect()['receipts'], [])

    def test_close_while_held_never_applies_result_and_releases_host_lock(self):
        probe = self.start()
        path = probe.runtime.store.path
        probe.close_run('test-close')
        probe.close_run('duplicate-close')
        self.assertEqual(probe.runtime.store.inspect()['receipts'], [])
        reopened = Runtime(path)
        reopened.close()

    def test_evidence_failure_while_held_still_cleans_up_without_apply(self):
        probe = self.start(cleanup=False)
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b'finish\n')
            with patch.object(probe.journal, 'append', side_effect=OSError('fixture journal failure')):
                with self.assertRaises((OSError, RuntimeError)):
                    serve_operator(probe, input_fd=read_fd)
            self.assertTrue(probe.close_done.is_set())
            data = probe.runtime.store.inspect()
            self.assertEqual(data['artifacts'], [])
            self.assertEqual(data['receipts'], [])
            reopened = Runtime(probe.runtime.store.path)
            reopened.close()
        finally:
            os.close(read_fd)
            os.close(write_fd)
            try:
                probe.close()
            except RuntimeError:
                pass  # The deliberately failed evidence remains an error.

    def test_operator_deadline_before_watchdog_exits_cleanly(self):
        probe = self.start()
        probe.deadline = time.monotonic() - 1
        read_fd, write_fd = os.pipe()
        try:
            serve_operator(probe, input_fd=read_fd)
        finally:
            os.close(read_fd)
            os.close(write_fd)
        self.assertTrue(probe.close_done.is_set())
        data = probe.runtime.store.inspect()
        self.assertEqual((data['receipts'], data['artifacts']), ([], []))
        records = verify_journal(probe.directory / 'journal.jsonl')
        self.assertEqual([r['reason'] for r in records if r['event'] == 'run.closed'],
                         ['wall_deadline'])
        self.assertFalse(any(r['event'] == 'operator.failed' for r in records))
        reopened = Runtime(probe.runtime.store.path)
        reopened.close()

    def test_operator_concurrent_close_preserves_original_reason(self):
        probe = self.start()
        check = probe._check
        def close_then_check():
            probe.close_run('signal')
            check()
        read_fd, write_fd = os.pipe()
        try:
            with patch.object(probe, '_check', side_effect=close_then_check):
                serve_operator(probe, input_fd=read_fd)
        finally:
            os.close(read_fd)
            os.close(write_fd)
        records = verify_journal(probe.directory / 'journal.jsonl')
        self.assertEqual([r['reason'] for r in records if r['event'] == 'run.closed'],
                         ['signal'])
        self.assertFalse(any(r['event'] == 'operator.failed' for r in records))
        self.assertTrue(probe.close_done.is_set())
        self.assertEqual(probe.runtime.store.inspect()['receipts'], [])

    def test_operator_other_rejection_remains_failure(self):
        probe = self.start()
        read_fd, write_fd = os.pipe()
        try:
            with patch.object(probe, '_check', side_effect=RunRejected('fixture pin changed')):
                with self.assertRaises(RunRejected):
                    serve_operator(probe, input_fd=read_fd)
        finally:
            os.close(read_fd)
            os.close(write_fd)
        records = verify_journal(probe.directory / 'journal.jsonl')
        self.assertTrue(any(r['event'] == 'operator.failed' for r in records))
        self.assertTrue(probe.close_done.is_set())
        self.assertEqual(probe.runtime.store.inspect()['receipts'], [])

    def test_subprocess_eof_sigint_and_deadline_while_held_release_lock(self):
        child_code = '''
import json,sys,time
from pathlib import Path
from pal.runtime import MockProvider,Runtime
from scripts.live_cancel_probe import CancelProbe,serve_operator
from tests.test_live_cancel_probe import CompleteExecutor
root=Path(sys.argv[1]); mode=sys.argv[2]
p=CancelProbe(root/'run',MockProvider(),executor=CompleteExecutor(),
              deadline=time.monotonic()+2 if mode=='deadline' else None)
try:
    p.runtime.submit('draft','Make a draft, do not send it')['response'].result(timeout=3)
    assert p.hold.held.wait(3)
    print('CHILD_HELD',flush=True)
    serve_operator(p,input_fd=sys.stdin.fileno())
finally:
    p.close()
assert not p.runtime.store.inspect()['receipts']
assert not p.runtime.store.inspect()['artifacts']
q=Runtime(p.runtime.store.path); q.close()
print('CHILD_CLOSED_LOCK_FREE',flush=True)
'''
        for mode in ('eof', 'sigint', 'deadline'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                child = subprocess.Popen([sys.executable, '-u', '-c', child_code, temp, mode],
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True)
                try:
                    self.assertTrue(select.select([child.stdout], [], [], 5)[0])
                    self.assertEqual(child.stdout.readline().strip(), 'CHILD_HELD')
                    if mode == 'eof':
                        child.stdin.close()
                        child.stdin = None
                    elif mode == 'sigint':
                        # Let the operator install its handler, without timing the worker.
                        self.assertTrue(select.select([child.stdout], [], [], 3)[0])
                        self.assertIn('ready', child.stdout.readline().lower())
                        child.send_signal(signal.SIGINT)
                    if mode != 'eof':
                        # communicate closes stdin: doing it before exit would test
                        # EOF instead of the intended signal or wall deadline.
                        child.wait(timeout=6)
                    stdout, stderr = child.communicate(timeout=3)
                    self.assertEqual(child.returncode, 0, stderr)
                    self.assertIn('CHILD_CLOSED_LOCK_FREE', stdout)
                    records = verify_journal(Path(temp) / 'run/journal.jsonl')
                    self.assertEqual([r['reason'] for r in records if r['event'] == 'run.closed'],
                                     [{'eof': 'stdin_eof', 'sigint': 'signal',
                                       'deadline': 'wall_deadline'}[mode]])
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=3)


class CancelProbePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = (Path(self.temp.name) / 'source').resolve()
        self.root.mkdir()
        source = Path(__file__).resolve().parents[1]
        # Only known product/harness files; no held-out corpus or existing DB.
        for rel in product_rel_paths(source) | HARNESS:
            destination = self.root / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / rel, destination)
        files = {rel: self.hash(self.root / rel) for rel in product_rel_paths(self.root)}
        identity = 'content:sha256:' + hashlib.sha256(
            json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        freeze = self.root / PRODUCT_FREEZE
        freeze.parent.mkdir(parents=True)
        freeze.write_text(json.dumps({'candidate': identity, 'files': files}))
        self.contract = self.root / 'contract.json'
        self.value = {'id': 'C047-CONTROLLED-CANCEL-v1', 'max_calls': 3,
                      'wall_seconds': 600, 'inputs': [REQUEST, CANCEL],
                      'harness_files': {rel: self.hash(self.root / rel) for rel in HARNESS},
                      'product_identity': identity}
        self.contract.write_text(json.dumps(self.value))
        (self.root / '.gitignore').write_text('runtime/\n')
        (self.root / 'runtime').mkdir()
        self.proof = self.root / 'runtime/proof.json'
        self.proof.write_text(json.dumps({'verified_at': time.time(),
                                         'no_extra_charge': True,
                                         'route': 'official_claude_pro'}))
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.commit()
        self.directory = self.root / 'runtime/probe'

    @staticmethod
    def hash(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root,
                                       stderr=subprocess.PIPE, text=True).strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Synthetic source freeze')
        self.candidate = self.git('rev-parse', 'HEAD')

    def rejected_before_native(self, candidate=None):
        with patch('scripts.live_cancel_probe.build_provider') as native:
            with self.assertRaises(RunRejected):
                build_live(self.root, self.directory, self.proof,
                           candidate or self.candidate, self.contract)
            native.assert_not_called()

    def test_existing_run_refused_before_proof_use(self):
        self.directory.mkdir()
        self.rejected_before_native()
        self.assertFalse((self.root / 'runtime/native-proof-use').exists())

    def test_wrong_candidate_and_dirty_source_refused_before_proof_use(self):
        self.rejected_before_native('0' * 40)
        (self.root / 'pal/runtime.py').write_text('dirty fixture source')
        self.rejected_before_native()

    def test_wrong_script_hash_product_identity_and_cap_refused(self):
        original = dict(self.value)
        for field in ('harness_files', 'product_identity', 'max_calls'):
            with self.subTest(field=field):
                self.value = dict(original)
                if field == 'harness_files':
                    self.value[field] = dict(original[field])
                    self.value[field]['scripts/live_cancel_probe.py'] = '0' * 64
                elif field == 'product_identity':
                    self.value[field] = 'content:sha256:' + '0' * 64
                else:
                    self.value[field] = 4
                self.contract.write_text(json.dumps(self.value))
                self.commit()  # A clean checkout alone cannot bless wrong hashes.
                self.rejected_before_native()

    def test_changed_product_bytes_rejected_despite_clean_candidate(self):
        product = self.root / 'pal/runtime.py'
        product.write_text(product.read_text() + '\n# synthetic drift\n')
        self.commit()
        self.rejected_before_native()

    def test_consumed_proof_marker_refused_before_runtime_without_native_call(self):
        AccessProof.load(self.proof).consume(self.root / 'runtime/native-proof-use')
        with patch('scripts.live_cancel_probe.Runtime') as runtime, \
                patch.object(NativeClaude, 'complete') as complete:
            with self.assertRaises(ProviderUnavailable):
                build_live(self.root, self.directory, self.proof,
                           self.candidate, self.contract)
            runtime.assert_not_called()
            complete.assert_not_called()
        self.assertFalse(self.directory.exists())


if __name__ == '__main__':
    unittest.main()
