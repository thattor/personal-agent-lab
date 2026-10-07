import tempfile
import unittest
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pal.controls import parse_control
from pal.store import Store, Conflict


class TargetSelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = Store(Path(temp.name) / 'state.db')

    def draft(self, name):
        return self.store.ingress(name, name + ' draft', 'draft')

    def request(self, key, text):
        return self.store.ingress(key, text, 'control', natural_control=parse_control(text))

    def choose(self, key, question, target):
        return self.store.ingress(key, 'Select work target', 'control', control={
            'action': 'select', 'selection_id': question['selection_id'],
            'source_key': question['source_key'], 'target_id': target})

    def test_unique_and_no_match_never_fall_back(self):
        goal = self.draft('Birch')['goal']
        result = self.request('missing', 'Cedarの下書きを止めて')
        self.assertEqual(result['control_status'], 'no_target')
        self.assertEqual(self.store.get_goal(goal['id'])['state'], 'queued')
        result = self.request('unique', 'その下書きを止めて')
        self.assertEqual(result['goal']['state'], 'cancelled')
        self.assertIsNotNone(self.store.stored_reply('unique'))

    def test_frozen_nine_case_mixed_state_matrix(self):
        cases = json.loads((Path(__file__).parent / 'fixtures' /
                            'stable1_target_matrix_v1.json').read_text())['cases']
        for case in cases:
            with self.subTest(case=case['id']):
                self.setUp()
                goals = []
                for index, (name, state) in sorted(enumerate(case['goals']), key=lambda item: item[1][1] == 'queued'):
                    result = self.store.ingress('seed-' + str(index), name + ' draft', 'draft')
                    goal = result['goal']
                    goals.append(goal['id'])
                    if state == 'cancelled':
                        self.store.control('cancel-' + str(index), goal['id'], 'cancel')
                    elif state in ('running', 'waiting_input', 'completed'):
                        attempt = self.store.claim()
                        self.assertEqual(attempt['goal_id'], goal['id'])
                        if state == 'waiting_input':
                            self.store.waiting(attempt['id'], 'Which details?')
                        elif state == 'completed':
                            receipt = self.store.write_draft(attempt['id'], 'Seed draft')
                            self.store.complete(attempt['id'], receipt['id'])
                before = self.store.inspect()
                result = self.request('request', case['text'])
                if case['expected'].startswith(('no_', 'terminal_')):
                    self.assertEqual(result['control_status'], 'no_target')
                    self.assertEqual(self.store.inspect()['goals'], before['goals'])
                elif case['expected'].startswith('persistent_'):
                    self.assertEqual(result['control_status'], 'selection_required')
                    self.assertEqual(self.store.inspect()['goals'], before['goals'])
                    self.assertEqual(len(self.store.selections()[0]['choices']), 2)
                else:
                    self.assertEqual(result['control_status'], 'applied')
                    changed = [g for g in self.store.inspect()['goals'] if g != next(
                               old for old in before['goals'] if old['id'] == g['id'])]
                    self.assertEqual(len(changed), 1)
                    self.assertEqual(changed[0]['id'], result['goal']['id'])
                    self.assertEqual(changed[0]['state'], 'cancelled' if case['action'] == 'cancel' else 'queued')
                    if case['action'] == 'correct':
                        self.assertEqual(changed[0]['revision'], 2)
                self.assertEqual(self.store.inspect()['acceptances'], before['acceptances'])

    def test_persistent_bound_choice_once_and_fixed_correction_sources(self):
        cedar, birch = self.draft('Cedar'), self.draft('Birch')
        question = self.request('question', 'その下書きを訂正して: Short invitation')
        self.assertEqual(question['control_status'], 'selection_required')
        self.assertEqual(len(self.store.selections()[0]['choices']), 2)
        self.store = Store(self.store.path)
        selected = self.choose('choice', question, cedar['goal']['id'])
        self.assertEqual(selected['control_status'], 'applied')
        self.assertEqual(self.choose('choice', question, cedar['goal']['id']), selected)
        self.assertEqual(self.choose('second', question, birch['goal']['id'])['control_status'],
                         'already_resolved')
        revised = self.store.inspect()['revisions'][-1]
        self.assertEqual(json.loads(revised['sources']), [question['record_id']])
        self.assertEqual(self.store.get_goal(birch['goal']['id'])['revision'], 1)
        with self.assertRaises(Conflict):
            self.choose('choice', question, birch['goal']['id'])

    def test_claim_invalidates_epoch_and_wrong_source_has_no_oracle(self):
        cedar = self.draft('Cedar')['goal']
        self.draft('Birch')
        question = self.request('question', 'その下書きを止めて')
        self.store.claim()
        self.assertEqual(self.store.selections()[0]['status'], 'stale')
        self.assertEqual(self.store.selections()[0]['choices'], [])
        forged = dict(question, source_key='other')
        self.assertEqual(self.choose('forged', forged, cedar['id'])['control_status'], 'rejected')
        self.assertEqual(self.choose('stale', question, cedar['id'])['control_status'], 'stale')
        self.assertEqual(self.store.get_goal(cedar['id'])['state'], 'running')

    def test_forget_original_or_target_hides_labels_and_blocks_application(self):
        for forgotten in ('request', 'target'):
            with self.subTest(forgotten=forgotten):
                self.setUp()
                cedar = self.draft('Cedar')
                self.draft('Birch')
                question = self.request('question', 'その下書きを止めて')
                self.store.forget('forget', question['record_id'] if forgotten == 'request'
                                  else cedar['record_id'])
                projection = self.store.selections()[0]
                self.assertEqual(projection['status'], 'unavailable')
                self.assertEqual(projection['choices'], [])
                self.assertEqual(self.choose('choice', question, cedar['goal']['id'])[
                    'control_status'], 'unavailable')

    def test_concurrent_choices_apply_exactly_once(self):
        cedar = self.draft('Cedar')['goal']
        birch = self.draft('Birch')['goal']
        question = self.request('question', 'その下書きを止めて')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda pair: self.choose(pair[0], question, pair[1]),
                                    [('one', cedar['id']), ('two', birch['id'])]))
        self.assertEqual(sorted(r['control_status'] for r in results), ['already_resolved', 'applied'])
        self.assertEqual(sum(g['state'] == 'cancelled' for g in self.store.inspect()['goals']), 1)

    def test_bound_rejection_more_than_three_and_recovery_fencing(self):
        for name in ('Cedar', 'Birch', 'Maple', 'Oak'):
            self.draft(name)
        self.assertEqual(self.request('broad', 'その下書きを止めて')['control_status'],
                         'more_specific_target_required')
        self.assertEqual(self.store.selections(), [])
        self.assertEqual(self.request('specific', 'Oakの下書きを止めて')['control_status'], 'applied')
        question = self.request('question', 'その下書きを止めて')
        target = self.store.inspect()['goals'][0]['id']
        self.assertEqual(self.choose('foreign', question, 'foreign-id')['control_status'], 'rejected')
        missing = dict(question, selection_id='missing-id')
        self.assertEqual(self.choose('missing', missing, target)['control_status'], 'rejected')
        before = self.store.inspect()
        with self.assertRaises(ValueError):
            self.store.ingress('tampered', 'Select work target', 'control', control={
                'action': 'select', 'selection_id': question['selection_id'],
                'source_key': question['source_key'], 'target_id': target, 'text': 'override'})
        self.assertEqual(self.store.inspect(), before)
        self.store.claim()
        self.store.recover()
        self.assertEqual(self.choose('recovered', question, target)['control_status'], 'stale')
        self.assertEqual(self.store.get_goal(target)['state'], 'queued')

    def test_process_kill_selection_create_and_correct_commit_boundaries(self):
        child = '''import json, os, signal, sys
from pal.store import Store
from pal.controls import parse_control
store=Store(sys.argv[1])
def die(point):
    if point == sys.argv[2]: os.kill(os.getpid(), signal.SIGKILL)
store.fault=die
payload=json.loads(sys.argv[3])
store.ingress(**payload)
'''
        for operation in ('question', 'choice'):
            for boundary in ('selection.mid_transaction', 'ingress.before_commit', 'ingress.after_commit'):
                with self.subTest(operation=operation, boundary=boundary):
                    self.setUp()
                    cedar = self.draft('Cedar')['goal']
                    self.draft('Birch')
                    text = 'その下書きを訂正して: Short invitation'
                    payload = dict(key='question', content=text, intent='control',
                                   natural_control=parse_control(text))
                    if operation == 'choice':
                        question = self.store.ingress(**payload)
                        payload = dict(key='choice', content='Select work target', intent='control',
                                       control=dict(action='select', selection_id=question['selection_id'],
                                                    source_key=question['source_key'], target_id=cedar['id']))
                    before = (self.store.inspect(), self.store.selections())
                    killed = subprocess.run([sys.executable, '-c', child, self.store.path,
                                              boundary, json.dumps(payload)], capture_output=True, timeout=15)
                    self.assertEqual(killed.returncode, -9, killed.stderr)
                    self.store = Store(self.store.path)
                    if boundary != 'ingress.after_commit':
                        self.assertEqual((self.store.inspect(), self.store.selections()), before)
                    replay = self.store.ingress(**payload)
                    after = (self.store.inspect(), self.store.selections())
                    self.assertEqual(self.store.ingress(**payload), replay)
                    self.assertEqual((self.store.inspect(), self.store.selections()), after)
                    self.assertEqual(len(self.store.selections()), 1)
                    if operation == 'choice':
                        self.assertEqual(self.store.get_goal(cedar['id'])['revision'], 2)
                    self.assertIsNotNone(self.store.stored_reply(payload['key']))
                    self.assertEqual(self.store.inspect()['receipts'], [])
                    self.store.deliver()
                    delivered = self.store.inspect()
                    self.store.deliver()
                    self.assertEqual(self.store.inspect(), delivered)
