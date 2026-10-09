"""READ01 actual owner readback; all databases are temporary fixture files."""
import copy
import hashlib
import importlib
import unittest

from pal.contracts_v5 import dumps, loads
from pal.events_v5 import EventReader
from pal.mock_runner_v5 import MockRunner
from pal.verification_v5 import VerificationStore
import test_completion_connection_v5 as completion
import test_mock_completion_connection_v5 as flow


class ReadConnectionTests(unittest.TestCase):
    def setUp(self):
        self.f = completion.CompletionConnectionTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.HostReader = importlib.import_module('pal.host_read_v5').HostReader
        consumer = importlib.import_module('pal.read_consumer_v5')
        self.inspect_session, self.render = consumer.inspect_session, consumer.render

    def reader(self, owner=None):
        return self.HostReader(self.f.memory, self.f.artifacts, owner or self.f.verifications)

    def inspect(self, *, request=None, max_pages=64, reader=None, page_size=1):
        return self.f.value(self.inspect_session(request or {'session_id': 'draft-session'},
            events=EventReader(self.f.conn, page_size=page_size), tasks=self.f.tasks,
            reader=reader or self.reader(), max_pages=max_pages))

    def reads(self, inspection, kind):
        return [read for item in inspection['items'] for read in item['reads']
                if read['ref']['kind'] == kind]

    def test_three_real_owners_return_matching_utf8_hashes_without_writes(self):
        verification, request = self.f.ready()
        self.f.value(self.f.tasks.control(request))
        snapshot, changes = self.f.snapshot(), self.f.conn.total_changes
        for ref in (self.f.refs[0], self.f.saved_refs[0], verification['verification_ref']):
            with self.subTest(kind=ref['kind']):
                body = self.f.value(self.reader().read({'ref': ref}, purpose='user_view'))
                self.assertEqual(body['ref'], ref)
                self.assertEqual(body['hash'], hashlib.sha256(body['content'].encode('utf-8')).hexdigest())
                self.assertTrue(body['usable'])
        self.assertEqual((self.f.snapshot(), self.f.conn.total_changes), (snapshot, changes))

    def test_read_clock_changes_only_observation_time_and_public_artifact_binding_is_exact(self):
        verification, _ = self.f.ready()
        clock = ['2026-10-09T10:00:00+00:00']
        owner = VerificationStore(self.f.conn, context=self.f.tasks.verification_context,
            artifact_inspect=self.f.artifacts.inspect, source_gate=self.f.memory.source_gate,
            clock=lambda: clock[0])
        reader = self.reader(owner)
        first = self.f.value(reader.read({'ref': verification['verification_ref']}, purpose='user_view'))
        clock[0] = '2026-10-09T10:00:01Z'
        second = self.f.value(reader.read({'ref': verification['verification_ref']}, purpose='user_view'))
        self.assertNotEqual(first['observed_at'], second['observed_at'])
        self.assertEqual((first['content'], first['hash']), (second['content'], second['hash']))
        projection = loads(first['content'])
        self.assertEqual(first['content'], dumps(projection))
        self.assertEqual(set(projection), {'work_ref', 'conditions', 'artifact_refs', 'artifacts', 'source_refs', 'checks'})
        self.assertEqual(projection['conditions'], self.f.current()['brief']['conditions'])
        artifact = self.f.value(reader.read({'ref': self.f.saved_refs[0]}, purpose='user_view'))
        self.assertEqual(projection['artifacts'], [{'artifact_ref': self.f.saved_refs[0],
            'hash': artifact['hash'], 'bytes': len(artifact['content'].encode('utf-8'))}])
        self.assertNotIn('key', projection)

    def test_real_paginated_result_readback_preserves_multiartifact_order_and_cursor(self):
        _, _ = self.f.ready()
        self.f.compose()
        verification = self.f.verify('whole-set')
        self.f.value(self.f.tasks.control(self.f.complete_request(verification)))
        snapshot, changes = self.f.snapshot(), self.f.conn.total_changes
        first = self.inspect(max_pages=1)
        self.assertTrue(first['truncated'])
        self.assertEqual(first['items'], [])
        rest = self.inspect(request={'session_id': 'draft-session', 'after_event_id': first['next_cursor']})
        self.assertFalse(rest['truncated'])
        self.assertEqual([read['ref'] for read in self.reads(rest, 'artifact')], self.f.saved_refs)
        verification_read = self.reads(rest, 'verification')[0]
        self.assertEqual(verification_read['validity'], 'current')
        self.assertEqual(rest['items'][0]['work']['value']['state'], 'completed')
        rendered = self.render(rest).lower()
        for label in ('mock', 'structural', 'read at', 'completed'):
            self.assertIn(label, rendered)
        self.assertIn('下書き', rendered)
        self.assertEqual((self.f.snapshot(), self.f.conn.total_changes), (snapshot, changes))

    def test_completed_source_stop_keeps_body_hash_and_state_but_changes_readback_usability(self):
        _, request = self.f.ready()
        self.f.value(self.f.tasks.control(request))
        before = self.inspect()
        original = self.reads(before, 'verification')[0]['result']['value']
        self.f.value(self.f.stop(self.f.memory, self.f.refs[1]))
        snapshot, changes = self.f.snapshot(), self.f.conn.total_changes
        after = self.inspect()
        current = self.reads(after, 'verification')[0]
        self.assertEqual(current['validity'], 'source stopped')
        body = current['result']['value']
        self.assertEqual((body['content'], body['hash']), (original['content'], original['hash']))
        self.assertFalse(body['usable'])
        self.assertTrue(all(item['work']['value']['state'] == 'completed' for item in after['items']))
        self.assertTrue(all(not read['result']['value']['usable'] for read in self.reads(after, 'artifact')))
        self.assertEqual((self.f.snapshot(), self.f.conn.total_changes), (snapshot, changes))

    def test_epoch_only_nonmet_history_stays_readable_without_claiming_source_stop(self):
        verification, _ = self.f.ready(all_kinds=True)
        request = {'ref': verification['verification_ref']}
        before = self.f.value(self.reader().read(request, purpose='user_view'))
        self.f.value(self.f.tasks.release({'lease_id': self.f.lease['lease_id'], 'work_ref': self.f.work,
                                          'outcome': 'yield', 'reason': 'bounded mock slice'}))
        self.f.value(self.f.tasks.claim({'runner_id': 'new-epoch'}))
        after = self.f.value(self.reader().read(request, purpose='user_view'))
        self.assertEqual((before['content'], before['hash']), (after['content'], after['hash']))
        self.assertFalse(after['usable'])
        self.assertEqual([check['status'] for check in loads(after['content'])['checks']], ['met', 'unknown', 'unknown'])
        self.assertFalse(any(event['text'] == completion.NOTICE for event in self.f.events()))
        for purpose in ('model_context', 'verification'):
            self.f.error(self.reader().read(request, purpose=purpose), 'denied')

    def test_two_completed_works_in_one_session_keep_separate_state_and_refs(self):
        _, request = self.f.ready()
        first_work = copy.deepcopy(self.f.work)
        self.f.value(self.f.tasks.control(request))
        second = self.f.create_next(session='draft-session')
        runner = MockRunner(self.f.tasks, self.f.memory, artifacts=self.f.artifacts,
                            verifications=self.f.verifications)
        def expert(context, **diagnostics):
            return {'kind': 'compose', 'media_type': 'text/plain', 'content': '別の仕事の下書き',
                    'source_refs': [body['ref'] for body in context['context']]}
        self.assertEqual(self.f.value(runner.run_once(expert))['status'], 'completed')
        self.f.work = self.f.value(self.f.tasks.get_work({'goal_id': second['goal_id'],
                                                        'revision': second['revision']}))['work_ref']
        result = self.inspect()
        self.assertEqual([item['event']['work_ref'] for item in result['items']], [first_work, self.f.work])
        self.assertEqual([item['work']['value']['work_ref'] for item in result['items']], [first_work, self.f.work])
        self.assertEqual(len(self.reads(result, 'artifact')), 2)
        self.assertEqual(len(self.reads(result, 'verification')), 2)

    def test_missing_actual_artifact_is_visible_and_does_not_drop_the_saved_result(self):
        _, request = self.f.ready()
        self.f.value(self.f.tasks.control(request))
        self.f.conn.execute('DELETE FROM v5_art_body')
        before = self.f.snapshot()
        result = self.inspect()
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['work']['value']['state'], 'completed')
        reads = result['items'][0]['reads']
        self.assertEqual(len(reads), 2)
        self.assertTrue(all(not read['result']['ok'] for read in reads))
        rendered = self.render(result)
        for read in reads:
            self.assertIn(read['result']['error']['code'], rendered)
        self.assertEqual(before, self.f.snapshot())

    def test_result_is_discoverable_after_committed_but_lost_runner_response(self):
        consumer = flow.MockCompletionConnectionTests()
        consumer.setUp()
        self.addCleanup(consumer.doCleanups)
        runner = consumer.runner(control_mode='lost_always')
        consumer.f.error(runner.run_once(consumer.expert), 'unavailable')
        self.f = consumer.f
        result = self.inspect()
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['work']['value']['state'], 'completed')
        self.assertEqual(self.reads(result, 'verification')[0]['validity'], 'current')
        self.assertEqual(len(consumer.inputs), 1)
        self.assertEqual(consumer.tasks.releases, [])

    def test_read_snapshot_orders_a_stop_attempt_from_another_connection(self):
        verification, request = self.f.ready()
        self.f.value(self.f.tasks.control(request))
        _, _, other_memory, _, _ = self.f.connect()
        attempts = []
        def clock():
            if not attempts:
                attempts.append(self.f.stop(other_memory, self.f.refs[1]))
            return '2026-10-09T10:00:00+00:00'
        owner = VerificationStore(self.f.conn, context=self.f.tasks.verification_context,
            artifact_inspect=self.f.artifacts.inspect, source_gate=self.f.memory.source_gate, clock=clock)
        reader = self.reader(owner)
        first = self.f.value(reader.read({'ref': verification['verification_ref']}, purpose='user_view'))
        self.assertTrue(first['usable'])
        self.assertEqual(len(attempts), 1)
        self.f.error(attempts[0], 'unavailable')
        self.f.value(self.f.stop(other_memory, self.f.refs[1]))
        after = self.f.value(reader.read({'ref': verification['verification_ref']}, purpose='user_view'))
        self.assertFalse(after['usable'])
        self.assertEqual((first['content'], first['hash']), (after['content'], after['hash']))


if __name__ == '__main__':
    unittest.main()
