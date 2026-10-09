"""Real owned child death at saved-tail barriers; no provider/semantic proof."""
from pathlib import Path
import contextlib
import hashlib
import json
import select
import signal
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_mock_recovery_connection_v5 as fixture
from pal.artifacts_v5 import ArtifactStore, artifact_save_key
from pal.contracts_v5 import Limits, dumps, loads
from pal.memory_v5 import MemoryStore
from pal.mock_host_v5 import MockHostSession
from pal.mock_runner_v5 import MockInvoker
from pal.sanitize import sanitize
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore

value = fixture.value


def _child(path, saved, prior):
    guard = MockHostSession.open(path)
    owners = fixture.Owners(path, guard)
    owners.startup()
    _, origin = owners.create()
    lease = value(owners.tasks.claim({'runner_id': guard.runner_id}))
    old_ver = None
    for index in range(2 if prior else 1):
        action = {'kind': 'compose', 'content': '元の本文😀\n' + str(index),
                  'media_type': 'text/plain', 'source_refs': [origin]}
        reservation = value(owners.tasks.reserve_budget({'key': 'model-' + str(index),
            'work_ref': lease['work_ref'], 'kind': 'model', 'role': 'expert'}))
        call = {'call_id': dumps(['C15.call', lease['lease_id'], index]),
            'lease_id': lease['lease_id'], 'work_ref': lease['work_ref'],
            'reservation_id': reservation['reservation_id'], 'source_refs': [origin]}
        value(MockInvoker().invoke(owners.tasks, call, lambda: action))
        step = value(owners.tasks.begin_step({'key': 'begin-' + str(index),
            'work_ref': lease['work_ref'], 'action': action}))
        key = artifact_save_key(lease['work_ref'], step['step_id'])
        receipt = None
        if saved or (prior and index == 0):
            receipt = value(owners.artifacts.save({'key': key, 'work_ref': lease['work_ref'],
                'step_id': step['step_id'], **{k:v for k,v in action.items() if k != 'kind'}}))
        if prior and index == 0:
            value(owners.tasks.finish_step({'work_ref': lease['work_ref'],
                'step_id': step['step_id'], 'result_refs': [receipt['artifact_ref']]}))
            old_ver = value(owners.verifications.verify({'key': 'old-verify',
                'work_ref': lease['work_ref'], 'artifact_refs': [receipt['artifact_ref']]}))
    print(json.dumps({'lease_id': lease['lease_id'], 'work_ref': lease['work_ref'],
        'step': step, 'key': key, 'receipt': receipt, 'origin': origin,
        'old_ver': old_ver}, ensure_ascii=True), flush=True)
    sys.stdin.buffer.read(1)
    raise AssertionError('barrier must end by parent SIGKILL, not return')


class RecoveryOwners(fixture.Owners):
    def __init__(self, path, guard=None):
        self.conn = sqlite3.connect(path, isolation_level=None, timeout=0)
        self.guard = guard
        self.memory = self.artifacts = self.verifications = None
        self.grant = fixture.Grant((), ('demo',), Limits(0, 8, 8))
        self.lookups = []
        def lookup(conn, request):
            self.lookups.append(request)
            return self.artifacts.lookup_saved(conn, request)
        self.tasks = TaskStore(self.conn, host_limits=Limits(0, 30, 30),
            startup_guard=guard, host_grant=self.grant, expert_id='mock-expert',
            source_gate=lambda c,r:self.memory.source_gate(c,r),
            artifact_inspect=lambda c,r:self.artifacts.inspect(c,r),
            verification_inspect=lambda c,r:self.verifications.inspect(c,r),
            artifact_lookup=lookup)
        self.memory = MemoryStore(self.conn, sanitize_text=sanitize,
            append_event=self.tasks.append_event, invalidate_by_refs=self.tasks.invalidate_by_refs)
        self.artifacts = ArtifactStore(self.conn, authorize_save=self.tasks.authorize_artifact_save,
                                       source_gate=self.memory.source_gate)
        self.verifications = VerificationStore(self.conn, context=self.tasks.verification_context,
            artifact_inspect=self.artifacts.inspect, source_gate=self.memory.source_gate)


class SavedTailConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pal-real-saved-tail-')
        self.addCleanup(self.temp.cleanup)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.path = Path(self.temp.name) / 'work.sqlite'

    def crash(self, saved=True, prior=False):
        code = ('import sys;sys.path.insert(0,sys.argv[2]);'
                'from test_saved_tail_connection_v5 import _child;'
                '_child(sys.argv[1],sys.argv[3]=="yes",sys.argv[4]=="yes")')
        proc = subprocess.Popen([sys.executable, '-E', '-s', '-B', '-c', code,
            str(self.path), str(ROOT / 'tests'), 'yes' if saved else 'no', 'yes' if prior else 'no'],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def cleanup():
            if proc.poll() is None: proc.kill()
            proc.wait(timeout=5)
            for stream in (proc.stdin, proc.stdout, proc.stderr): stream.close()
        self.addCleanup(cleanup)
        self.assertTrue(select.select([proc.stdout], [], [], 10)[0], 'child barrier timed out')
        line = proc.stdout.readline()
        if not line:
            self.fail('child failed before durable barrier: ' + proc.stderr.read().decode()[-1500:])
        old = json.loads(line)
        self.assertIsNone(proc.poll())
        proc.kill()
        self.assertEqual(proc.wait(timeout=5), -signal.SIGKILL)
        return old

    def open(self, guard=True):
        host = MockHostSession.open(self.path) if guard else None
        if host: self.stack.callback(lambda: host.close() if host.phase != 'closed' else None)
        owners = RecoveryOwners(self.path, host)
        self.stack.callback(owners.close)
        return owners

    def recover(self, old):
        owners = self.open()
        registration = value(owners.tasks.register_host())
        self.assertEqual(registration['orphan_lease_id'], old['lease_id'])
        result = value(owners.tasks.recover({'key': 'recover', 'lease_id': old['lease_id']}))
        self.assertEqual(result['disposition'], 'settled')
        return owners, result

    def evidence(self, owners):
        return {'art': tuple(line for line in owners.conn.iterdump() if line.startswith('INSERT INTO "v5_art_')),
                'calls': owners.conn.execute('SELECT * FROM v5_tsk_call ORDER BY id').fetchall(),
                'usage': owners.conn.execute('SELECT * FROM v5_tsk_usage ORDER BY rowid').fetchall(),
                'host': owners.conn.execute('SELECT * FROM v5_tsk_host ORDER BY rowid').fetchall()}

    def current(self, owners, old):
        return value(owners.tasks.get_work({'goal_id': old['work_ref']['goal_id'],
                                          'revision': old['work_ref']['revision']}))

    def test_saved_commit_crash_adopts_original_and_replays_without_charge(self):
        old = self.crash()
        before = self.open(guard=False)
        baseline = self.evidence(before)
        owners, result = self.recover(old)
        self.assertEqual(self.evidence(owners), baseline)
        self.assertEqual(result['work_ref']['epoch'], old['work_ref']['epoch'] + 1)
        current = self.current(owners, old)
        self.assertEqual(current['current_artifact_refs'], [old['receipt']['artifact_ref']])
        step = loads(owners.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?',
                                        (old['step']['step_id'],)).fetchone()[0])
        self.assertEqual(step, {**old['step'], 'status': 'finished',
                                'result_refs': [old['receipt']['artifact_ref']]})
        self.assertEqual(value(owners.artifacts.get_by_key({'key':old['key']})), old['receipt'])
        dump = list(owners.conn.iterdump())
        self.assertEqual(value(owners.tasks.recover({'key':'recover','lease_id':old['lease_id']})), result)
        self.assertEqual(list(owners.conn.iterdump()), dump)
        value(owners.tasks.finish_startup())
        body = value(owners.artifacts.read({'ref':old['receipt']['artifact_ref']}, purpose='user_view'))
        self.assertEqual(body['content'], old['step']['action']['content'])
        self.assertEqual(body['work_ref'], old['work_ref'])
        self.assertEqual(body['hash'], hashlib.sha256(body['content'].encode()).hexdigest())
        reader = fixture.HostReader(memory=owners.memory, artifacts=owners.artifacts,
                                    verifications=owners.verifications)
        displayed = fixture.inspect_session({'session_id':'restart-demo'},
            events=fixture.EventReader(owners.conn), tasks=owners.tasks, reader=reader)
        self.assertTrue(displayed.ok)
        self.assertIn(old['receipt']['artifact_ref']['id'], dumps(displayed))

    def test_fresh_verification_accepts_old_art_epoch_old_ver_stays_invalidated(self):
        old = self.crash(prior=True)
        owners, result = self.recover(old)
        value(owners.tasks.finish_startup())
        status = value(owners.verifications.get_verification(
            {'verification_ref':old['old_ver']['verification_ref']}))
        self.assertEqual(status['status'], 'invalidated')
        history = value(owners.verifications.read({'ref':old['old_ver']['verification_ref']}, purpose='user_view'))
        self.assertFalse(history['usable'])
        self.assertEqual(value(owners.verifications.get_by_key({'key':'old-verify'})), old['old_ver'])
        refs = self.current(owners, old)['current_artifact_refs']
        self.assertEqual(len(refs), 2)
        lease = value(owners.tasks.claim({'runner_id':owners.guard.runner_id}))
        fresh = value(owners.verifications.verify({'key':'fresh-verify',
            'work_ref':lease['work_ref'], 'artifact_refs':refs}))
        self.assertNotEqual(fresh['verification_ref'], old['old_ver']['verification_ref'])
        rejected = owners.tasks.control({'key':'old-complete','work_ref':lease['work_ref'],
            'command':{'kind':'complete','verification_ref':old['old_ver']['verification_ref']}})
        self.assertFalse(rejected.ok)
        self.assertEqual(rejected.error.code.value, 'stale')
        value(owners.tasks.control({'key':'fresh-complete','work_ref':lease['work_ref'],
            'command':{'kind':'complete','verification_ref':fresh['verification_ref']}}))

    def test_before_save_crash_abandons_then_one_new_bounded_call(self):
        old = self.crash(saved=False)
        owners, result = self.recover(old)
        self.assertEqual(self.current(owners, old)['current_artifact_refs'], [])
        step = loads(owners.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?',
                                        (old['step']['step_id'],)).fetchone()[0])
        self.assertEqual(step['status'], 'abandoned')
        self.assertEqual(owners.artifacts.get_by_key({'key':old['key']}).error.code.value, 'not_found')
        value(owners.tasks.finish_startup())
        called=[]
        def fresh(context, **diagnostics):
            called.append(context['work_ref'])
            return {'kind':'compose','content':'fresh distinct draft','media_type':'text/plain',
                    'source_refs':[body['ref'] for body in context['context']]}
        answer = value(owners.runner().run_once(fresh))
        self.assertEqual((answer['status'],len(called)), ('completed',1))
        self.assertEqual(owners.conn.execute('SELECT count(*) FROM v5_art_body').fetchone()[0], 1)
        self.assertEqual(owners.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0], 2)

    def test_ordered_second_connection_latest_intents_never_adopt_saved_body(self):
        for intent in ('pause','change','cancel','source_stop'):
            with self.subTest(intent=intent):
                with tempfile.TemporaryDirectory(prefix='pal-tail-intent-') as directory:
                    self.path = Path(directory)/'work.sqlite'
                    old = self.crash()
                    controller = self.open(guard=False)
                    baseline = self.evidence(controller)
                    if intent == 'source_stop':
                        value(controller.memory.stop_reference({'key':'stop','source_ref':old['origin']}, session_id='control'))
                    else:
                        command = intent
                        if intent == 'change':
                            correction = value(controller.memory.append({'client_key':'correction',
                                'session_id':'restart-demo','role':'user','text':'new revision'}))['record_ref']
                            brief = {'purpose':'new draft','target':{'repository':'demo','issue_numbers':[],'files':[]},
                                'constraints':[],'context_refs':[],
                                'conditions':[{'description':'saved','check':'artifact_saved'}]}
                            command={'kind':'change','brief':brief,'origin_record_ref':correction}
                        value(controller.tasks.control({'key':'intent','work_ref':old['work_ref'],'command':command}))
                    owners, result = self.recover(old)
                    self.assertEqual(owners.lookups, [])
                    self.assertEqual(self.evidence(owners)['art'], baseline['art'])
                    self.assertEqual(result['state'], 'paused' if intent=='pause' else 'cancelled' if intent=='cancel' else 'queued')
                    step = loads(owners.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?',
                        (old['step']['step_id'],)).fetchone()[0])
                    self.assertEqual(step['status'],'abandoned')
                    work = value(owners.tasks.get_work({'goal_id':result['work_ref']['goal_id'],
                                                       'revision':result['work_ref']['revision']}))
                    self.assertEqual(work['current_artifact_refs'], [])
                    self.assertEqual(value(owners.artifacts.get_by_key({'key':old['key']})),old['receipt'])
                    owners.close(); controller.close()
