"""Connected actual MEM/TSK/C14 with bounded mock calls and ordered controls."""
from contextlib import contextmanager
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from pal.contracts_v5 import ErrorCode, Grant, Limits, Result, dumps
from pal.events_v5 import EventReader
from pal.memory_v5 import MemoryStore
from pal.mock_runner_v5 import MockInvoker, MockRunner
from pal.sanitize import sanitize
from pal.tasks_v5 import TaskStore


class MockExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'work.sqlite'
        self.grant = Grant(('github.issue.read',), ('thattor/personal-agent-lab',), Limits(2, 8, 8))
        self.host_limits = Limits(20, 20, 20)
        self.conn, self.tasks, self.memory = self.connect()
        self.addCleanup(lambda: self.conn.close())

    def connect(self):
        conn = sqlite3.connect(self.path, isolation_level=None, timeout=0)
        memory = None
        tasks = TaskStore(conn, host_grant=self.grant, expert_id='expert',
                          host_limits=self.host_limits,
                          source_gate=lambda c, refs: memory.source_gate(c, refs))
        memory = MemoryStore(conn, sanitize_text=sanitize,
                             append_event=tasks.append_event,
                             invalidate_by_refs=tasks.invalidate_by_refs)
        return conn, tasks, memory

    def value(self, result):
        self.assertTrue(result.ok, result)
        return result.value.to_json()

    def record(self, key, text, session='work-session'):
        return self.value(self.memory.append({'client_key': key, 'session_id': session,
                                              'role': 'user', 'text': text}))['record_ref']

    def create(self, origin=None, key='create'):
        origin = origin or self.record('origin-' + key, 'Prepare a reversible local draft')
        request = {'key': key, 'session_id': 'work-session', 'origin_record_ref': origin,
                   'brief': {'purpose': 'Prepare a draft',
                             'target': {'repository': 'thattor/personal-agent-lab',
                                        'issue_numbers': [], 'files': []},
                             'constraints': [], 'context_refs': [],
                             'conditions': [{'description': 'Draft is useful', 'check': 'semantic'}]}}
        return origin, self.value(self.tasks.create(request, request_scope=self.grant))['work_ref']

    def current(self, work):
        return self.value(self.tasks.get_work({'goal_id': work['goal_id']}))

    def control(self, work, command):
        return self.value(self.tasks.control({'key': dumps(['control', work['goal_id'], command]),
                                              'work_ref': work, 'command': command}))

    def stop(self, ref, key='stop'):
        return self.value(self.memory.stop_reference({'key': key, 'source_ref': ref},
                                                      session_id='control-session'))

    @contextmanager
    def held_run(self, *, boundary='callback'):
        entered, proceed = threading.Event(), threading.Event()
        state = {'calls': 0}
        def run():
            conn = None
            try:
                conn, tasks, memory = self.connect()
                original_admit, original_get = tasks.admit_call, tasks.get_call
                def admit(request):
                    state['admission'] = copy.deepcopy(request)
                    if boundary == 'admission':
                        entered.set()
                        if not proceed.wait(5):
                            raise AssertionError('admission barrier timed out')
                    return original_admit(request)
                def get_call(request):
                    result = original_get(request)
                    if boundary == 'entry' and result.ok and result.value.to_json()['status'] == 'admitted':
                        entered.set()
                        if not proceed.wait(5):
                            raise AssertionError('entry barrier timed out')
                        return original_get(request)
                    return result
                tasks.admit_call, tasks.get_call = admit, get_call
                def expert(c12, **metadata):
                    state['calls'] += 1
                    state['context'] = c12
                    state['transaction_open'] = conn.in_transaction
                    if boundary == 'callback':
                        entered.set()
                        if not proceed.wait(5):
                            raise AssertionError('callback barrier timed out')
                    return {'kind': 'report', 'summary': 'one mock report'}
                state['result'] = MockRunner(tasks, memory).run_once(expert)
            except BaseException as error:
                state['error'] = error
                entered.set()
            finally:
                if conn is not None:
                    conn.close()
                if not entered.is_set():
                    state['error'] = AssertionError('worker ended before barrier: ' + str(state.get('result')))
                    entered.set()
        worker = threading.Thread(target=run)
        worker.start()
        try:
            self.assertTrue(entered.wait(5), 'worker did not reach barrier')
            if 'error' in state:
                raise state['error']
            yield state
        finally:
            proceed.set()
            worker.join(5)
            self.assertFalse(worker.is_alive(), 'mock did not actually return')
        if 'error' in state:
            raise state['error']

    def events(self, session='work-session'):
        reader = EventReader(self.conn, page_size=2)
        events, request = [], {'session_id': session}
        for _ in range(100):
            page = self.value(reader.get_events(request))
            if not page['events']:
                return events
            events.extend(page['events'])
            request['after_event_id'] = page['next_cursor']
        self.fail('finite event page did not terminate')

    def test_report_is_durable_progress_and_never_completes_goal(self):
        _, work = self.create()
        seen = []
        def expert(c12, **metadata):
            seen.append(c12)
            self.assertFalse(self.conn.in_transaction)
            return {'kind': 'report', 'summary': 'mock progress'}
        outcome = self.value(MockRunner(self.tasks, self.memory).run_once(expert))
        self.assertEqual((outcome['state'], len(seen), len(outcome['steps'])), ('queued', 1, 1))
        self.assertEqual(outcome['steps'][0]['status'], 'finished')
        self.assertEqual(self.current(work)['state'], 'queued')
        saved = self.events()
        self.assertEqual(len([e for e in saved if e['kind'] == 'progress']), 1)
        self.conn.close()
        self.conn, self.tasks, self.memory = self.connect()
        self.assertEqual(self.events(), saved)
        next_lease = self.value(self.tasks.claim({'runner_id': 'inspect-after-reopen'}))
        self.assertEqual(next_lease['steps'], outcome['steps'])
        metadata = self.value(self.tasks.get_execution_context(
            {'lease_id': next_lease['lease_id'], 'work_ref': next_lease['work_ref']}))
        self.assertEqual(metadata['remaining_budget']['model'], {'work': 7, 'host': 19})
        self.assertEqual(metadata['remaining_budget']['step'], {'work': 7, 'host': 19})

    def test_lookup_reads_actual_bodies_and_hashes_into_next_call(self):
        self.create()
        text = 'reference: verified local context'
        reference = self.record('reference', text)
        self.record('foreign', 'reference: foreign session body', session='foreign')
        seen = []
        def expert(c12, **metadata):
            seen.append(c12)
            if len(seen) == 1:
                self.assertNotIn(reference, [r['ref'] for r in c12['context']])
                return {'kind': 'lookup', 'query': 'reference'}
            record = next(r for r in c12['context'] if r['ref'] == reference)
            self.assertEqual(record['content'], text)
            self.assertEqual(record['hash'], hashlib.sha256(text.encode()).hexdigest())
            self.assertEqual(c12['steps'][0]['result_refs'], [reference])
            self.assertNotIn('foreign session body', json.dumps(c12))
            return {'kind': 'report', 'summary': 'source-backed mock report'}
        outcome = self.value(MockRunner(self.tasks, self.memory).run_once(expert, max_steps=2))
        self.assertEqual((outcome['state'], len(seen), len(outcome['steps'])), ('queued', 2, 2))

    def test_stopped_optional_body_and_derived_steps_are_excluded_after_reclaim(self):
        _, work = self.create()
        text = 'reference: OPTIONAL_PRIVATE_TEXT'
        reference = self.record('reference', text)
        count = []
        def first(c12, **metadata):
            count.append(1)
            return ({'kind': 'lookup', 'query': 'reference'} if len(count) == 1
                    else {'kind': 'report', 'summary': 'Observed OPTIONAL_PRIVATE_TEXT'})
        before = self.value(MockRunner(self.tasks, self.memory).run_once(first, max_steps=2))
        self.stop(reference)
        def after(c12, **metadata):
            self.assertNotIn('OPTIONAL_PRIVATE_TEXT', json.dumps(c12))
            self.assertEqual(c12['steps'], [])
            self.assertIn(reference, metadata['excluded_refs'])
            self.assertEqual(set(metadata['excluded_step_ids']), {s['step_id'] for s in before['steps']})
            return {'kind': 'report', 'summary': 'available origin only'}
        outcome = self.value(MockRunner(self.tasks, self.memory).run_once(after))
        self.assertEqual((outcome['state'], self.current(work)['state']), ('queued', 'queued'))

    def test_stop_between_lookup_search_and_read_is_named_before_next_call(self):
        self.create()
        reference = self.record('reference', 'reference: excluded before read')
        real_search = self.memory.search
        def search(request):
            result = real_search(request)
            self.stop(reference)
            return result
        self.memory.search = search
        seen = []
        def expert(c12, **metadata):
            seen.append(c12)
            if len(seen) == 1:
                return {'kind': 'lookup', 'query': 'reference'}
            self.assertNotIn('excluded before read', json.dumps(c12))
            self.assertIn(reference, metadata['excluded_refs'])
            self.assertEqual(c12['steps'][0]['result_refs'], [])
            return {'kind': 'report', 'summary': 'excluded source was not read'}
        result = self.value(MockRunner(self.tasks, self.memory).run_once(expert, max_steps=2))
        self.assertEqual((result['state'], len(seen)), ('queued', 2))
        lookup_events = [e for e in self.events() if e['kind'] == 'progress' and e['text'].startswith('{')]
        self.assertEqual(json.loads(lookup_events[0]['text'])['lookup_excluded_refs'], [reference])

    def test_concurrent_duplicate_invoker_request_never_enters_second_callable(self):
        ref, _ = self.create()
        lease = self.value(self.tasks.claim({'runner_id': 'one-host'}))
        reservation = self.value(self.tasks.reserve_budget(
            {'key': 'reserve', 'work_ref': lease['work_ref'], 'kind': 'model', 'role': 'expert'}))
        request = {'call_id': dumps(['C15.call', lease['lease_id'], 0]),
                   'lease_id': lease['lease_id'], 'work_ref': lease['work_ref'],
                   'reservation_id': reservation['reservation_id'], 'source_refs': [ref]}
        invoker = MockInvoker()
        entered, proceed = threading.Event(), threading.Event()
        calls, state = [], {}
        def run():
            conn = None
            try:
                conn, tasks, _ = self.connect()
                def callback():
                    calls.append('first')
                    entered.set()
                    if not proceed.wait(5):
                        raise AssertionError('duplicate barrier timed out')
                    return {'kind': 'report', 'summary': 'returned once'}
                state['result'] = invoker.invoke(tasks, request, callback)
            except BaseException as error:
                state['error'] = error
                entered.set()
            finally:
                if conn is not None:
                    conn.close()
        worker = threading.Thread(target=run)
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            if 'error' in state:
                raise state['error']
            duplicate = invoker.invoke(self.tasks, request, lambda: calls.append('second'))
            self.assertEqual(duplicate.error.code, ErrorCode.CONFLICT)
            self.assertEqual(calls, ['first'])
        finally:
            proceed.set()
            worker.join(5)
            self.assertFalse(worker.is_alive())
        if 'error' in state:
            raise state['error']
        self.value(state['result'])
        self.assertEqual(self.value(self.tasks.get_call({'call_id': request['call_id']}))['status'], 'returned')

    def test_pause_before_admission_and_after_admission_before_entry_invoke_zero_times(self):
        for boundary in ('admission', 'entry'):
            with self.subTest(boundary=boundary):
                _, work = self.create(key=boundary)
                with self.held_run(boundary=boundary) as state:
                    self.control(work, 'pause')
                self.assertEqual(state['calls'], 0)
                self.assertEqual(self.value(state['result'])['state'], 'paused')

    def test_held_pause_keeps_slot_until_actual_callback_return(self):
        _, work = self.create()
        with self.held_run() as state:
            controlled = self.control(work, 'pause')
            self.assertEqual(controlled['control_status'], 'pause_requested')
            self.assertFalse(state['transaction_open'])
            admission = state['admission']
            premature = self.tasks.release({'lease_id': admission['lease_id'],
                                            'work_ref': admission['work_ref'],
                                            'outcome': 'yield', 'reason': 'too early'})
            self.assertEqual(premature.error.code, ErrorCode.CONFLICT)
            self.assertEqual(self.tasks.claim({'runner_id': 'other'}).error.code, ErrorCode.CONFLICT)
        self.assertEqual(self.value(state['result'])['state'], 'paused')
        self.assertEqual(state['calls'], 1)
        self.assertEqual([e for e in self.events() if e['kind'] == 'progress'], [])

    def test_cancel_held_call_invalidates_immediately_and_keeps_occupancy(self):
        _, work = self.create()
        with self.held_run() as state:
            before = self.current(work)['work_ref']
            self.control(work, 'cancel')
            current = self.current(work)
            self.assertEqual(current['state'], 'cancelled')
            self.assertEqual(current['work_ref']['epoch'], before['epoch'] + 1)
            self.assertEqual(self.tasks.claim({'runner_id': 'other'}).error.code, ErrorCode.CONFLICT)
        self.assertEqual(self.value(state['result'])['state'], 'cancelled')
        self.assertEqual(self.value(self.tasks.claim({'runner_id': 'other'})), {'status': 'empty'})

    def test_stop_held_call_requeues_then_required_source_fails_once(self):
        ref, work = self.create()
        with self.held_run() as state:
            self.stop(ref)
            self.assertEqual(self.tasks.claim({'runner_id': 'other'}).error.code, ErrorCode.CONFLICT)
        self.assertEqual(self.value(state['result'])['state'], 'queued')
        calls = []
        outcome = self.value(MockRunner(self.tasks, self.memory).run_once(
            lambda *args, **kwargs: calls.append(1)))
        self.assertEqual((outcome['state'], calls), ('failed', []))
        self.assertEqual(self.current(work)['state'], 'failed')
        self.assertEqual(self.value(self.tasks.claim({'runner_id': 'later'})), {'status': 'empty'})

    def test_latest_control_wins_during_source_draining(self):
        for order, expected in ((('stop', 'pause'), 'paused'),
                                (('pause', 'stop'), 'paused'),
                                (('stop', 'cancel'), 'cancelled')):
            with self.subTest(order=order):
                key = '-'.join(order)
                ref, work = self.create(key=key)
                with self.held_run() as state:
                    for command in order:
                        if command == 'stop':
                            self.stop(ref, key='stop-' + key)
                        else:
                            self.value(self.tasks.control({'key': 'control-' + key,
                                                           'work_ref': work, 'command': command}))
                self.assertEqual(self.value(state['result'])['state'], expected)

    def test_raising_mock_is_ended_without_leaking_error_and_never_refunded(self):
        _, work = self.create()
        def expert(*args, **kwargs):
            raise RuntimeError('PRIVATE_CALLBACK_FAILURE')
        outcome = self.value(MockRunner(self.tasks, self.memory).run_once(expert))
        self.assertEqual(outcome['state'], 'failed')
        self.assertNotIn('PRIVATE_CALLBACK_FAILURE', json.dumps(outcome))
        call = self.value(self.tasks.get_call({'call_id': outcome['call_ids'][0]}))
        self.assertEqual(call['status'], 'raised')
        self.create(key='another')
        lease = self.value(self.tasks.claim({'runner_id': 'another'}))
        context = self.value(self.tasks.get_execution_context(
            {'lease_id': lease['lease_id'], 'work_ref': lease['work_ref']}))
        self.assertEqual(context['remaining_budget']['model']['host'], 19)
        self.assertEqual(self.current(work)['state'], 'failed')

    def test_zero_work_or_host_model_or_step_budget_prevents_invocation(self):
        for kind, owner in (('model', 'work'), ('step', 'work'), ('model', 'host'), ('step', 'host')):
            with self.subTest(kind=kind, owner=owner):
                self.conn.close()
                self.path = Path(self.temp.name) / f'{kind}-{owner}.sqlite'
                limits = Limits(2, 0 if kind == 'step' else 8, 0 if kind == 'model' else 8)
                self.grant = Grant(('github.issue.read',), ('thattor/personal-agent-lab',),
                                   limits if owner == 'work' else Limits(2, 8, 8))
                self.host_limits = limits if owner == 'host' else Limits(20, 20, 20)
                self.conn, self.tasks, self.memory = self.connect()
                _, work = self.create()
                calls = []
                result = MockRunner(self.tasks, self.memory).run_once(lambda *a, **k: calls.append(1))
                self.assertEqual(calls, [])
                if owner == 'host':
                    self.assertEqual(result.error.code, ErrorCode.LIMIT)
                    self.assertEqual(self.current(work)['state'], 'queued')
                else:
                    self.assertEqual(self.value(result)['state'], 'failed')

    def test_persisted_admission_replay_never_dispatches_and_reopen_stays_blocked(self):
        ref, _ = self.create()
        lease = self.value(self.tasks.claim({'runner_id': 'old-host'}))
        work = lease['work_ref']
        self.value(self.tasks.register_sources({'work_ref': work, 'refs': [ref]}))
        reservation = self.value(self.tasks.reserve_budget(
            {'key': 'reserve', 'work_ref': work, 'kind': 'model', 'role': 'expert'}))
        admission = {'call_id': dumps(['C15.call', lease['lease_id'], 0]),
                     'lease_id': lease['lease_id'], 'work_ref': work,
                     'reservation_id': reservation['reservation_id'], 'source_refs': [ref]}
        first = self.tasks.admit_call(admission)
        self.assertEqual(self.tasks.admit_call(admission), first)
        calls = []
        replay = MockInvoker().invoke(self.tasks, admission, lambda: calls.append(1))
        self.assertEqual((replay.error.code, calls), (ErrorCode.CONFLICT, []))
        self.conn.close()
        self.conn, self.tasks, self.memory = self.connect()
        result = MockRunner(self.tasks, self.memory).run_once(lambda *a, **k: calls.append(1))
        self.assertEqual((result.error.code, calls), (ErrorCode.CONFLICT, []))
        release = self.tasks.release({'lease_id': lease['lease_id'], 'work_ref': work,
                                      'outcome': 'failed', 'reason': 'cannot infer cessation'})
        self.assertEqual(release.error.code, ErrorCode.CONFLICT)

    def test_cessation_persistence_failure_is_bounded_and_keeps_slot(self):
        self.create()
        calls, endings = [], []
        original = self.tasks.end_call
        def unavailable(request):
            endings.append(copy.deepcopy(request))
            return Result.failure(ErrorCode.UNAVAILABLE, 'fixture persistence unavailable')
        self.tasks.end_call = unavailable
        def expert(*args, **kwargs):
            calls.append(1)
            return {'kind': 'report', 'summary': 'completed mock callback'}
        result = MockRunner(self.tasks, self.memory).run_once(expert)
        self.tasks.end_call = original
        self.assertFalse(result.ok)
        self.assertEqual((len(calls), len(endings)), (1, 3))
        self.assertTrue(all(r == endings[0] for r in endings))
        self.assertEqual(self.value(self.tasks.get_call(
            {'call_id': endings[0]['call_id']}))['status'], 'admitted')
        self.assertEqual(self.tasks.claim({'runner_id': 'new'}).error.code, ErrorCode.CONFLICT)

    def test_pre_admission_unavailable_yields_and_explicit_later_run_is_safe(self):
        for owner, name in ((self.tasks, 'get_execution_context'), (self.tasks, 'register_sources'),
                            (self.memory, 'read'), (self.tasks, 'reserve_budget'),
                            (self.tasks, 'admit_call')):
            with self.subTest(boundary=name):
                _, work = self.create(key=name)
                runner = MockRunner(self.tasks, self.memory)
                calls = []
                def expert(*args, **kwargs):
                    calls.append(1)
                    return {'kind': 'report', 'summary': 'usable'}
                original = getattr(owner, name)
                setattr(owner, name, lambda *a, **k: Result.failure(ErrorCode.UNAVAILABLE, 'SECRET fixture'))
                result = runner.run_once(expert)
                setattr(owner, name, original)
                self.assertEqual(self.current(work)['state'], 'queued')
                self.assertEqual(calls, [])
                self.assertEqual(self.value(result)['reason_code'], 'unavailable')
                self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_tsk_lease WHERE active=1').fetchone()[0], 0)
                self.value(runner.run_once(expert))
                self.assertEqual(calls, [1])
                self.control(work, 'cancel')

    def test_same_input_write_retry_handles_one_shot_and_lost_commit_receipts(self):
        for lost in (False, True):
            with self.subTest(commit_then_unavailable=lost):
                _, work = self.create(key=str(lost))
                runner = MockRunner(self.tasks, self.memory)
                attempts = {'begin_step': [], 'finish_step': []}
                originals = {}
                for name in attempts:
                    original = getattr(self.tasks, name)
                    originals[name] = original
                    def flaky(request, _name=name, _original=original, **kwargs):
                        attempts[_name].append((copy.deepcopy(request), copy.deepcopy(kwargs)))
                        if len(attempts[_name]) == 1:
                            if lost:
                                self.value(_original(request, **kwargs))
                            return Result.failure(ErrorCode.UNAVAILABLE, 'lost response')
                        return _original(request, **kwargs)
                    setattr(self.tasks, name, flaky)
                calls = []
                def expert(*a, **k):
                    calls.append(1)
                    return {'kind': 'report', 'summary': 'once'}
                result = runner.run_once(expert)
                for name, original in originals.items():
                    setattr(self.tasks, name, original)
                self.value(result)
                self.assertEqual(calls, [1])
                for requests in attempts.values():
                    self.assertEqual(len(requests), 2)
                    self.assertEqual(requests[0], requests[1])
                goal = work['goal_id']
                self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_tsk_step WHERE goal=?', (goal,)).fetchone()[0], 1)
                self.assertEqual(self.conn.execute('SELECT used FROM v5_tsk_usage WHERE goal=? AND kind=?', (goal, 'step')).fetchone()[0], 1)
                self.assertEqual(sum(e['kind'] == 'progress' and e.get('work_ref', {}).get('goal_id') == goal for e in self.events()), 1)
                self.control(work, 'cancel')

    def persistent_write_failure(self, name):
        _, work = self.create()
        runner = MockRunner(self.tasks, self.memory)
        calls, attempts = [], []
        original = getattr(self.tasks, name)
        def unavailable(request, **kwargs):
            attempts.append((copy.deepcopy(request), copy.deepcopy(kwargs)))
            return Result.failure(ErrorCode.UNAVAILABLE, 'SECRET fixture')
        setattr(self.tasks, name, unavailable)
        def expert(*args, **kwargs):
            calls.append(1)
            return {'kind': 'report', 'summary': 'do not discard'}
        result = runner.run_once(expert)
        setattr(self.tasks, name, original)
        self.assertEqual(result.error.code, ErrorCode.UNAVAILABLE)
        self.assertNotIn('SECRET', dumps(result))
        self.assertEqual(len(attempts), 3)
        self.assertTrue(all(item == attempts[0] for item in attempts))
        self.assertEqual(self.current(work)['state'], 'running')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_tsk_lease WHERE active=1').fetchone()[0], 1)
        before = self.conn.execute('SELECT * FROM v5_tsk_usage ORDER BY kind').fetchall()
        again = runner.run_once(expert)
        self.assertFalse(again.ok)
        self.assertEqual(calls, [1])
        self.assertEqual(before, self.conn.execute('SELECT * FROM v5_tsk_usage ORDER BY kind').fetchall())
        self.assertEqual(self.current(work)['state'], 'running')

    def test_persistent_begin_failure_retains_returned_output_and_blocks_reentry(self):
        self.persistent_write_failure('begin_step')

    def test_persistent_finish_failure_retains_started_step_and_blocks_reentry(self):
        self.persistent_write_failure('finish_step')

    def test_uncertain_admission_never_retries_or_fails_goal(self):
        _, work = self.create()
        runner = MockRunner(self.tasks, self.memory)
        original = self.tasks.admit_call
        def lost(request):
            self.value(original(request))
            return Result.failure(ErrorCode.UNAVAILABLE, 'lost admission')
        self.tasks.admit_call = lost
        calls = []
        result = runner.run_once(lambda *a, **k: calls.append(1))
        self.tasks.admit_call = original
        self.assertFalse(result.ok)
        before = self.conn.execute('SELECT * FROM v5_tsk_usage').fetchall()
        self.assertFalse(runner.run_once(lambda *a, **k: calls.append(1)).ok)
        self.assertEqual(calls, [])
        self.assertEqual(self.current(work)['state'], 'running')
        self.assertEqual(before, self.conn.execute('SELECT * FROM v5_tsk_usage').fetchall())

    def test_lookup_unavailable_after_step_start_preserves_output(self):
        _, work = self.create()
        runner = MockRunner(self.tasks, self.memory)
        calls = []
        original = self.memory.search
        self.memory.search = lambda request: Result.failure(ErrorCode.UNAVAILABLE, 'SECRET search')
        def expert(*a, **k):
            calls.append(1)
            return {'kind': 'lookup', 'query': ''}
        result = runner.run_once(expert)
        self.memory.search = original
        self.assertEqual(result.error.code, ErrorCode.UNAVAILABLE)
        self.assertEqual(self.current(work)['state'], 'running')
        self.assertFalse(runner.run_once(expert).ok)
        self.assertEqual(calls, [1])
        self.assertEqual(self.conn.execute("SELECT used FROM v5_tsk_usage WHERE kind='model'").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT used FROM v5_tsk_usage WHERE kind='step'").fetchone()[0], 1)
        self.assertEqual(sum(e['kind'] == 'progress' for e in self.events()), 0)

    def test_lost_reservation_response_is_not_refunded_and_later_run_is_explicit(self):
        _, work = self.create()
        runner = MockRunner(self.tasks, self.memory)
        original = self.tasks.reserve_budget
        def lost(request):
            self.value(original(request))
            return Result.failure(ErrorCode.UNAVAILABLE, 'lost reservation')
        self.tasks.reserve_budget = lost
        calls = []
        def expert(*a, **k):
            calls.append(1)
            return {'kind': 'report', 'summary': 'later explicit attempt'}
        self.value(runner.run_once(expert))
        self.tasks.reserve_budget = original
        self.assertEqual(calls, [])
        self.assertEqual(self.current(work)['state'], 'queued')
        self.value(runner.run_once(expert))
        self.assertEqual(calls, [1])
        self.assertEqual(self.conn.execute("SELECT used FROM v5_tsk_usage WHERE kind='model'").fetchone()[0], 2)

    def test_pause_committed_during_local_retry_wins_over_runner_failure(self):
        _, work = self.create()
        control_conn, controls, _ = self.connect()
        self.addCleanup(control_conn.close)
        original = self.tasks.begin_step
        attempts = []
        def transient(request):
            attempts.append(copy.deepcopy(request))
            if len(attempts) == 1:
                self.value(controls.control({'key': 'pause-during-write', 'work_ref': request['work_ref'], 'command': 'pause'}))
                return Result.failure(ErrorCode.UNAVAILABLE, 'temporary')
            return original(request)
        self.tasks.begin_step = transient
        calls = []
        def expert(*a, **k):
            calls.append(1)
            return {'kind': 'report', 'summary': 'fenced'}
        result = MockRunner(self.tasks, self.memory).run_once(expert)
        self.tasks.begin_step = original
        self.assertEqual(self.value(result)['state'], 'paused')
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0], attempts[1])
        self.assertEqual(calls, [1])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_tsk_lease WHERE active=1').fetchone()[0], 0)
        self.assertEqual(sum(e['kind'] == 'progress' for e in self.events()), 0)

    def test_fenced_output_releases_after_persistent_write_failure_or_reentry(self):
        for boundary in ('begin_step', 'finish_step'):
            for reentry in (False, True):
                for command in ('pause', 'cancel', 'stop'):
                    with self.subTest(boundary=boundary, reentry=reentry, command=command):
                        key = f'{boundary}-{reentry}-{command}'
                        origin, work = self.create(key=key)
                        runner = MockRunner(self.tasks, self.memory)
                        calls, attempts = [], []
                        def control():
                            if command == 'stop':
                                self.stop(origin, key=key)
                            else:
                                self.control(work, command)
                        original = getattr(self.tasks, boundary)
                        def unavailable(request, **kwargs):
                            attempts.append(1)
                            if len(attempts) == 3 and not reentry:
                                control()
                            return Result.failure(ErrorCode.UNAVAILABLE, 'local persistence failure')
                        def expert(*a, **k):
                            calls.append(1)
                            return {'kind': 'report', 'summary': 'fenced output'}
                        setattr(self.tasks, boundary, unavailable)
                        result = runner.run_once(expert)
                        setattr(self.tasks, boundary, original)
                        if reentry:
                            self.assertFalse(result.ok)
                            control()
                            result = runner.run_once(expert)
                        try:
                            self.assertEqual(self.value(result)['state'],
                                             {'pause': 'paused', 'cancel': 'cancelled', 'stop': 'queued'}[command])
                            self.assertEqual(calls, [1])
                            self.assertEqual(len(attempts), 3)
                            self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_tsk_lease WHERE active=1').fetchone()[0], 0)
                            usage = dict(self.conn.execute('SELECT kind,used FROM v5_tsk_usage WHERE goal=?', (work['goal_id'],)))
                            self.assertEqual(usage.get('model'), 1)
                            self.assertEqual(usage.get('step', 0), int(boundary == 'finish_step'))
                            self.assertFalse(any(e['kind'] == 'progress' and e.get('work_ref', {}).get('goal_id') == work['goal_id'] for e in self.events()))
                        finally:
                            held = self.value(self.tasks.claim({'runner_id': runner.runner_id}))
                            if 'lease_id' in held:
                                self.value(self.tasks.release({'lease_id': held['lease_id'],
                                    'work_ref': held['work_ref'], 'outcome': 'failed', 'reason': 'test cleanup'}))
                            if self.current(work)['state'] not in ('cancelled', 'failed'):
                                self.control(work, 'cancel')

    def test_reentry_cannot_release_uncertain_admitted_call_even_after_cancel(self):
        _, work = self.create()
        runner = MockRunner(self.tasks, self.memory)
        original = self.tasks.admit_call
        def lost(request):
            self.value(original(request))
            return Result.failure(ErrorCode.UNAVAILABLE, 'lost admission')
        self.tasks.admit_call = lost
        calls = []
        self.assertFalse(runner.run_once(lambda *a, **k: calls.append(1)).ok)
        self.tasks.admit_call = original
        self.control(work, 'cancel')
        before = self.conn.execute('SELECT * FROM v5_tsk_usage').fetchall()
        self.assertFalse(runner.run_once(lambda *a, **k: calls.append(1)).ok)
        self.assertEqual(calls, [])
        self.assertEqual(before, self.conn.execute('SELECT * FROM v5_tsk_usage').fetchall())
        self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_tsk_lease WHERE active=1').fetchone()[0], 1)
        self.assertEqual(self.current(work)['state'], 'cancelled')


if __name__ == '__main__':
    unittest.main()
