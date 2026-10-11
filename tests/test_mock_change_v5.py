"""CHANGE01 RUN fixed public-owner doubles; no TSK persistence proof."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import copy
import sqlite3
import unittest
from pal.contracts_v5 import Result, dumps
from pal.mock_runner_v5 import MockRunner
import test_mock_ask_v5 as ask_fixture
import test_mock_completion_v5 as completion_fixture

value = completion_fixture.value


class RevisionOwners(ask_fixture.AskOwners):
    """A fenced TSK contract double, with separate old lease and latest work."""
    def __init__(self):
        super().__init__()
        self.latest = copy.deepcopy(self.work)
        self.old = copy.deepcopy(self.work)
        self.active = True
        self.lease = 'lease'
        self.changed = False
        self.trace = []
        self.saves = []
        self.used_model = self.used_step = 0
        self.history = {'artifacts': [self.artifact], 'verifications': [self.verification]}
        self.hook = None

    def change(self):
        self.latest = {**self.latest, 'revision': self.latest['revision'] + 1,
                       'epoch': self.latest['epoch'] + 1}
        self.changed = True
        self.trace.append('change')

    def intent(self, command):
        self.trace.append(command)
        if command in ('pause', 'cancel'):
            self.state = 'paused' if command == 'pause' else 'cancelled'
        if command in ('shared_stop', 'cancel'):
            self.latest['epoch'] += 1

    def claim(self, request):
        if not self.active:
            if self.state in ('paused', 'cancelled'):
                return Result.success({'status': 'empty'})
            self.lease += '-next'
            self.work = copy.deepcopy(self.latest)
            self.old = copy.deepcopy(self.work)
            self.changed = False
            self.steps, self.calls, self.artifact_refs, self.pending = [], {}, [], []
            self.active = True
        data = value(super().claim(request))
        data['lease_id'] = self.lease
        return Result.success(data)

    def get_execution_context(self, request):
        if self.changed:
            return Result.failure('stale', 'revision replaced')
        return super().get_execution_context(request)

    def reserve_budget(self, request):
        if self.changed:
            return Result.failure('stale', 'revision replaced')
        self.used_model += request['kind'] == 'model'
        self.used_step += request['kind'] == 'step'
        return super().reserve_budget(request)

    def admit_call(self, request):
        self.trace.append('admit')
        result = super().admit_call(request)
        self.calls[request['call_id']]['lease_id'] = self.lease
        return result

    def end_call(self, request):
        self.trace.append(request['outcome'])
        return super().end_call(request)

    def boundary(self, name):
        self.trace.append(name)
        if self.hook == name:
            self.hook = None
            self.change()

    def begin_step(self, request):
        self.boundary('begin')
        if self.changed:
            return Result.failure('stale', 'revision replaced')
        step = value(completion_fixture.SyntheticOwners.begin_step(self, request))
        call_id = dumps(['C15.call', self.lease, step['index']])
        self.calls[call_id]['step_id'] = step['step_id']
        return Result.success(step)

    def finish_step(self, request, **metadata):
        self.boundary('finish')
        if self.changed:
            self.finishes.append(copy.deepcopy(request))
            return Result.failure('stale', 'revision replaced')
        return super().finish_step(request, **metadata)

    def save(self, request):
        self.saves.append(copy.deepcopy(request))
        self.boundary('save')
        if self.changed:
            return Result.failure('stale', 'revision replaced')
        return super().save(request)

    def ask(self, request):
        self.boundary('ask')
        if self.changed:
            self.asks.append(copy.deepcopy(request))
            return Result.failure('stale', 'revision replaced')
        return super().ask(request)

    def get_work(self, request):
        self.trace.append('work')
        historical = request.get('revision') == self.old['revision'] and self.changed
        return Result.success({'work_ref': self.old if historical else self.latest,
            'state': 'superseded' if historical else self.state, 'control_status': 'none',
            'current_artifact_refs': self.artifact_refs})

    def verify(self, request):
        self.verifies.append(copy.deepcopy(request))
        self.boundary('verify')
        if self.changed:
            return Result.failure('stale', 'revision replaced')
        return Result.success(completion_fixture.SyntheticOwners.receipt(self))

    def control(self, request):
        self.completes.append(copy.deepcopy(request))
        self.boundary('complete')
        if self.changed:
            return Result.failure('stale', 'revision replaced')
        return super().control(request)

    def release(self, request):
        self.trace.append('release')
        self.releases.append(copy.deepcopy(request))
        if any(call['status'] == 'admitted' for call in self.calls.values()):
            return Result.failure('conflict', 'call has not ceased')
        self.active = False
        if self.state not in ('paused', 'cancelled'):
            self.state = 'queued'
        return Result.success({'work_ref': copy.deepcopy(self.latest),
                               'state': self.state, 'control_status': 'none'})


class MockChangeTests(unittest.TestCase):
    def setUp(self):
        self.o = RevisionOwners()
        self.inputs = []
        self.runner = MockRunner(self.o, self.o, artifacts=self.o, verifications=self.o)

    def action(self, kind):
        if kind == 'compose':
            return {'kind': kind, 'content': 'saved draft', 'media_type': 'text/plain',
                    'source_refs': [self.o.origin]}
        if kind == 'ask':
            return {'kind': kind, 'question': 'Which date?', 'missing_fact': 'date',
                    'source_refs': [self.o.origin]}
        return {'kind': 'report', 'summary': 'bounded'}

    def expert(self, kind='report', *, change=False, controls=()):
        def run(context, **diagnostics):
            self.inputs.append(copy.deepcopy(context))
            self.assertEqual(self.o.calls[next(reversed(self.o.calls))]['status'], 'admitted')
            self.assertEqual(self.o.trace[-1], 'admit')
            if change:
                self.o.change()
            for control in controls:
                self.o.change() if control == 'change' else self.o.intent(control)
            return self.action(kind)
        return run

    def settled(self, result, state='queued'):
        data = value(result)
        self.assertEqual((data['status'], data['state'], data['work_ref']),
                         ('released', state, self.o.latest))
        self.assertEqual(self.o.releases[-1]['work_ref'], self.o.old)
        self.assertFalse(self.o.active)
        self.assertEqual(self.o.completes, [])
        return data

    def tail(self, kind, *, finished=False, status='returned'):
        step = {'step_id': 'old-tail', 'work_ref': copy.deepcopy(self.o.old), 'index': 0,
                'action': self.action(kind), 'status': 'finished' if finished else 'started',
                'result_refs': [self.o.artifact] if kind == 'compose' and finished else []}
        self.o.steps = [step]
        if step['result_refs']:
            self.o.artifact_refs = copy.deepcopy(step['result_refs'])
        key = dumps(['C15.call', 'lease', 0])
        self.o.calls[key] = {'call_id': key, 'lease_id': 'lease', 'work_ref': copy.deepcopy(self.o.old),
                             'index': 0, 'status': status, 'may_enter': False, 'step_id': 'old-tail'}
        self.o.change()
        return key

    def test_change_during_admitted_call_discards_all_action_kinds_after_return(self):
        for kind in ('compose', 'ask', 'report'):
            with self.subTest(kind=kind):
                self.setUp()
                self.settled(self.runner.run_once(self.expert(kind, change=True), max_steps=3))
                self.assertEqual((len(self.inputs), len(self.o.reserves)), (1, 1))
                self.assertLess(self.o.trace.index('returned'), self.o.trace.index('release'))
                self.assertEqual((self.o.steps, self.o.saves, self.o.asks, self.o.verifies), ([], [], [], []))

    def test_pause_change_shared_stop_latest_intent_wins_after_cessation(self):
        self.settled(self.runner.run_once(self.expert(change=True,
            controls=('pause', 'change', 'shared_stop')), max_steps=3), 'paused')
        self.assertEqual(self.o.latest, {'goal_id': 'g', 'revision': 3, 'epoch': 3})
        self.assertLess(self.o.trace.index('returned'), self.o.trace.index('release'))
        self.assertEqual(len(self.inputs), 1)

    def test_cancel_wins_over_old_failed_outcome(self):
        self.settled(self.runner.run_once(self.expert(change=True,
            controls=('pause', 'change', 'shared_stop', 'cancel'))), 'cancelled')
        self.assertEqual(self.o.releases[-1]['outcome'], 'failed')
        self.assertEqual(len(self.inputs), 1)

    def test_raised_callable_releases_only_after_raised_cessation(self):
        def raised(context, **diagnostics):
            self.o.change()
            raise RuntimeError('mock ended')
        self.settled(self.runner.run_once(raised))
        self.assertLess(self.o.trace.index('raised'), self.o.trace.index('release'))
        self.assertEqual(len(self.o.reserves), 1)

    def test_retained_started_compose_and_report_never_reenter_or_save(self):
        for kind in ('compose', 'report'):
            with self.subTest(kind=kind):
                self.setUp()
                self.tail(kind)
                self.settled(self.runner.run_once(self.expert(), max_steps=3))
                self.assertEqual((self.inputs, self.o.reserves, self.o.saves, self.o.verifies), ([], [], [], []))

    def test_retained_ask_checks_call_then_one_fenced_ask_no_inference(self):
        self.tail('ask')
        self.settled(self.runner.run_once(self.expert(), max_steps=3))
        self.assertEqual((self.inputs, self.o.reserves, self.o.finishes), ([], [], []))
        self.assertEqual(len(self.o.asks), 1)
        self.assertEqual(self.o.asks[0]['work_ref'], self.o.old)
        self.assertEqual(self.o.lookups, [])

    def test_retained_finished_compose_verification_stale_then_safe_release(self):
        self.tail('compose', finished=True)
        self.settled(self.runner.run_once(self.expert(), max_steps=3))
        self.assertEqual((self.inputs, self.o.reserves, self.o.saves), ([], [], []))
        self.assertEqual(len(self.o.verifies), 1)
        self.assertEqual(self.o.verifies[0]['work_ref'], self.o.old)

    def test_retained_admitted_call_keeps_occupancy_until_returned(self):
        key = self.tail('ask', status='admitted')
        result = self.runner.run_once(self.expert())
        self.assertFalse(result.ok)
        self.assertTrue(self.o.active)
        self.assertEqual((self.o.asks, self.inputs, self.o.reserves), ([], [], []))
        self.o.calls[key]['status'] = 'returned'
        self.settled(self.runner.run_once(self.expert()))
        self.assertEqual(len(self.o.asks), 1)

    def test_change_at_local_save_finish_ask_and_verify_boundaries_never_completes(self):
        for boundary, kind in (('save', 'compose'), ('finish', 'report'),
                               ('ask', 'ask'), ('verify', 'compose')):
            with self.subTest(boundary=boundary):
                self.setUp()
                self.o.hook = boundary
                self.settled(self.runner.run_once(self.expert(kind), max_steps=3))
                self.assertEqual((len(self.inputs), len(self.o.reserves)), (1, 1))
                self.assertTrue(all(s['status'] == 'started' for s in self.o.steps)
                                or boundary == 'verify')
                self.assertLess(self.o.trace.index('returned'), self.o.trace.index('release'))

    def test_next_revision_progress_preserves_goal_usage_and_history(self):
        before = copy.deepcopy(self.o.history)
        self.settled(self.runner.run_once(self.expert(change=True)))
        usage = self.o.used_model
        self.settled(self.runner.run_once(self.expert('report')))
        self.assertEqual(self.o.used_model, usage + 1)
        self.assertEqual(self.o.history, before)
        self.assertEqual(self.inputs[-1]['work_ref']['revision'], 2)
        self.assertEqual(self.o.steps[-1]['work_ref']['revision'], 2)


class ActualAdmissionChangeTests(unittest.TestCase):
    """One actual in-memory owner seam; broader connection/races are Root-owned."""
    def test_actual_admitted_change_returns_latest_revision_without_adopting_report(self):
        from pal.contracts_v5 import Grant, Limits
        from pal.memory_v5 import MemoryStore
        from pal.tasks_v5 import TaskStore
        from pal.sanitize import sanitize
        conn = sqlite3.connect(':memory:', isolation_level=None)
        self.addCleanup(conn.close)
        grant = Grant((), ('repo',), Limits(0, 4, 4))
        memory = None
        tasks = TaskStore(conn, host_grant=grant, expert_id='expert',
            host_limits=Limits(0, 8, 8), source_gate=lambda c, refs: memory.source_gate(c, refs))
        memory = MemoryStore(conn, sanitize_text=sanitize, append_event=tasks.append_event,
                             invalidate_by_refs=tasks.invalidate_by_refs)
        def record(key):
            return value(memory.append({'client_key': key, 'session_id': 's',
                'role': 'user', 'text': 'synthetic independent draft ' + key}))['record_ref']
        brief = {'purpose': 'synthetic draft', 'target': {'repository': 'repo',
            'issue_numbers': [], 'files': []}, 'constraints': [], 'context_refs': [],
            'conditions': [{'description': 'saved', 'check': 'artifact_saved'}]}
        old = value(tasks.create({'key': 'create', 'session_id': 's', 'brief': brief,
            'origin_record_ref': record('original')}, request_scope=grant))['work_ref']
        correction = record('correction')
        changes, inputs = [], []
        def expert(context, **diagnostics):
            inputs.append(copy.deepcopy(context))
            changes.append(tasks.control({'key': 'change', 'work_ref': context['work_ref'],
                'command': {'kind': 'change', 'brief': brief, 'origin_record_ref': correction}}))
            return {'kind': 'report', 'summary': 'old revision output'}
        result = MockRunner(tasks, memory).run_once(expert, max_steps=2)
        self.assertTrue(changes, 'mock call never entered')
        self.assertTrue(changes[0].ok, changes[0].to_json())
        self.assertEqual(len(changes), 1)
        changed = value(changes[0])['work_ref']
        self.assertEqual(changed['revision'], old['revision'] + 1)
        self.assertEqual(len(inputs), 1)
        released = value(result)
        self.assertEqual((released['status'], released['state'], released['work_ref']),
                         ('released', 'queued', changed))
        self.assertEqual(released['steps'], [])
        self.assertEqual(value(tasks.get_work({'goal_id': old['goal_id'],
            'revision': old['revision']}))['state'], 'superseded')


if __name__ == '__main__':
    unittest.main()
