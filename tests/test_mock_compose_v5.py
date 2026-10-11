"""RUN compose coordination against an explicit ART contract double, not storage proof."""
import copy
import hashlib
import sqlite3
import unittest

from pal.contracts_v5 import Grant, Limits, Result, dumps
from pal.memory_v5 import MemoryStore
from pal.mock_runner_v5 import MockRunner
from pal.tasks_v5 import TaskStore


def value(result):
    if not result.ok:
        raise AssertionError(result.to_json())
    return result.value.to_json()


class ReceiptOwner:
    """In-memory interface double: never qualifies actual immutable ART storage."""
    def __init__(self):
        self.saved = None
        self.saves, self.lookups = [], []
        self.save_failure = None
        self.lookup_failure = None
        self.after_save = None

    def save(self, request):
        self.saves.append(copy.deepcopy(request))
        if self.save_failure in ('conflict', 'invalid_input'):
            return Result.failure(self.save_failure, 'double rejected input')
        if self.saved is None:
            body = request['content'].encode('utf-8')
            self.saved = {'artifact_ref': {'kind': 'artifact', 'id': 'draft'},
                          'hash': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
        if self.after_save:
            callback, self.after_save = self.after_save, None
            callback()
        if self.save_failure:
            return Result.failure(self.save_failure, 'double lost response')
        return Result.success(self.saved)

    def get_by_key(self, request):
        self.lookups.append(copy.deepcopy(request))
        if self.lookup_failure:
            return Result.failure(self.lookup_failure, 'double lookup failure')
        return Result.success(self.saved)


class MockComposeTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:', isolation_level=None)
        self.addCleanup(self.conn.close)
        grant = Grant(('github.issue.read',), ('repo',), Limits(0, 8, 8))
        memory = None
        self.tasks = TaskStore(self.conn, host_grant=grant, expert_id='expert',
                               host_limits=Limits(0, 50, 50),
                               artifact_inspect=lambda c, r: Result.failure('unavailable', 'unused double'),
                               source_gate=lambda c, refs: memory.source_gate(c, refs))
        memory = self.memory = MemoryStore(self.conn, sanitize_text=lambda x: x,
                                           append_event=self.tasks.append_event,
                                           invalidate_by_refs=self.tasks.invalidate_by_refs)
        self.origin = value(memory.append({'client_key': 'origin', 'session_id': 's',
                                           'role': 'user', 'text': 'Prepare a local draft'}))['record_ref']
        self.work = value(self.tasks.create({'key': 'create', 'session_id': 's',
            'origin_record_ref': self.origin,
            'brief': {'purpose': 'draft', 'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
                      'constraints': [], 'context_refs': [],
                      'conditions': [{'description': 'Draft saved', 'check': 'artifact_saved'}]}},
            request_scope=grant))['work_ref']
        self.owner = ReceiptOwner()
        self.calls, self.finishes = [], []
        self.real_finish = self.tasks.finish_step
        self.tasks.finish_step = self.finish_double

    def expert(self, c12, **metadata):
        self.calls.append(copy.deepcopy(c12))
        return {'kind': 'compose', 'content': '下書き\n内容\r\n', 'media_type': 'text/markdown',
                'source_refs': [self.origin]}

    def finish_double(self, request, **metadata):
        self.finishes.append((copy.deepcopy(request), metadata))
        # This test double validates orchestration and returns the stored started Step.
        # Actual TSK attachment has a separate owner test and later connected test.
        row = self.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?', (request['step_id'],)).fetchone()
        from pal.contracts_v5 import loads
        step = loads(row[0]); step['status'] = 'finished'; step['result_refs'] = request['result_refs']
        self.conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(step), request['step_id']))
        return Result.success(step)

    def state(self):
        return value(self.tasks.get_work({'goal_id': self.work['goal_id']}))['state']

    def test_no_art_owner_preserves_output_without_creating_step_or_repeating_call(self):
        runner = MockRunner(self.tasks, self.memory)
        result = runner.run_once(self.expert)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, 'unavailable')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_tsk_step').fetchone()[0], 0)
        self.assertEqual(self.state(), 'running')
        self.assertFalse(runner.run_once(self.expert).ok)
        self.assertEqual(len(self.calls), 1)

    def test_exact_action_and_canonical_key_are_saved_before_finish(self):
        out = value(MockRunner(self.tasks, self.memory, artifacts=self.owner).run_once(self.expert))
        self.assertEqual(out['state'], 'queued')
        self.assertEqual((len(self.calls), len(self.owner.saves), len(self.finishes)), (1, 1, 1))
        req = self.owner.saves[0]
        self.assertEqual(req['key'], dumps(['C08.save', req['work_ref'], req['step_id']]))
        self.assertEqual(req['content'], '下書き\n内容\r\n')
        self.assertEqual(req['media_type'], 'text/markdown')
        self.assertEqual(req['source_refs'], [self.origin])
        self.assertEqual(set(req), {'key', 'work_ref', 'step_id', 'content', 'media_type', 'source_refs'})
        self.assertEqual(self.finishes[0][0]['result_refs'], [self.owner.saved['artifact_ref']])
        self.assertEqual(self.owner.lookups, [])

    def test_lost_save_response_recovers_only_after_bounded_identical_retries(self):
        self.owner.save_failure = 'unavailable'
        out = value(MockRunner(self.tasks, self.memory, artifacts=self.owner).run_once(self.expert))
        self.assertEqual(out['state'], 'queued')
        self.assertEqual(len(self.owner.saves), 3)
        self.assertTrue(all(r == self.owner.saves[0] for r in self.owner.saves))
        self.assertEqual(self.owner.lookups, [{'key': self.owner.saves[0]['key']}])
        self.assertEqual((len(self.calls), len(self.finishes)), (1, 1))

    def test_persistent_receipt_failure_keeps_occupancy_without_model_retry(self):
        self.owner.save_failure = self.owner.lookup_failure = 'unavailable'
        runner = MockRunner(self.tasks, self.memory, artifacts=self.owner)
        result = runner.run_once(self.expert)
        self.assertEqual(result.error.code, 'unavailable')
        self.assertEqual((len(self.owner.saves), len(self.owner.lookups)), (3, 3))
        self.assertEqual(self.finishes, [])
        self.assertEqual(self.state(), 'running')
        self.assertFalse(runner.run_once(self.expert).ok)
        self.assertEqual(len(self.calls), 1)

    def test_input_conflict_is_not_recovered_via_an_unrelated_receipt(self):
        self.owner.save_failure = 'conflict'
        result = value(MockRunner(self.tasks, self.memory, artifacts=self.owner).run_once(self.expert))
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(len(self.owner.saves), 1)
        self.assertEqual(self.owner.lookups, [])
        self.assertEqual(self.finishes, [])
        self.assertEqual(len(self.calls), 1)

    def test_missing_receipt_after_unavailable_save_does_not_fail_the_goal(self):
        self.owner.save_failure = 'unavailable'
        self.owner.lookup_failure = 'not_found'
        runner = MockRunner(self.tasks, self.memory, artifacts=self.owner)
        result = runner.run_once(self.expert)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, 'unavailable')
        self.assertEqual(self.state(), 'running')
        self.assertEqual((len(self.owner.saves), len(self.owner.lookups)), (3, 1))
        self.assertEqual(self.finishes, [])
        self.assertFalse(runner.run_once(self.expert).ok)
        self.assertEqual(len(self.calls), 1)

    def test_pause_after_save_still_refences_finish_and_releases_to_pause(self):
        self.tasks.finish_step = self.real_finish
        self.owner.after_save = lambda: value(self.tasks.control({'key': 'pause',
            'work_ref': self.calls[0]['work_ref'], 'command': 'pause'}))
        out = value(MockRunner(self.tasks, self.memory, artifacts=self.owner).run_once(self.expert))
        self.assertEqual(out['state'], 'paused')
        self.assertEqual(len(self.calls), 1)
        self.assertIsNotNone(self.owner.saved)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_tsk_step').fetchone()[0], 1)

    def test_corrupt_save_receipt_never_reaches_finish(self):
        self.owner.saved = {'artifact_ref': {'kind': 'record', 'id': 'wrong'},
                            'hash': '0' * 64, 'bytes': 1}
        runner = MockRunner(self.tasks, self.memory, artifacts=self.owner)
        result = runner.run_once(self.expert)
        self.assertEqual(result.error.code, 'unavailable')
        self.assertEqual(self.finishes, [])
        self.assertEqual(self.state(), 'running')
        self.assertEqual(len(self.calls), 1)


if __name__ == '__main__':
    unittest.main()
