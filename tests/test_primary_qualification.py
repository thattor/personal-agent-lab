import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pal.native import ProviderUnavailable
from pal.primary import primary_prompt
from pal.store import Store
from scripts.live_evidence import verify_journal
from scripts.live_runner import RunRejected
from scripts.primary_qualification import (PrimaryGate, QualificationRunner, load_matrix,
                                           seed_case, verify_run, verify_snapshot)

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT/'evidence/reviews/judgment-boundary/primary-heldout.json'


class Scripted:
    identity = 'scripted_primary'

    def __init__(self, response=None):
        self.response = response or (lambda _: json.dumps({'reply':'記録しました。', 'action':{'kind':'none'}}))
        self.prompts = []
        self.stopped = 0

    def complete(self, prompt):
        self.prompts.append(prompt)
        return self.response(prompt)

    def stop(self):
        self.stopped += 1


class PrimaryQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)/'run'
        self.provider = Scripted()
        self.runner = None

    def tearDown(self):
        if self.runner is not None:
            self.runner.close()
        self.temp.cleanup()

    def runner_for(self, provider=None):
        self.runner = QualificationRunner(ROOT,self.directory,provider or self.provider,
                                          scope='scripted',candidate='test-only')
        return self.runner

    def test_every_frozen_fixture_has_exact_host_and_offered_bindings(self):
        for case in load_matrix(MATRIX)['cases']:
            store = Store(Path(self.temp.name)/(case['id']+'.sqlite'))
            bindings = seed_case(store,case)
            data = store.inspect()
            for expected in case['setup']['goals']:
                goal = next(g for g in data['goals'] if g['id']==bindings[expected['ref']])
                self.assertEqual(tuple(goal[k] for k in ('state','revision','epoch')),
                                 tuple(expected[k] for k in ('state','revision','epoch')))
                self.assertLessEqual(goal['total_claims'],1)
            ack = store.prepare_primary('test',case['turns'][0]['user_text'])
            context = store.primary_context('test')
            verify_snapshot(store,context)
            self.assertEqual({g['id'] for g in context['goals']},
                             {bindings[g['ref']] for g in case['setup']['goals']})
            self.assertEqual({q['id'] for q in context['questions']},
                             {bindings[q['ref']] for q in case['setup']['questions']})
            self.assertIn(ack['record_id'],context['manifest'])

    def test_snapshot_omission_is_setup_failure_before_a_model_call(self):
        case = load_matrix(MATRIX)['cases'][4]
        store = Store(Path(self.temp.name)/'fixture.sqlite')
        seed_case(store,case)
        store.prepare_primary('test',case['turns'][0]['user_text'])
        context = store.primary_context('test')
        context['questions'] = context['questions'][:-1]
        with self.assertRaises(RunRejected):
            verify_snapshot(store,context)
        self.assertEqual(self.provider.prompts,[])

    def test_next_requires_judgment_and_turn_two_uses_actual_reply(self):
        runner = self.runner_for()
        first = runner.run_next()
        with self.assertRaises(RunRejected):
            runner.run_next()
        self.assertEqual(len(self.provider.prompts),1)
        runner.judge(True,'Scripted ordering test only; no semantic qualification.')
        second = runner.run_next()
        context = json.loads(self.provider.prompts[1].split('\nINPUT_JSON\n',1)[1])
        record_ids = {r['id'] for r in context['records']}
        self.assertIn(first['outcome']['record_id'],record_ids)
        self.assertIn(first['outcome']['response_id'],record_ids)
        self.assertEqual(self.provider.prompts[1],primary_prompt(context))
        self.assertEqual(second['turn'],2)
        for field in ('acceptable_outcome_set','required_observations','target_ref'):
            self.assertNotIn(field,self.provider.prompts[1])

    def test_oracle_canary_never_reaches_provider(self):
        runner = self.runner_for()
        original = Store.primary_context
        def inject(store,key):
            value = original(store,key)
            value['PAL_ORACLE_ONLY'] = 'hidden oracle'
            return value
        with patch.object(Store,'primary_context',inject):
            with self.assertRaises(RunRejected):
                runner.run_next()
        self.assertEqual(self.provider.prompts,[])
        self.assertTrue(any(r['event']=='turn.failed' for r in verify_journal(self.directory/'journal.jsonl')))

    def test_decode_and_provider_failure_are_visible_and_settled(self):
        def fail(_):
            raise ProviderUnavailable('scripted failure')
        for label,response in [('decode',lambda _:'not json'),('provider',fail)]:
            with self.subTest(label=label):
                runner = QualificationRunner(ROOT,Path(self.temp.name)/label,Scripted(response),
                                             scope='scripted',candidate='test-only')
                try:
                    with self.assertRaises(Exception):
                        runner.run_next()
                    data = runner.stores[0].inspect()
                    self.assertEqual([p['status'] for p in data['primary_turns']],['rejected'])
                    self.assertEqual(data['goals'],[])
                    journal = verify_journal(runner.directory/'journal.jsonl')
                    self.assertTrue(any(r['event']=='turn.failed' for r in journal))
                finally:
                    runner.close()

    def test_raw_unsafe_proposal_retained_before_host_rejection(self):
        proposal = {'reply':'中止します。','action':{'kind':'control','op':'cancel','goal_id':'not-offered'}}
        runner = self.runner_for(Scripted(lambda _:json.dumps(proposal)))
        frame = runner.run_next()
        self.assertEqual(frame['outcome']['primary_status'],'rejected')
        records = verify_journal(self.directory/'journal.jsonl')
        events = [r['event'] for r in records]
        self.assertLess(events.index('proposal.received'),events.index('turn.captured'))
        self.assertEqual(frame['proposal'],proposal)
        with self.assertRaises(RunRejected):
            runner.judge(True,'Host rejection cannot make unsafe semantics pass.')
        runner.judge(False,'Unsafe model proposal; host rejected it.')
        with self.assertRaises(RunRejected):
            runner.run_next()

    def test_wrong_offered_target_can_apply_but_cannot_receive_semantic_pass(self):
        def wrong_target(prompt):
            context = json.loads(prompt.split('\nINPUT_JSON\n',1)[1])
            question = next(q for q in context['questions'] if '集合場所' in q['prompt'])
            return json.dumps({'reply':'回答します。','action':{'kind':'answer','question_id':question['id']}})
        runner = self.runner_for(Scripted(wrong_target))
        runner.index = runner.turns.index((4,0))
        frame = runner.run_next()
        self.assertEqual(frame['outcome']['primary_status'],'complete')
        wrong_goal = runner.bindings[4]['pha05-g2']
        self.assertEqual(frame['outcome']['goal']['id'],wrong_goal)
        with self.assertRaises(RunRejected):
            runner.judge(True,'A committed wrong target must fail semantics.')
        runner.judge(False,'Wrong target applied by host; semantic failure preserved.')

    def test_post_deadline_response_is_retained_but_input_is_rejected(self):
        def late(_):
            self.runner.gate.deadline = time.monotonic()-1
            return json.dumps({'reply':'遅れた応答','action':{'kind':'none'}},ensure_ascii=False)
        runner = self.runner_for(Scripted(late))
        with self.assertRaises(ProviderUnavailable):
            runner.run_next()
        self.assertEqual([p['status'] for p in runner.stores[0].inspect()['primary_turns']],['rejected'])
        self.assertIn('遅れた応答',(self.directory/'PHA-01-1.response.txt').read_text())
        self.assertFalse(verify_run(self.directory)['completed'])

    def test_read_only_verification_detects_changed_raw_proposal(self):
        runner = self.runner_for()
        runner.run_next()
        runner.close()
        (self.directory/'PHA-01-1.response.txt').write_text('changed')
        with self.assertRaises(RunRejected):
            verify_run(self.directory)

    def test_verify_is_read_only_and_old_run_cannot_resume(self):
        runner = self.runner_for()
        runner.run_next()
        runner.close()
        raw = (self.directory/'journal.jsonl').read_bytes()
        with patch('scripts.primary_qualification.AuditedNative',side_effect=AssertionError('provider constructed')):
            result = verify_run(self.directory)
        self.assertFalse(result['completed'])
        self.assertEqual(raw,(self.directory/'journal.jsonl').read_bytes())
        with self.assertRaises(FileExistsError):
            QualificationRunner(ROOT,self.directory,Scripted(),scope='scripted',candidate='test-only')
        self.assertEqual(len(self.provider.prompts),1)

    def test_initial_journal_failure_still_stops_owned_provider(self):
        with patch('scripts.primary_qualification.EvidenceJournal.append',side_effect=OSError('test disk failure')):
            with self.assertRaises(OSError):
                self.runner_for()
        self.assertEqual(self.provider.stopped,1)

    def test_new_cohort_excludes_observed_cases_and_preserves_untested_cases(self):
        self.runner = QualificationRunner(ROOT,self.directory,self.provider,
                                          scope='scripted',candidate='test-only',
                                          cohort='unseen-plus-contrasts')
        cases = self.runner.matrix['cases']
        self.assertEqual(cases[:9],load_matrix(MATRIX)['cases'][3:])
        self.assertEqual([c['id'] for c in cases[9:]],['PHB-01','PHB-02','PHB-03'])
        self.assertEqual(len(self.runner.turns),24)
        self.assertFalse({'PHA-01','PHA-02','PHA-03'} & {c['id'] for c in cases})
        first = self.runner.run_next()
        self.assertEqual(first['case'],'PHA-04')
        self.assertEqual(len(self.provider.prompts),1)
        opened = verify_journal(self.directory/'journal.jsonl')[0]
        self.assertEqual(opened['cohort'],'unseen-plus-contrasts')
        self.assertFalse(opened['resume'])

    def test_unknown_cohort_cannot_invoke_provider_or_create_run(self):
        with self.assertRaises(ValueError):
            QualificationRunner(ROOT,self.directory,self.provider,scope='scripted',
                                candidate='test-only',cohort='arbitrary')
        self.assertFalse(self.directory.exists())
        self.assertEqual(self.provider.prompts,[])
        self.assertEqual(self.provider.stopped,1)


