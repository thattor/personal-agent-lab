"""PRI03 saved native fixture recovery is visible, never C14 text authority.

Closing/reopening the real local guard is cooperative recovery, not SIGKILL or
provider cessation proof. Every body/readback comes from actual fresh owners.
"""
from pathlib import Path
import copy
import sqlite3
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_expert_fixtures_v5 import NativeFixture
from pal.artifacts_v5 import ArtifactStore, artifact_save_key
from pal.contracts_v5 import Limits
from pal.events_v5 import EventReader
from pal.host_read_v5 import HostReader
from pal.memory_v5 import MemoryStore
from pal.read_consumer_v5 import inspect_session, render
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore


class NativeRecoveryReadTests(unittest.TestCase):
    def fixture(self):
        n = NativeFixture(self)
        def connect(guard=None):
            f = n.f
            conn = sqlite3.connect(f.path, isolation_level=None, timeout=0)
            f.addCleanup(conn.close)
            mem = art = ver = None
            t = TaskStore(conn, startup_guard=guard, host_grant=f.grant, host_limits=Limits(0, 100, 100), expert_id='expert',
                source_gate=lambda c, refs: mem.source_gate(c, refs),
                artifact_inspect=lambda c, request: art.inspect(c, request),
                artifact_lookup=lambda c, request: art.lookup_saved(c, request),
                verification_inspect=lambda c, request: ver.inspect(c, request))
            mem = MemoryStore(conn, sanitize_text=lambda text: text, append_event=t.append_event, invalidate_by_refs=t.invalidate_by_refs)
            art = ArtifactStore(conn, authorize_save=t.authorize_artifact_save, source_gate=mem.source_gate)
            ver = VerificationStore(conn, context=t.verification_context, artifact_inspect=art.inspect, source_gate=mem.source_gate)
            return conn, t, mem, art, ver
        n.f.connect = connect
        return n

    def ok(self, result):
        self.assertTrue(result.ok, result.to_json())
        return result.value.to_json()

    def inspect(self, n):
        return self.ok(inspect_session({'session_id': 'session'}, events=EventReader(n.f.conn), tasks=n.t,
            reader=HostReader(n.f.mem, n.f.art, n.f.ver)))

    def test_native_saved_tail_original_owner_recovery_has_public_user_view_item(self):
        n = self.fixture()
        n.action = {'kind': 'compose', 'content': '合成 native 保存下書き', 'media_type': 'text/plain',
                    'source_refs': [n.f.origin, n.f.optional]}
        for result in (n.admit(), n.enter(), n.end()): self.ok(result)
        step = self.ok(n.begin())
        receipt = self.ok(n.f.art.save({'key': artifact_save_key(n.work, step['step_id']),
            'work_ref': n.work, 'step_id': step['step_id'], **{k: v for k, v in n.action.items() if k != 'kind'}}))
        original = self.ok(n.f.art.read({'ref': receipt['artifact_ref']}, purpose='user_view'))
        usage = copy.deepcopy(n.f.usage())
        n.f.reopen()
        recovered = self.ok(n.f.recover())
        self.assertEqual(recovered['disposition'], 'settled')
        self.assertEqual(n.f.usage(), usage)
        self.ok(n.t.finish_startup())
        current = n.f.work()
        self.assertEqual(current['current_artifact_refs'], [receipt['artifact_ref']])
        before = n.f.snapshot()
        inspection = self.inspect(n)
        items = inspection['items']
        selected = [item for item in items if item['event']['text'] == 'Saved draft recovered']
        self.assertEqual(len(selected), 1)
        item = selected[0]
        self.assertEqual(item['event']['kind'], 'state')
        self.assertEqual(item['event']['work_ref'], recovered['work_ref'])
        self.assertEqual(item['event']['refs'], [receipt['artifact_ref']])
        self.assertEqual(item['work']['value']['current_artifact_refs'], [receipt['artifact_ref']])
        self.assertEqual(len(item['reads']), 1)
        self.assertTrue(item['reads'][0]['result']['ok'])
        body = item['reads'][0]['result']['value']
        for name in ('ref', 'content', 'media_type', 'hash', 'work_ref', 'source_refs'):
            self.assertEqual(body[name], original[name])
        rendered = render(inspection)
        self.assertIn('Model provenance: unverified by this view', rendered)
        self.assertNotIn('Model: mock', rendered)
        self.assertNotIn('no real model call', rendered)
        self.assertNotIn('Model: native', rendered)
        self.assertNotIn('qualified real model', rendered)
        self.assertEqual(n.f.snapshot(), before)

    def test_same_text_ordinary_c14_event_cannot_invent_artifact_producer(self):
        n = self.fixture()
        nonexistent = {'kind': 'artifact', 'id': 'fixture-no-producer'}
        n.f.conn.execute('BEGIN IMMEDIATE')
        try:
            self.ok(n.t.append_event(n.f.conn, {'key': n.f.key(), 'session_id': 'session', 'work_ref': n.work,
                'kind': 'state', 'text': 'Saved draft recovered', 'refs': [nonexistent]}))
            n.f.conn.execute('COMMIT')
        except BaseException:
            if n.f.conn.in_transaction: n.f.conn.execute('ROLLBACK')
            raise
        before = n.f.snapshot()
        items = self.inspect(n)['items']
        selected = [item for item in items if item['event']['text'] == 'Saved draft recovered']
        self.assertEqual(len(selected), 1)
        item = selected[0]
        self.assertEqual(item['work']['value']['current_artifact_refs'], [])
        self.assertEqual(item['work']['value']['state'], 'running')
        self.assertFalse(item['reads'][0]['result']['ok'])
        self.assertEqual(item['reads'][0]['result']['error']['code'], 'not_found')
        self.assertEqual(n.f.snapshot(), before)
        self.assertEqual(n.f.work()['current_artifact_refs'], [])


if __name__ == '__main__':
    unittest.main()
