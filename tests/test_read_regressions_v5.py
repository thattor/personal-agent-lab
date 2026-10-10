"""READ01 contractual gaps found by the integrator after frozen tests passed."""
from pathlib import Path
import sys
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import unittest
import test_read_consumer_v5 as fixed


class ReadRegressionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixed.ReadConsumerTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_completed_history_notice_is_a_visible_item_even_without_work_ref(self):
        notices = [fixed.event('notice1', kind='progress', text=fixed.NOTICE, refs=[fixed.R]),
                   fixed.event('notice2', kind='progress', text=fixed.NOTICE, refs=[fixed.R], work=None)]
        out = self.fixture.inspect([self.fixture.page(notices, 'notice2'), self.fixture.page([], 'notice2')])
        self.assertEqual([item['event'] for item in out['items']], notices)
        self.assertEqual(out['items'][1]['work']['error']['code'], 'unavailable')
        self.assertEqual(out['items'][0]['reads'][0]['ref'], fixed.R)

    def test_unknown_and_malformed_refs_remain_visible_per_ref_failures(self):
        refs = [fixed.A, {'kind': 'alien', 'id': 'x'}, {'kind': 'artifact'}, fixed.V]
        out = self.fixture.inspect([self.fixture.page([fixed.event('result', refs=refs)], 'result'),
                                    self.fixture.page([], 'result')])
        reads = out['items'][0]['reads']
        self.assertEqual([read['ref'] for read in reads], refs)
        self.assertTrue(reads[0]['result']['ok'])
        self.assertTrue(reads[3]['result']['ok'])
        for index in (1, 2):
            self.assertEqual(reads[index]['result']['error']['code'], 'invalid_input')
            self.assertIsNone(reads[index]['validity'])
        self.assertIn('invalid_input', self.fixture.render(out))

    def test_renderer_preserves_each_owner_timestamp_meaning(self):
        out = self.fixture.inspect([self.fixture.page([fixed.event('result', refs=[fixed.R, fixed.A, fixed.V])], 'result'),
                                    self.fixture.page([], 'result')])
        text = self.fixture.render(out).lower()
        record = text.split('ref record:r')[1].split('ref artifact:a')[0]
        artifact = text.split('ref artifact:a')[1].split('ref verification:v')[0]
        verification = text.split('ref verification:v')[1]
        for section in (record, artifact):
            self.assertIn('stored', section)
            self.assertNotIn('time of this read', section)
        self.assertIn('read at', verification)
        self.assertIn('not creation time', verification)

    def test_real_c11_optional_fields_are_accepted_and_extras_rejected(self):
        body = fixed.c11(fixed.R)
        del body['work_ref']
        owner = self.fixture.owners[0]
        for value in (body, {**body, 'version': 'saved-v1'}, {**body, 'work_ref': None}):
            owner.response = fixed.Result.success(value)
            result = self.fixture.reader.read({'ref': fixed.R}, purpose='user_view')
            self.assertTrue(result.ok, result.to_json())
            self.assertEqual(result.value.to_json(), value)
        for value in ({**body, 'version': 5}, {**body, 'extra': 1}):
            owner.response = fixed.Result.success(value)
            self.fixture.error(self.fixture.reader.read({'ref': fixed.R}, purpose='user_view'), 'unavailable')

    def test_malformed_notice_refs_are_visible_without_correlating_false_cause(self):
        self.fixture.owners[2].usable = False
        notice = fixed.event('notice', kind='progress', text=fixed.NOTICE,
                             refs=['raw', 5, None, {'kind': 'record'}])
        out = self.fixture.inspect([self.fixture.page([fixed.event('result'), notice], 'notice'),
                                    self.fixture.page([], 'notice')])
        self.assertEqual(len(out['items']), 2)
        self.assertEqual(out['items'][0]['reads'][1]['validity'], 'not current')
        for read in out['items'][1]['reads']:
            self.assertEqual(read['result']['error']['code'], 'invalid_input')
        self.assertIn('invalid_input', self.fixture.render(out))
        self.assertIn('notice', self.fixture.render(out).lower())

    def test_resumed_window_never_invents_an_unseen_source_stop_notice(self):
        self.fixture.owners[2].usable = False
        events = fixed.StrictEvents(self, [self.fixture.page([fixed.event('result')], 'result'),
                                          self.fixture.page([], 'result')], initial_cursor='old-notice')
        result = self.fixture.inspect_session({'session_id': 'session', 'after_event_id': 'old-notice'},
            events=events, tasks=self.fixture.tasks, reader=self.fixture.reader)
        self.assertTrue(result.ok, result.to_json())
        self.assertEqual(result.value.to_json()['items'][0]['reads'][1]['validity'], 'not current')


if __name__ == '__main__':
    unittest.main()