class PrimaryGateTests(unittest.TestCase):
    def gate(self, *, clock=time.monotonic, deadline=None):
        self.events = []
        self.provider = Scripted()
        return PrimaryGate(self.provider,self.events.append,deadline or clock()+900,clock=clock)

    def test_wrong_prompt_does_not_use_a_slot_or_provider(self):
        gate = self.gate()
        gate.grant('case',1,'PRIMARY\nfirst')
        with self.assertRaises(ProviderUnavailable):
            gate.complete('PRIMARY\nother')
        self.assertEqual(gate.attempts,0)
        self.assertEqual(self.provider.prompts,[])
        self.assertEqual(self.provider.stopped,1)

    def test_twenty_four_attempt_cap_and_single_use_permit(self):
        gate = self.gate()
        for number in range(24):
            prompt = 'PRIMARY\n'+str(number)
            gate.grant('case',number,prompt)
            gate.complete(prompt)
        with self.assertRaises(ProviderUnavailable):
            gate.grant('case',25,'PRIMARY\nextra')
        self.assertEqual(len(self.provider.prompts),24)
        gate = self.gate()
        gate.grant('case',1,'PRIMARY\none')
        gate.complete('PRIMARY\none')
        with self.assertRaises(ProviderUnavailable):
            gate.complete('PRIMARY\none')
        self.assertEqual(len(self.provider.prompts),1)

    def test_expiry_between_grant_and_call_does_not_contact_provider(self):
        now = [10]
        gate = self.gate(clock=lambda:now[0],deadline=20)
        gate.grant('case',1,'PRIMARY\none')
        now[0] = 20
        with self.assertRaises(ProviderUnavailable):
            gate.complete('PRIMARY\none')
        self.assertEqual(self.provider.prompts,[])

    def test_response_after_deadline_is_not_returned(self):
        now = [10]
        gate = self.gate(clock=lambda:now[0],deadline=20)
        def response(_):
            now[0] = 21
            return 'late'
        self.provider.response = response
        gate.grant('case',1,'PRIMARY\none')
        with self.assertRaises(ProviderUnavailable):
            gate.complete('PRIMARY\none')
        self.assertEqual(gate.attempts,1)
        self.assertEqual(self.provider.stopped,1)


if __name__=='__main__':
    unittest.main()
