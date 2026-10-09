"""Frozen RECOVERY01 TSK acceptance: actual managed Host and fresh file SQLite.

No process-death proof is simulated: HOST/Root own subprocess acceptance. Closing
an idle real guard ends the scoped cooperative host lifetime for these owner tests.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from pal.contracts_v5 import Grant, Limits, dumps, loads
from pal.tasks_v5 import TaskStore
from pal.memory_v5 import MemoryStore
from pal.artifacts_v5 import ArtifactStore
from pal.verification_v5 import VerificationStore
from pal.events_v5 import EventReader
import test_tasks_ask_v5 as existing

MAX = 2**63 - 1


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        # Import in setUp makes the initial RED explicitly implementation absence,
        # while still discovering every fixed expectation (no skipped fake guard).
        from pal.mock_host_v5 import MockHostSession
        self.Host = MockHostSession
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'managed.sqlite'
        self.serial = 0
        self.grant = Grant(('github.issue.read',), ('repo',), Limits(0, 20, 20))
        self.guard = self.Host.open(self.path)
        self.addCleanup(self.close_guard, self.guard)
        self.conn, self.t, self.mem, self.art, self.ver = self.connect(self.guard)
        self.registration = self.value(self.t.register_host())
        self.value(self.t.finish_startup())
        self.origin = self.record('origin'); self.optional = self.record('optional')
        self.draft = {'purpose': 'local draft', 'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
                      'constraints': [], 'context_refs': [],
                      'conditions': [{'description': 'saved', 'check': 'artifact_saved'}]}
        made = self.value(self.t.create({'key': self.key(), 'session_id': 'session',
            'origin_record_ref': self.origin, 'brief': self.draft}, request_scope=self.grant))
        self.goal = made['work_ref']['goal_id']
        self.lease = self.value(self.t.claim({'runner_id': self.guard.runner_id}))

    @staticmethod
    def close_guard(guard):
        if guard.phase != 'closed': guard.close()

    def connect(self, guard=None):
        conn = sqlite3.connect(self.path, isolation_level=None, timeout=0, factory=existing.FaultConnection)
        self.addCleanup(conn.close)
        mem = art = ver = None
        kwargs = {'startup_guard': guard} if guard is not None else {}
        t = TaskStore(conn, host_grant=self.grant, host_limits=Limits(0, 100, 100), expert_id='expert',
            source_gate=lambda c, refs: mem.source_gate(c, refs),
            artifact_inspect=lambda c, r: art.inspect(c, r),
            verification_inspect=lambda c, r: ver.inspect(c, r), **kwargs)
        mem = MemoryStore(conn, sanitize_text=lambda x: x, append_event=t.append_event,
                          invalidate_by_refs=t.invalidate_by_refs)
        art = ArtifactStore(conn, authorize_save=t.authorize_artifact_save, source_gate=mem.source_gate)
        ver = VerificationStore(conn, context=t.verification_context, artifact_inspect=art.inspect,
                                source_gate=mem.source_gate)
        return conn, t, mem, art, ver

    def key(self):
        self.serial += 1; return 'recovery-fixture-' + str(self.serial)

    def value(self, result):
        self.assertTrue(result.ok, result.to_json()); return result.value.to_json()

    def error(self, result, code):
        self.assertFalse(result.ok, result.to_json()); self.assertEqual(result.error.code, code)
        self.assertEqual(result.error.refs, ()); self.assertLess(len(result.error.message), 160)
        self.assertNotIn('private', result.error.message)

    def record(self, text):
        return self.value(self.mem.append({'client_key': self.key(), 'session_id': 'session',
            'role': 'user', 'text': text}))['record_ref']

    def snapshot(self): return tuple(self.conn.iterdump())
    def usage(self):
        return (self.conn.execute('SELECT * FROM v5_tsk_usage ORDER BY goal,kind').fetchall(),
                self.conn.execute('SELECT * FROM v5_tsk_host ORDER BY kind').fetchall(),
                self.conn.execute('SELECT * FROM v5_tsk_reservation ORDER BY id').fetchall())
    def work(self, revision=None):
        request = {'goal_id': self.goal}
        if revision is not None: request['revision'] = revision
        return self.value(self.t.get_work(request))
    def events(self): return self.value(EventReader(self.conn).get_events({'session_id': 'session'}))['events']

    def call(self, outcome='returned', refs=None):
        refs = refs or [self.origin]
        work = self.lease['work_ref']
        self.value(self.t.register_sources({'work_ref': work, 'refs': refs}))
        context = self.value(self.t.get_execution_context({'lease_id': self.lease['lease_id'], 'work_ref': work}))
        index = context['next_step_index']
        reservation = self.value(self.t.reserve_budget({'key': self.key(), 'work_ref': work,
            'kind': 'model', 'role': 'expert'}))['reservation_id']
        call_id = dumps(['C15.call', self.lease['lease_id'], index])
        self.value(self.t.admit_call({'call_id': call_id, 'lease_id': self.lease['lease_id'],
            'work_ref': work, 'reservation_id': reservation, 'source_refs': refs}))
        if outcome is not None: self.value(self.t.end_call({'call_id': call_id, 'outcome': outcome}))
        return call_id

    def stage(self, kind='report'):
        call_id = self.call(refs=[self.origin, self.optional])
        actions = {'report': {'kind': 'report', 'summary': '日本語の記録'},
                   'lookup': {'kind': 'lookup', 'query': 'query', 'source_refs': [self.origin]},
                   'ask': {'kind': 'ask', 'question': 'いつですか', 'missing_fact': 'date', 'source_refs': [self.origin]},
                   'compose': {'kind': 'compose', 'content': '本文', 'media_type': 'text/plain', 'source_refs': [self.origin]}}
        step = self.value(self.t.begin_step({'key': self.key(), 'work_ref': self.lease['work_ref'], 'action': actions[kind]}))
        return call_id, step

    def reopen(self):
        self.old_runner = self.guard.runner_id
        self.conn.close(); self.guard.close()
        self.guard = self.Host.open(self.path); self.addCleanup(self.close_guard, self.guard)
        self.conn, self.t, self.mem, self.art, self.ver = self.connect(self.guard)
        self.registration = self.value(self.t.register_host())
        return self.registration

    def recover(self, key='fixed-recovery', lease=None):
        return self.t.recover({'key': key, 'lease_id': lease or self.lease['lease_id']})

    def settled(self, result, interrupted=()):
        receipt = self.value(result)
        self.assertEqual(set(receipt), {'disposition', 'work_ref', 'state', 'control_status', 'recovered_lease_id', 'interrupted_call_ids'})
        self.assertEqual(receipt['disposition'], 'settled'); self.assertEqual(receipt['control_status'], 'none')
        self.assertEqual(receipt['recovered_lease_id'], self.lease['lease_id'])
        self.assertEqual(receipt['interrupted_call_ids'], list(interrupted))
        self.assertEqual(self.conn.execute('SELECT active FROM v5_tsk_lease WHERE id=?', (self.lease['lease_id'],)).fetchone()[0], 0)
        return receipt

    def test_registration_snapshot_retry_and_empty_finish_are_idempotent(self):
        self.reopen(); before = self.snapshot()
        expected = {'session_id': self.guard.session_id, 'runner_id': self.guard.runner_id, 'orphan_lease_id': self.lease['lease_id']}
        self.assertEqual(self.registration, expected)
        self.assertEqual(self.value(self.t.register_host()), expected); self.assertEqual(self.snapshot(), before)
        self.error(self.t.finish_startup(), 'conflict'); self.assertEqual(self.snapshot(), before)
        self.settled(self.recover()); before = self.snapshot()
        ready = self.value(self.t.finish_startup())
        self.assertEqual(ready, {'session_id': self.guard.session_id, 'runner_id': self.guard.runner_id, 'status': 'ready'})
        self.assertEqual(self.value(self.t.finish_startup()), ready); self.assertEqual(self.snapshot(), before)

    def test_closed_recover_input_no_key_consumption(self):
        self.reopen()
        for request in ({}, {'key': '', 'lease_id': 'x'}, {'key': 'x', 'lease_id': False},
                        {'key': 'x', 'lease_id': 'x', 'ceased': True}, {'key': 'x', 'lease_id': 'x', 'status': 'returned'}):
            with self.subTest(request=request):
                before = self.snapshot(); self.error(self.t.recover(request), 'invalid_input'); self.assertEqual(self.snapshot(), before)
        self.error(self.recover(lease='missing'), 'not_found'); self.settled(self.recover())

    def test_startup_only_and_replay_at_later_start_is_historical(self):
        self.error(self.recover(), 'conflict')
        self.reopen(); receipt = self.settled(self.recover())
        before = self.snapshot(); self.assertEqual(self.value(self.recover()), receipt); self.assertEqual(self.snapshot(), before)
        self.error(self.recover(lease='different'), 'conflict')
        self.error(self.recover(key='new-key'), 'conflict')
        self.value(self.t.finish_startup()); self.lease2 = self.value(self.t.claim({'runner_id': self.guard.runner_id}))
        self.reopen(); before = self.snapshot()
        self.assertEqual(self.value(self.recover()), receipt); self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.conn.execute('SELECT active FROM v5_tsk_lease WHERE id=?', (self.lease2['lease_id'],)).fetchone()[0], 1)
        self.error(self.t.finish_startup(), 'conflict')

    def test_admitted_interrupted_fences_once_no_refund_or_output(self):
        call = self.call(None); usage = self.usage(); old = self.work()['work_ref']; self.reopen(); events = len(self.events())
        out = self.settled(self.recover(), [call]); self.assertEqual(out['state'], 'queued')
        self.assertEqual(out['work_ref'], {**old, 'epoch': old['epoch'] + 1}); self.assertEqual(self.usage(), usage)
        observed = self.value(self.t.get_call({'call_id': call}))
        self.assertEqual((observed['status'], observed['may_enter'], observed['step_id']), ('interrupted', False, None))
        self.assertEqual(len(self.events()), events + 1)
        event=self.events()[-1]; self.assertEqual((event['kind'],event['work_ref']),('state',out['work_ref']))
        before = self.snapshot(); self.error(self.t.end_call({'call_id': call, 'outcome': 'returned'}), 'conflict')
        self.assertEqual(self.snapshot(), before)

    def test_known_ended_without_step_preserves_status(self):
        for ending in ('returned', 'raised', 'not_entered'):
            with self.subTest(ending=ending):
                self.setUp(); call = self.call(ending); usage = self.usage(); self.reopen()
                self.settled(self.recover()); self.assertEqual(self.value(self.t.get_call({'call_id': call}))['status'], ending)
                self.assertEqual(self.usage(), usage)

    def test_reservation_only_is_consumed_history_and_zero_budget_still_cleans(self):
        self.value(self.t.reserve_budget({'key': self.key(), 'work_ref': self.lease['work_ref'], 'kind': 'model', 'role': 'expert'}))
        self.conn.execute('UPDATE v5_tsk_host SET ceiling=used'); usage = self.usage(); self.reopen()
        self.conn.execute('UPDATE v5_tsk_host SET ceiling=used'); usage = self.usage()
        self.settled(self.recover()); self.assertEqual(self.usage(), usage)
        self.value(self.t.finish_startup())
        self.error(self.t.claim({'runner_id': self.guard.runner_id}), 'limit')

    def test_safe_started_steps_abandon_and_finished_history_remains(self):
        for kind in ('report', 'lookup', 'ask'):
            with self.subTest(kind=kind):
                self.setUp(); _, step = self.stage(kind); usage = self.usage(); self.reopen(); self.settled(self.recover())
                saved = loads(self.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?', (step['step_id'],)).fetchone()[0])
                self.assertEqual(saved, {**step, 'status': 'abandoned'}); self.assertEqual(self.usage(), usage)
        self.setUp(); _, step = self.stage(); done = self.value(self.t.finish_step({'work_ref': self.lease['work_ref'], 'step_id': step['step_id'], 'result_refs': []}))
        self.reopen(); self.settled(self.recover())
        self.assertEqual(loads(self.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?', (step['step_id'],)).fetchone()[0]), done)

    def test_saved_compose_receipt_and_started_compose_hold_without_writes(self):
        for saved in (False, True):
            with self.subTest(saved=saved):
                self.setUp(); _, step = self.stage('compose')
                req = {'key': dumps(['C08.save', self.lease['work_ref'], step['step_id']]), 'work_ref': self.lease['work_ref'],
                       'step_id': step['step_id'], **{k:v for k,v in step['action'].items() if k != 'kind'}}
                receipt = self.value(self.art.save(req)) if saved else None
                self.reopen(); before = self.snapshot()
                out = self.value(self.recover())
                self.assertEqual(out, {'disposition': 'held', 'work_ref': self.work()['work_ref'], 'state': 'running', 'control_status': 'none',
                    'lease_id': self.lease['lease_id'], 'step_id': step['step_id'], 'reason': 'artifact_tail'})
                self.assertEqual(self.snapshot(), before); self.assertEqual(self.guard.phase, 'startup')
                self.assertEqual(self.value(self.recover()), out); self.error(self.t.finish_startup(), 'conflict')
                self.assertEqual(self.snapshot(), before)
                if saved: self.assertEqual(self.value(self.art.get_by_key({'key': req['key']})), receipt)

    def test_atomic_ask_receipt_is_history_without_reopening_question(self):
        _, step = self.stage('ask'); req = {'key': dumps(['C04.ask', self.lease['work_ref'], step['step_id']]),
            'work_ref': self.lease['work_ref'], 'step_id': step['step_id'], **{k:v for k,v in step['action'].items() if k != 'kind'}}
        receipt = self.value(self.t.ask(req)); usage = self.usage(); self.reopen(); before = self.snapshot()
        self.assertIsNone(self.registration['orphan_lease_id']); self.value(self.t.finish_startup())
        self.assertEqual(self.value(self.t.get_question_by_key({'key': req['key']})), receipt)
        self.assertEqual(self.work()['state'], 'waiting_input'); self.assertEqual(self.snapshot(), before); self.assertEqual(self.usage(), usage)

    def test_half_committed_ask_refuses_instead_of_abandoning_question(self):
        _, step = self.stage('ask')
        self.conn.execute('INSERT INTO v5_tsk_question VALUES (?,?,?,?,?,?,?,?,NULL)',
            ('half-question', self.goal, 1, step['step_id'], step['action']['question'], step['action']['missing_fact'], dumps([self.origin]), 'open'))
        self.reopen(); before = self.snapshot(); self.error(self.recover(), 'unavailable'); self.assertEqual(self.snapshot(), before)

    def test_corrupt_call_reservation_sources_indices_and_links_refuse_atomically(self):
        cases = ('status', 'id', 'source_shape', 'source_missing', 'source_extra', 'work_epoch', 'sql_index', 'reservation_binding', 'step_bool', 'step_link', 'step_status', 'flags')
        for case in cases:
            with self.subTest(case=case):
                self.setUp(); call, step = self.stage(); self.reopen()
                if case == 'status': self.conn.execute("UPDATE v5_tsk_call SET status='unknown'")
                elif case == 'id':
                    self.conn.execute("UPDATE v5_tsk_call SET id=''"); self.conn.execute("UPDATE v5_tsk_reservation SET binding='' WHERE kind='model'")
                elif case.startswith('source'):
                    refs = {'source_shape': {}, 'source_missing': [], 'source_extra': [self.origin, {'kind':'record','id':'unregistered'}]}[case]
                    self.conn.execute('UPDATE v5_tsk_call SET sources=?', (dumps(refs),))
                elif case == 'work_epoch':
                    self.conn.execute('UPDATE v5_tsk_call SET work=?', (dumps({**self.lease['work_ref'], 'epoch':self.lease['work_ref']['epoch']+1}),))
                elif case == 'sql_index': self.conn.execute('UPDATE v5_tsk_call SET idx=-1')
                elif case == 'reservation_binding': self.conn.execute("UPDATE v5_tsk_reservation SET binding='forged' WHERE kind='model'")
                elif case == 'flags': self.conn.execute('INSERT INTO v5_tsk_control VALUES (?,?,0,2) ON CONFLICT(goal,revision) DO UPDATE SET drain=2', (self.goal,1))
                elif case == 'step_link': self.conn.execute("UPDATE v5_tsk_call SET step='missing'")
                else:
                    wire = copy.deepcopy(step); wire['index' if case == 'step_bool' else 'status'] = True if case == 'step_bool' else 'unknown'
                    self.conn.execute('UPDATE v5_tsk_step SET wire=?', (dumps(wire),))
                before = self.snapshot(); self.error(self.recover(), 'unavailable'); self.assertEqual(self.snapshot(), before)
                self.assertFalse(self.conn.in_transaction); self.error(self.t.finish_startup(), 'conflict')

    def test_guardless_and_other_session_same_runner_text_cannot_execute(self):
        call, step = self.stage('compose'); self.reopen(); _, plain, _, _, _ = self.connect()
        targets = (self.t, plain)
        for target in targets:
            for operation in (
                lambda: target.claim({'runner_id': self.old_runner}),
                lambda: target.end_call({'call_id': call, 'outcome': 'returned'}),
                lambda: target.release({'lease_id':self.lease['lease_id'],'work_ref':self.lease['work_ref'],'outcome':'yield','reason':'no proof'}),
                lambda: target.begin_step({'key':self.key(),'work_ref':self.lease['work_ref'],'action':{'kind':'report','summary':'no'}}),
                lambda: target.reserve_budget({'key':self.key(),'work_ref':self.lease['work_ref'],'kind':'model','role':'expert'}),
                lambda: target.register_sources({'work_ref':self.lease['work_ref'],'refs':[self.origin]}),
                lambda: target.finish_step({'work_ref':self.lease['work_ref'],'step_id':step['step_id'],'result_refs':[]}),
                lambda: target.consume({'reservation_id': self.conn.execute("SELECT id FROM v5_tsk_reservation WHERE kind='model'").fetchone()[0], 'call_or_operation_id':call}),
                lambda: target.control({'key':self.key(),'work_ref':self.lease['work_ref'],'command':{'kind':'complete','verification_ref':{'kind':'verification','id':'not-authority'}}})):
                with self.subTest(target=target, operation=operation):
                    before=self.snapshot(); result=operation(); self.assertFalse(result.ok, result.to_json()); self.assertIn(result.error.code, ('unavailable','conflict','denied')); self.assertEqual(self.snapshot(),before)
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            result=self.t.authorize_artifact_save(self.conn, {'work_ref':self.lease['work_ref'],'step_id':step['step_id'],'action':step['action']})
            self.assertFalse(result.ok)
            self.assertFalse(self.t.verification_context(self.conn, {'work_ref':self.lease['work_ref']}, purpose='save').ok)
        finally: self.conn.execute('ROLLBACK')

    def test_two_connection_latest_pause_cancel_and_source_stop_win(self):
        for intent in ('pause','cancel','source_stop'):
            with self.subTest(intent=intent):
                self.setUp(); call=self.call(None); self.reopen(); _, controller, memory, _, _ = self.connect()
                if intent == 'source_stop': self.value(memory.stop_reference({'key':self.key(),'source_ref':self.origin},session_id='control'))
                else: self.value(controller.control({'key':self.key(),'work_ref':self.work()['work_ref'],'command':intent}))
                epoch = self.work()['work_ref']['epoch']; out=self.settled(self.recover(), [call])
                self.assertEqual(out['state'], 'cancelled' if intent=='cancel' else 'paused' if intent=='pause' else 'queued')
                self.assertEqual(out['work_ref']['epoch'], epoch if intent=='cancel' else epoch+1)

    def test_change_then_pause_or_cancel_latest_revision_settles_old_lease(self):
        for intent in ('pause','cancel'):
            with self.subTest(intent=intent):
                self.setUp(); call=self.call(None); correction=self.record('correction'); self.reopen(); _, controller, _, _, _=self.connect()
                changed=self.value(controller.control({'key':self.key(),'work_ref':self.work()['work_ref'],
                    'command':{'kind':'change','origin_record_ref':correction,'brief':self.draft}}))
                self.value(controller.control({'key':self.key(),'work_ref':changed['work_ref'],'command':intent}))
                out=self.settled(self.recover(), [call]); self.assertEqual(out['work_ref']['revision'],2)
                self.assertEqual(out['state'],'paused' if intent=='pause' else 'cancelled')
                self.assertEqual(self.work(1)['state'],'superseded')

    def test_overflow_and_prewrite_mint_transaction_loss_refuse(self):
        self.call(None); self.reopen(); self.conn.execute('UPDATE v5_intake_work SET epoch=?',(MAX,))
        before=self.snapshot(); self.error(self.recover(),'unavailable'); self.assertEqual(self.snapshot(),before)
        self.conn.execute('UPDATE v5_intake_work SET epoch=?',(self.lease['work_ref']['epoch'],))
        for operation in ('COMMIT','ROLLBACK','COMMIT_BEGIN','ROLLBACK_BEGIN','WRITE'):
            with self.subTest(operation=operation):
                original=self.t._id_factory
                def mint(prefix):
                    if operation=='WRITE': self.conn.execute('UPDATE v5_tsk_usage SET used=used+1')
                    else:
                        self.conn.execute(operation.split('_')[0])
                        if operation.endswith('BEGIN'): self.conn.execute('BEGIN IMMEDIATE')
                    return 'minted-id'
                before=self.snapshot()
                self.t._id_factory=mint
                try: self.error(self.recover(),'unavailable')
                finally: self.t._id_factory=original
                self.assertEqual(self.snapshot(),before); self.assertFalse(self.conn.in_transaction)

    def test_owned_write_failure_and_baseexception_roll_back_entire_settlement(self):
        for exception in (RuntimeError, KeyboardInterrupt):
            with self.subTest(exception=exception):
                self.setUp(); call=self.call(None); self.reopen(); before=self.snapshot()
                self.conn.fault=exception; self.conn.writes_until_fault=1
                if exception is KeyboardInterrupt:
                    with self.assertRaises(KeyboardInterrupt): self.recover()
                else: self.error(self.recover(),'unavailable')
                self.assertEqual(self.snapshot(),before); self.assertFalse(self.conn.in_transaction)
                self.settled(self.recover(), [call])

    def test_finished_artifact_history_and_old_verification_cannot_complete_new_epoch(self):
        _, step=self.stage('compose'); work=self.lease['work_ref']
        saved=self.value(self.art.save({'key':dumps(['C08.save',work,step['step_id']]),'work_ref':work,'step_id':step['step_id'],
            **{k:v for k,v in step['action'].items() if k!='kind'}}))
        finished=self.value(self.t.finish_step({'work_ref':work,'step_id':step['step_id'],'result_refs':[saved['artifact_ref']]}))
        receipt=self.value(self.ver.verify({'key':dumps(['C09.verify',work,[saved['artifact_ref']]]),'work_ref':work,'artifact_refs':[saved['artifact_ref']]}))
        self.reopen(); self.settled(self.recover()); self.value(self.t.finish_startup()); self.lease=self.value(self.t.claim({'runner_id':self.guard.runner_id}))
        self.assertEqual(self.work()['current_artifact_refs'],[saved['artifact_ref']])
        before=self.snapshot(); self.error(self.t.control({'key':self.key(),'work_ref':self.lease['work_ref'],
            'command':{'kind':'complete','verification_ref':receipt['verification_ref']}}),'stale')
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(loads(self.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?',(step['step_id'],)).fetchone()[0]),finished)

    def test_closed_guard_blocks_same_owner_execution_and_consume_replay(self):
        call=self.call(); reservation=self.conn.execute("SELECT reservation FROM v5_tsk_call WHERE id=?",(call,)).fetchone()[0]
        request={'reservation_id':reservation,'call_or_operation_id':call}
        self.value(self.t.consume(request)); self.guard.close(); before=self.snapshot()
        for invoke in (lambda:self.t.consume(request), lambda:self.t.end_call({'call_id':call,'outcome':'returned'}),
                       lambda:self.t.begin_step({'key':self.key(),'work_ref':self.lease['work_ref'],'action':{'kind':'report','summary':'closed'}})):
            with self.subTest(invoke=invoke):
                self.assertFalse(invoke().ok); self.assertEqual(self.snapshot(),before)

    def test_stored_verify_abandons_but_operate_tail_holds(self):
        # These closed C12 Action shapes cannot be dispatched by today's bounded
        # begin_step; persisted-tail classification is nevertheless frozen. This
        # constructs stored input, never executes EXE or pretends a call occurred.
        for kind in ('verify','operate'):
            with self.subTest(kind=kind):
                self.setUp(); _,step=self.stage()
                action={'kind':'verify','artifact_refs':[]} if kind=='verify' else {
                    'kind':'operate','capability':'github.issue.read','arguments':{},'source_refs':[self.origin]}
                step['action']=action; self.conn.execute('UPDATE v5_tsk_step SET wire=?',(dumps(step),))
                self.reopen(); before=self.snapshot()
                if kind=='verify':
                    self.settled(self.recover())
                    self.assertEqual(loads(self.conn.execute('SELECT wire FROM v5_tsk_step').fetchone()[0])['status'],'abandoned')
                else:
                    held=self.value(self.recover()); self.assertEqual((held['disposition'],held['reason']),('held','external_tail'))
                    self.assertEqual(held['step_id'],step['step_id']); self.assertEqual(self.snapshot(),before)
                    self.error(self.t.finish_startup(),'conflict')

    def test_unmanaged_active_lease_never_becomes_qualified_by_registration(self):
        self.conn.close(); self.guard.close()
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.path=Path(temp.name)/'unmanaged.sqlite'
        self.conn,self.t,self.mem,self.art,self.ver=self.connect()
        origin=self.record('unmanaged origin')
        created=self.value(self.t.create({'key':self.key(),'session_id':'session','origin_record_ref':origin,'brief':self.draft},request_scope=self.grant))
        self.goal=created['work_ref']['goal_id']; self.lease=self.value(self.t.claim({'runner_id':'unmanaged'})); self.conn.close()
        self.guard=self.Host.open(self.path); self.addCleanup(self.close_guard,self.guard)
        self.conn,self.t,self.mem,self.art,self.ver=self.connect(self.guard)
        self.value(self.t.register_host()); before=self.snapshot()
        self.error(self.recover(),'unavailable'); self.assertEqual(self.snapshot(),before); self.error(self.t.finish_startup(),'conflict')

    def test_optional_stop_answer_link_survives_cleanup_without_source_regate(self):
        _,step=self.stage('ask'); req={'key':self.key(),'work_ref':self.lease['work_ref'],'step_id':step['step_id'],
            **{k:v for k,v in step['action'].items() if k!='kind'}}
        question=self.value(self.t.ask(req)); answer=self.record('answer')
        self.value(self.t.control({'key':self.key(),'work_ref':self.work()['work_ref'],'command':{
            'kind':'answer','question_id':question['question_id'],'answer_record_ref':answer}}))
        self.lease=self.value(self.t.claim({'runner_id':self.guard.runner_id})); links=copy.deepcopy(self.lease['pending_inputs'])
        call=self.call(None); self.reopen(); _,_,mem,_,_=self.connect()
        self.value(mem.stop_reference({'key':self.key(),'source_ref':answer},session_id='control'))
        self.settled(self.recover(), [call]); self.value(self.t.finish_startup()); next_claim=self.value(self.t.claim({'runner_id':self.guard.runner_id}))
        self.assertEqual(next_claim['pending_inputs'],links)

    def test_registration_after_commit_mark_reply_loss_reconstructs_snapshot(self):
        self.conn.close(); self.guard.close(); self.guard=self.Host.open(self.path); self.addCleanup(self.close_guard,self.guard)
        self.conn,self.t,self.mem,self.art,self.ver=self.connect(self.guard)
        original=self.Host.mark_registered; seen=[]
        def lose(guard,*args,**kwargs):
            seen.append(True); raise RuntimeError('private reply loss after registration commit')
        with patch.object(self.Host,'mark_registered',lose): self.error(self.t.register_host(),'unavailable')
        self.assertTrue(seen); before=self.snapshot()
        receipt=self.value(self.t.register_host()); self.assertEqual(receipt['orphan_lease_id'],self.lease['lease_id'])
        self.assertEqual(self.snapshot(),before); self.assertEqual(self.guard.phase,'startup')


if __name__ == '__main__': unittest.main()
