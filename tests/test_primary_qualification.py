import json
import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from pal.native import ProviderUnavailable
from pal.primary import primary_prompt
from pal.store import Store
from scripts.live_evidence import EvidenceJournal, verify_journal
from scripts.live_runner import RunRejected
from scripts.primary_qualification import (PrimaryGate, QualificationRunner, load_matrix,
                                           seed_case, verify_run, verify_snapshot, build_live, COHORTS)

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


class RecognitionQualificationTests(unittest.TestCase):
    setUp = PrimaryQualificationTests.setUp
    tearDown = PrimaryQualificationTests.tearDown
    def matrix(self):
        return {'recognition_regression':True,'max_primary_calls':16,'cases':[{
            'id':'R01','setup':{'sources':[],'goals':[],'questions':[]},'turns':[
                {'input_record_ref':'request','user_text':'案内の下書きをお願いします。',
                 'acceptable_outcome_set':[{'action_kind':'none','goal_count':0},
                                           {'action_kind':'local_draft','goal_count':1}]},
                {'input_record_ref':'answer','user_text':'土曜日の読書会への案内です。',
                 'only_if_prior_action':'none',
                 'acceptable_outcome_set':[{'action_kind':'local_draft','goal_count':1}]}]}]}

    def recognition_runner(self, matrix=None, response=None):
        self.provider = Scripted(response)
        with patch('scripts.primary_qualification.load_matrix',return_value=matrix or self.matrix()):
            self.runner = QualificationRunner(ROOT,self.directory,self.provider,
                                              scope='scripted',candidate='test-only')
        return self.runner

    def delegate(self, _):
        return json.dumps({'reply':'受け付けます。','action':{
            'kind':'local_draft','spec':'読書会の案内を下書きする','source_ids':[]}})

    def test_delegate_skips_answer_without_input_or_call_and_finishes_one_case(self):
        runner = self.recognition_runner(response=self.delegate)
        runner.run_next();runner.judge(True,'Sufficient request delegates.')
        data = runner.stores[0].inspect()
        self.assertEqual(len(data['primary_turns']),1)
        self.assertNotIn('answer',runner.bindings[0])
        self.assertEqual(len(self.provider.prompts),1)
        self.assertEqual(len(runner.accepted),1)
        self.assertEqual(len(runner.skipped),1)
        result = runner.finish()
        self.assertEqual((result['accepted_turns'],result['skipped_turns'],result['covered_cases']),(1,1,1))
        verified = verify_run(self.directory)
        self.assertEqual((verified['judged_turns'],verified['skipped_turns']),(1,1))
        self.assertTrue(verified['completed'])

    def test_ask_uses_actual_reply_and_frozen_answer_then_one_goal(self):
        def response(prompt):
            if len(self.provider.prompts)==1:
                return json.dumps({'reply':'何の案内ですか？','action':{'kind':'none'}})
            return self.delegate(prompt)
        runner = self.recognition_runner(response=response)
        first=runner.run_next();runner.judge(True,'One essential question.')
        second=runner.run_next()
        context=json.loads(self.provider.prompts[1].split('\nINPUT_JSON\n',1)[1])
        self.assertIn('何の案内ですか？',[r['content'] for r in context['records']])
        self.assertEqual(second['input'],self.matrix()['cases'][0]['turns'][1]['user_text'])
        self.assertNotIn('only_if_prior_action',self.provider.prompts[1])
        runner.judge(True,'Answer delegates once.');result=runner.finish()
        self.assertEqual((result['attempts'],result['covered_cases'],result['skipped_turns']),(2,1,0))
        self.assertEqual(len(runner.stores[0].inspect()['goals']),1)

    def test_failure_never_skips_or_completes(self):
        runner=self.recognition_runner(response=self.delegate)
        runner.run_next();runner.judge(False,'Failed semantic content.')
        self.assertEqual(runner.skipped,[])
        self.assertFalse(verify_run(self.directory)['completed'])
        with self.assertRaises(RunRejected):runner.run_next()

    def test_one_skipped_case_does_not_complete_unexecuted_cases(self):
        matrix=self.matrix()
        other=copy.deepcopy(matrix['cases'][0]);other['id']='R02'
        other['turns'][0]['input_record_ref']='request2'
        other['turns'][1]['input_record_ref']='answer2'
        matrix['cases'].append(other)
        runner=self.recognition_runner(matrix,response=self.delegate)
        runner.run_next();runner.judge(True,'First case delegates.')
        with self.assertRaises(RunRejected):runner.finish()
        runner.close()
        result=verify_run(self.directory)
        self.assertFalse(result['completed'])
        self.assertEqual((result['judged_turns'],result['skipped_turns']),(1,1))

    def test_second_question_cannot_pass_or_skip(self):
        runner=self.recognition_runner();runner.run_next();runner.judge(True,'Essential question.')
        runner.run_next()
        with self.assertRaises(RunRejected):runner.judge(True,'A second question is not recognition.')
        self.assertEqual(runner.skipped,[])
        runner.judge(False,'Follow-up did not delegate.')
        self.assertFalse(verify_run(self.directory)['completed'])

    def test_missing_actual_stored_reply_cannot_admit_answer(self):
        runner=self.recognition_runner();runner.run_next()
        with patch.object(runner.stores[0],'stored_reply',return_value=''):
            with self.assertRaises(RunRejected):runner.judge(True,'Cannot substitute a fixture question.')
        self.assertEqual(runner.skipped,[])
        self.assertEqual(len(self.provider.prompts),1)

    def test_invalid_conditional_schema_and_budget_rejected_before_run_creation(self):
        for mutation in ('first','value','three','first_kind','reask','goals','overflow','budget'):
            matrix=self.matrix();case=matrix['cases'][0]
            if mutation=='first':case['turns'][0]['only_if_prior_action']='none'
            elif mutation=='value':case['turns'][1]['only_if_prior_action']='local_draft'
            elif mutation=='three':case['turns'].append(copy.deepcopy(case['turns'][1]))
            elif mutation=='first_kind':case['turns'][0]['acceptable_outcome_set']=[{'action_kind':'remember'}]
            elif mutation=='reask':case['turns'][1]['acceptable_outcome_set']=[{'action_kind':'none'}]
            elif mutation=='goals':case['setup']['goals']=[{}]
            elif mutation=='overflow':matrix['cases']=[dict(copy.deepcopy(case),id=str(i)) for i in range(9)]
            elif mutation=='budget':matrix['max_primary_calls']=17
            with self.subTest(mutation=mutation):
                with self.assertRaises(RunRejected):self.recognition_runner(matrix)
                self.assertFalse(self.directory.exists())
                self.assertEqual(self.provider.prompts,[])

    def test_invalid_matrix_precedes_live_provider_and_proof_construction(self):
        matrix=self.matrix();matrix['max_primary_calls']=1
        with patch('scripts.primary_qualification.load_matrix',return_value=matrix), \
             patch('scripts.primary_qualification.clean_candidate'), \
             patch('scripts.primary_qualification.AccessProof.load',side_effect=AssertionError('proof touched')):
            with self.assertRaises(RunRejected):
                build_live(ROOT,ROOT/'runtime/nonexistent-recognition-test','unused','test-only')

    def test_live_native_owner_and_record_use_cohort_bound(self):
        for max_calls in (16,10):
            with self.subTest(max_calls=max_calls):
                owner=Mock();owner.command.return_value=['unused-cli']
                proof=Mock();proof.verified_at=time.time();proof.route='existing'
                result=Mock();result.journal=Mock();matrix=self.matrix()
                matrix['max_primary_calls']=max_calls
                with patch('scripts.primary_qualification.load_matrix',return_value=matrix), \
                     patch('scripts.primary_qualification.clean_candidate'), \
                     patch('scripts.primary_qualification.AccessProof.load',return_value=proof), \
                     patch('scripts.primary_qualification.AuditedNative',return_value=owner) as native, \
                     patch('scripts.primary_qualification.subprocess.run',return_value=Mock(stdout='test version')), \
                     patch('scripts.primary_qualification.QualificationRunner',return_value=result):
                    build_live(ROOT,ROOT/'runtime/nonexistent-recognition-test','unused','test-only')
                native.assert_called_once_with(proof,max_calls=max_calls)
                self.assertEqual(result.journal.append.call_args.args[0]['native_slots'],max_calls)
                owner.complete.assert_not_called()
                proof.consume.assert_called_once()

    def test_goal_count_rejects_incorrect_controller_pass(self):
        matrix=self.matrix();matrix['cases'][0]['turns'][0]['acceptable_outcome_set']=[
            {'action_kind':'local_draft','goal_count':0}]
        runner=self.recognition_runner(matrix,response=self.delegate);runner.run_next()
        with self.assertRaises(RunRejected):runner.judge(True,'Wrong expected total must reject.')
        self.assertEqual(runner.skipped,[])
        runner.judge(False,'Goal count discrepancy.')

    def test_verifier_rejects_unjustified_skip_even_with_valid_chain(self):
        runner=self.recognition_runner();runner.journal.append({
            'event':'turn.skipped','case':'R01','turn':2,'prior_turn':1,
            'prior_action':'local_draft','only_if_prior_action':'none'})
        runner.close()
        with self.assertRaises(RunRejected):verify_run(self.directory)

    def test_verifier_rejects_call_on_justified_skipped_turn(self):
        runner=self.recognition_runner(response=self.delegate)
        runner.run_next();runner.judge(True,'Delegation skips answer.')
        runner.journal.append({'event':'call.started','case':'R01','turn':2,'call_sequence':2})
        runner.close()
        with self.assertRaises(RunRejected):verify_run(self.directory)

    def rewritten_evidence(self, records):
        directory=Path(self.temp.name)/'rewritten'
        directory.mkdir()
        for path in self.directory.glob('*.txt'):
            (directory/path.name).write_bytes(path.read_bytes())
        with EvidenceJournal(directory/'journal.jsonl','scripted') as journal:
            for record in records:
                journal.append({k:v for k,v in record.items() if k not in
                                ('sequence','scope','previous_sha256','sha256','recorded_at')})
        return directory

    def test_completed_plan_requires_real_successful_call_lifecycle(self):
        runner=self.recognition_runner(response=self.delegate)
        runner.run_next();runner.judge(True,'Delegate once.');runner.finish()
        records=verify_journal(self.directory/'journal.jsonl')
        events={'permit.granted','call.started','call.returned','proposal.received'}
        forged=[dict(r) for r in records if r['event'] not in events]
        next(r for r in forged if r['event']=='qualification.finished')['attempts']=0
        next(r for r in forged if r['event']=='run.closed')['attempts']=0
        directory=self.rewritten_evidence(forged)
        with self.assertRaises(RunRejected):verify_run(directory)

    def test_duplicate_capture_cannot_replace_judged_action_to_justify_skip(self):
        runner=self.recognition_runner()
        first=runner.run_next();runner.judge(True,'Essential question.')
        replacement=copy.deepcopy(first)
        replacement['proposal']['action']={'kind':'local_draft','spec':'replacement','source_ids':[]}
        runner.journal.append(dict(replacement,event='turn.captured'))
        runner.journal.append({'event':'turn.skipped','case':'R01','turn':2,'prior_turn':1,
                               'prior_action':'local_draft','only_if_prior_action':'none'})
        runner.journal.append({'event':'qualification.finished','accepted_turns':1,
                               'skipped_turns':1,'covered_cases':1,'attempts':1})
        runner.close()
        with self.assertRaises(RunRejected):verify_run(self.directory)

    def test_sixteen_call_gate_is_effective(self):
        events=[];provider=Scripted()
        gate=PrimaryGate(provider,events.append,time.monotonic()+900,max_calls=16)
        for i in range(16):gate.grant('R',i,'PRIMARY\n'+str(i));gate.complete('PRIMARY\n'+str(i))
        with self.assertRaises(ProviderUnavailable):gate.grant('R',17,'PRIMARY\nextra')
        self.assertEqual(len(provider.prompts),16)

    def test_ten_call_suffix_gate_rejects_eleventh_before_provider(self):
        events=[];provider=Scripted()
        gate=PrimaryGate(provider,events.append,time.monotonic()+900,max_calls=10)
        for i in range(10):
            prompt='PRIMARY\n'+str(i);gate.grant('R',i,prompt);gate.complete(prompt)
        with self.assertRaises(ProviderUnavailable):gate.grant('R',11,'PRIMARY\nextra')
        self.assertEqual((gate.attempts,len(provider.prompts)),(10,10))

    def test_eleven_worst_case_calls_rejected_before_suffix_run_creation(self):
        matrix=self.matrix();matrix['max_primary_calls']=10
        matrix['cases']=[dict(copy.deepcopy(matrix['cases'][0]),id='R'+str(i)) for i in range(5)]
        last=copy.deepcopy(matrix['cases'][0]);last['id']='extra';last['turns']=last['turns'][:1]
        matrix['cases'].append(last)
        with self.assertRaisesRegex(RunRejected,'worst-case cohort calls exceed bound'):
            self.recognition_runner(matrix)
        self.assertFalse(self.directory.exists())
        self.assertEqual(self.provider.prompts,[])

    def test_frozen_suffix_is_exact_unexecuted_cases_and_smaller_owner(self):
        path,sha=COHORTS['recognition-r03-r08']
        suffix=load_matrix(ROOT/path,sha)
        original_path,original_sha=COHORTS['recognition-r01-r08']
        original=load_matrix(ROOT/original_path,original_sha)
        self.assertEqual(suffix['cases'],original['cases'][2:])
        self.assertEqual([c['id'] for c in suffix['cases']],['R03','R04','R05','R06','R07','R08'])
        self.assertEqual(sum(len(c['turns']) for c in suffix['cases']),10)
        self.assertEqual(suffix['max_primary_calls'],10)
        self.assertEqual(suffix['retained_measurement']['results'],{'R01':'PASS','R02':'MISS'})
        self.assertEqual(suffix['retained_measurement']['further_request_misses_allowed'],0)
        self.assertLessEqual(2+suffix['max_primary_calls'],16)
        self.runner=QualificationRunner(ROOT,self.directory,self.provider,scope='scripted',
                                        candidate='test-only',cohort='recognition-r03-r08')
        self.assertEqual(self.runner.gate.max_calls,10)
        opened=verify_journal(self.directory/'journal.jsonl')[0]
        self.assertEqual(opened['max_attempts'],10)
        self.assertEqual(opened['hashes'][path],sha)
        self.assertFalse(self.provider.prompts)


if __name__=='__main__':
    unittest.main()
