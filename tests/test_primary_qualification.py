import json
import copy
import hashlib
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from pal.native import ProviderUnavailable
from pal.primary import primary_prompt
from pal.store import Store
from scripts.live_evidence import EvidenceJournal, verify_journal
from scripts.live_runner import RunRejected, product_rel_paths
from scripts.primary_qualification import (PrimaryGate, QualificationRunner, load_matrix,
                                           seed_case, verify_run, verify_snapshot, build_live, COHORTS,
                                           FREEZE, NEW_FREEZE, COMPOUND_FREEZE, INTENT_LIMITS_FREEZE,
                                           ASK_FIRST_FREEZE, GROUNDING_FREEZE,
                                           validate_freeze, cohort_matrix, QualificationPin)

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT/'evidence/reviews/judgment-boundary/primary-heldout.json'

OLD_FREEZE_SHA = '1736095ccbee1f221f0ff062b59593cae4139de739cfd88c93586d0e694be2e2'
# Explicit old-corpus allowlist: never discover or copy the withheld clarification corpus.
KNOWN_FIXTURES = (
    'primary-heldout.json', 'primary-remaining.json', 'primary-unseen-contrasts.json',
    'recognition-r01-r08.json', 'recognition-r03-r08.json',
    'recognition-r09-r16.json', 'recognition-n01-n24.json',
)


def synthetic_freeze(root, relative):
    files = {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
             for name in sorted(product_rel_paths(root))}
    identity = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    manifest = {'candidate': 'content:sha256:'+identity, 'files': files,
                'scope': 'SCRIPTED_TEST_ONLY', 'human_evaluation': False}
    path = root/relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, sort_keys=True))
    return manifest


def isolated_test_root(destination):
    destination.mkdir()
    paths = set(product_rel_paths(ROOT))
    paths.update(str(p.relative_to(ROOT)) for pattern in ('live_*.py', 'primary_*.py')
                 for p in (ROOT/'scripts').glob(pattern))
    paths.update('evidence/reviews/judgment-boundary/'+name for name in KNOWN_FIXTURES)
    for relative in sorted(paths):
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, target)
    (destination/'runtime').mkdir()
    for relative in (FREEZE, NEW_FREEZE, COMPOUND_FREEZE, INTENT_LIMITS_FREEZE, ASK_FIRST_FREEZE, GROUNDING_FREEZE):
        synthetic_freeze(destination, relative)
    return destination


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
        self.root = isolated_test_root(Path(self.temp.name)/'source')
        self.directory = Path(self.temp.name)/'run'
        self.provider = Scripted()
        self.runner = None

    def tearDown(self):
        if self.runner is not None:
            self.runner.close()
        self.temp.cleanup()

    def runner_for(self, provider=None):
        self.runner = QualificationRunner(self.root,self.directory,provider or self.provider,
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
                runner = QualificationRunner(self.root,Path(self.temp.name)/label,Scripted(response),
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
            QualificationRunner(self.root,self.directory,Scripted(),scope='scripted',candidate='test-only')
        self.assertEqual(len(self.provider.prompts),1)

    def test_initial_journal_failure_still_stops_owned_provider(self):
        with patch('scripts.primary_qualification.EvidenceJournal.append',side_effect=OSError('test disk failure')):
            with self.assertRaises(OSError):
                self.runner_for()
        self.assertEqual(self.provider.stopped,1)

    def test_new_cohort_excludes_observed_cases_and_preserves_untested_cases(self):
        self.runner = QualificationRunner(self.root,self.directory,self.provider,
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
            QualificationRunner(self.root,self.directory,self.provider,scope='scripted',
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

    def recognition_runner(self, matrix=None, response=None, cohort='heldout-v1'):
        self.provider = Scripted(response)
        with patch('scripts.primary_qualification.load_matrix',return_value=matrix or self.matrix()):
            self.runner = QualificationRunner(self.root,self.directory,self.provider,
                                              scope='scripted',candidate='test-only',cohort=cohort)
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
                build_live(self.root,self.root/'runtime/nonexistent-recognition-test','unused','test-only')

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
                    build_live(self.root,self.root/'runtime/nonexistent-recognition-test','unused','test-only')
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
        directory=Path(tempfile.mkdtemp(prefix='rewritten-',dir=self.temp.name))
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
        path,sha,_=COHORTS['recognition-r03-r08']
        suffix=load_matrix(ROOT/path,sha)
        original_path,original_sha,_=COHORTS['recognition-r01-r08']
        original=load_matrix(ROOT/original_path,original_sha)
        self.assertEqual(suffix['cases'],original['cases'][2:])
        self.assertEqual([c['id'] for c in suffix['cases']],['R03','R04','R05','R06','R07','R08'])
        self.assertEqual(sum(len(c['turns']) for c in suffix['cases']),10)
        self.assertEqual(suffix['max_primary_calls'],10)
        self.assertEqual(suffix['retained_measurement']['results'],{'R01':'PASS','R02':'MISS'})
        self.assertEqual(suffix['retained_measurement']['further_request_misses_allowed'],0)
        self.assertLessEqual(2+suffix['max_primary_calls'],16)
        self.runner=QualificationRunner(self.root,self.directory,self.provider,scope='scripted',
                                        candidate='test-only',cohort='recognition-r03-r08')
        self.assertEqual(self.runner.gate.max_calls,10)
        opened=verify_journal(self.directory/'journal.jsonl')[0]
        self.assertEqual(opened['max_attempts'],10)
        self.assertEqual(opened['hashes'][path],sha)
        self.assertFalse(self.provider.prompts)


class FreezeQualificationTests(unittest.TestCase):
    setUp = PrimaryQualificationTests.setUp
    tearDown = PrimaryQualificationTests.tearDown
    matrix = RecognitionQualificationTests.matrix
    recognition_runner = RecognitionQualificationTests.recognition_runner
    delegate = RecognitionQualificationTests.delegate
    rewritten_evidence = RecognitionQualificationTests.rewritten_evidence

    def test_isolated_root_has_only_known_corpora_and_real_hash_checks(self):
        evidence = self.root/'evidence/reviews/judgment-boundary'
        self.assertEqual({p.name for p in evidence.iterdir()},
                         set(KNOWN_FIXTURES) | {Path(p).name for p in
                             (FREEZE, NEW_FREEZE, COMPOUND_FREEZE, INTENT_LIMITS_FREEZE, ASK_FIRST_FREEZE, GROUNDING_FREEZE)})
        self.assertFalse((evidence/'primary-clarification-heldout.json').exists())
        with self.assertRaises((FileNotFoundError, RunRejected)):
            cohort_matrix(self.root, 'clarification-heldout')
        for relative in (FREEZE, NEW_FREEZE, COMPOUND_FREEZE, INTENT_LIMITS_FREEZE, ASK_FIRST_FREEZE, GROUNDING_FREEZE):
            self.assertEqual(validate_freeze(self.root, relative)['scope'], 'SCRIPTED_TEST_ONLY')
        source = self.root/'pal/primary.py'
        source.write_bytes(source.read_bytes()+b'\n# scripted drift\n')
        for relative in (FREEZE, NEW_FREEZE, COMPOUND_FREEZE, INTENT_LIMITS_FREEZE, ASK_FIRST_FREEZE, GROUNDING_FREEZE):
            with self.assertRaises(RunRejected):
                validate_freeze(self.root, relative)

    def test_closed_cohort_mapping_preserves_old_bindings(self):
        old = {'heldout-v1', 'remaining-after-c031', 'unseen-plus-contrasts',
               'recognition-r01-r08', 'recognition-r03-r08',
               'recognition-r09-r16', 'recognition-n01-n24'}
        new = {'clarification-r01-r08', 'clarification-r09-r16',
               'clarification-n01-n24', 'clarification-heldout'}
        compound = {'compound-n01-n24', 'compound-r01-r08', 'compound-r09-r16', 'compound-heldout'}
        intent_limits = {'intent-limits-n01-n24', 'intent-limits-r01-r08',
                         'intent-limits-r09-r16', 'intent-limits-heldout'}
        ask_first = {'ask-first-n01-n24', 'ask-first-r01-r08',
                     'ask-first-r09-r16', 'ask-first-heldout'}
        grounding = {'grounding-n01-n24', 'grounding-r01-r08',
                     'grounding-r09-r16', 'grounding-heldout'}
        self.assertEqual(set(COHORTS), old | new | compound | intent_limits | ask_first | grounding)
        for name in grounding:
            self.assertEqual(COHORTS[name][2], GROUNDING_FREEZE)
        for name in ask_first:
            self.assertEqual(COHORTS[name][2], ASK_FIRST_FREEZE)
        for name in intent_limits:
            self.assertEqual(COHORTS[name][2], INTENT_LIMITS_FREEZE)
        for name in compound:
            self.assertEqual(COHORTS[name][2], COMPOUND_FREEZE)
        for name in old:
            self.assertEqual(COHORTS[name][2], FREEZE)
        for name in new:
            self.assertEqual(COHORTS[name][2], NEW_FREEZE)
        for suffix in ('r01-r08', 'r09-r16', 'n01-n24'):
            self.assertEqual(COHORTS['clarification-'+suffix][:2],
                             COHORTS['recognition-'+suffix][:2])
            fixture, freeze, matrix, maximum = cohort_matrix(self.root, 'clarification-'+suffix)
            self.assertEqual((fixture, freeze), (COHORTS['clarification-'+suffix][0], NEW_FREEZE))
            self.assertEqual(maximum, 24 if suffix=='n01-n24' else 16)
            self.assertTrue(matrix['cases'])

    def test_compound_cohorts_reuse_fixed_inputs_and_have_separate_product_binding(self):
        for suffix in ('n01-n24', 'r01-r08', 'r09-r16'):
            alias = COHORTS['compound-'+suffix]
            self.assertEqual(alias[:2], COHORTS['recognition-'+suffix][:2])
            self.assertEqual(alias[2],
                'evidence/reviews/judgment-boundary/primary-compound-candidate-freeze.json')
            self.assertNotEqual(alias[2], COHORTS['clarification-'+suffix][2])
        self.assertFalse((self.root/'evidence/reviews/judgment-boundary/primary-compound-heldout.json').exists())
        with self.assertRaises(RunRejected):
            cohort_matrix(self.root, 'compound-heldout')

    def test_intent_limits_cohorts_bind_fresh_source_without_redirecting_compound(self):
        for suffix in ('n01-n24', 'r01-r08', 'r09-r16'):
            current = COHORTS['intent-limits-'+suffix]
            self.assertEqual(current[:2], COHORTS['recognition-'+suffix][:2])
            self.assertEqual(current[2],
                'evidence/reviews/judgment-boundary/primary-intent-limits-candidate-freeze.json')
            self.assertEqual(COHORTS['compound-'+suffix][2], COMPOUND_FREEZE)
        self.assertFalse((self.root/'evidence/reviews/judgment-boundary/primary-intent-limits-heldout.json').exists())
        with self.assertRaises(RunRejected):
            cohort_matrix(self.root, 'intent-limits-heldout')

    def test_freeze_rejects_malformed_missing_and_inexact_manifests(self):
        valid = synthetic_freeze(self.root, NEW_FREEZE)
        path = self.root/NEW_FREEZE
        variants = [None, [], {}, {'files': {}}, dict(valid, files=[]),
                    dict(valid, candidate=''), dict(valid, candidate=3),
                    dict(valid, candidate='content:sha256:'+'0'*64)]
        for replacement in ('', 'f'*63, 'F'*64, 'x'*64, 123):
            files = dict(valid['files']);files['pal/primary.py'] = replacement
            variants.append(dict(valid, files=files))
        files = dict(valid['files']);files.pop('pal/primary.py')
        variants.append(dict(valid, files=files))
        for extra in ('pal/not-real.py', '../outside.py', '/absolute.py'):
            variants.append(dict(valid, files=dict(valid['files'], **{extra:'0'*64})))
        for index, value in enumerate(variants):
            with self.subTest(index=index):
                path.write_text(json.dumps(value))
                with self.assertRaises(RunRejected):validate_freeze(self.root, NEW_FREEZE)
        path.write_text('{invalid')
        with self.assertRaises(RunRejected):validate_freeze(self.root, NEW_FREEZE)
        path.unlink()
        with self.assertRaises(RunRejected):validate_freeze(self.root, NEW_FREEZE)

    def test_new_candidates_keep_original_recognition_inputs_and_heldout_isolated(self):
        for prefix, expected_freeze in (('ask-first', ASK_FIRST_FREEZE), ('grounding', GROUNDING_FREEZE)):
            for suffix in ('n01-n24', 'r01-r08', 'r09-r16'):
                self.assertEqual(COHORTS[prefix+'-'+suffix][:2],
                                 COHORTS['recognition-'+suffix][:2])
                _, freeze, matrix, maximum = cohort_matrix(self.root, prefix+'-'+suffix)
                self.assertEqual(freeze, expected_freeze)
                self.assertEqual(maximum, 24 if suffix=='n01-n24' else 16)
                self.assertTrue(matrix['cases'])
            self.assertFalse((self.root/('evidence/reviews/judgment-boundary/primary-'+prefix+'-heldout.json')).exists())
            with self.assertRaises(RunRejected):cohort_matrix(self.root, prefix+'-heldout')

    def test_untrusted_manifest_paths_are_rejected_before_file_reads(self):
        manifest = synthetic_freeze(self.root, NEW_FREEZE)
        # Same-size map defeats count-only validation and attempts to escape the test root.
        manifest['files'].pop('pal/primary.py')
        manifest['files']['../outside.py'] = '0'*64
        (self.root/NEW_FREEZE).write_text(json.dumps(manifest))
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('manifest path was read')):
            with self.assertRaises(RunRejected):validate_freeze(self.root, NEW_FREEZE)

    def test_added_removed_web_and_symlink_product_files_fail_closed(self):
        added = self.root/'pal/new_component.py'
        added.write_text('# new product file')
        with self.assertRaises(RunRejected):validate_freeze(self.root, NEW_FREEZE)
        added.unlink()
        web = self.root/'pal/web/new-resource.txt'
        web.write_text('new web resource')
        with self.assertRaises(RunRejected):validate_freeze(self.root, NEW_FREEZE)
        web.unlink()
        existing = self.root/'pal/web/style.css'
        original = existing.read_bytes();existing.unlink()
        with self.assertRaises(RunRejected):validate_freeze(self.root, NEW_FREEZE)
        existing.write_bytes(original)
        added.symlink_to(self.root/'pal/primary.py')
        with self.assertRaises(RunRejected):validate_freeze(self.root, NEW_FREEZE)

    def test_historical_freeze_fails_current_product_while_new_match_succeeds(self):
        (self.root/FREEZE).write_bytes((ROOT/FREEZE).read_bytes())
        with self.assertRaises(RunRejected):validate_freeze(self.root, FREEZE)
        manifest = validate_freeze(self.root, NEW_FREEZE)
        self.assertTrue(manifest['candidate'].startswith('content:sha256:'))

    def test_live_mismatch_precedes_clean_proof_and_owner_construction(self):
        (self.root/NEW_FREEZE).write_text('{}')
        with patch('scripts.primary_qualification.clean_candidate', side_effect=AssertionError('clean called')), \
             patch('scripts.primary_qualification.AccessProof.load', side_effect=AssertionError('proof loaded')), \
             patch('scripts.primary_qualification.AuditedNative', side_effect=AssertionError('owner created')):
            with self.assertRaises(RunRejected):
                build_live(self.root, self.root/'runtime/preflight', 'unused', 'test-only',
                           cohort='clarification-r01-r08')
        self.assertFalse((self.root/'runtime/preflight').exists())

    def test_runner_mismatch_precedes_owner_claim_and_run_directory(self):
        (self.root/NEW_FREEZE).write_text('{}')
        owner = Mock();owner._runner_claimed = False
        with self.assertRaises(RunRejected):
            QualificationRunner(self.root, self.directory, owner, scope='live_synthetic',
                                candidate='test-only', cohort='clarification-r01-r08')
        self.assertFalse(owner._runner_claimed)
        self.assertFalse(self.directory.exists())
        owner.complete.assert_not_called();owner.proof.check.assert_not_called()
        owner.stop.assert_called_once()

    def test_pin_tracks_selected_freeze_and_current_product_only(self):
        fixture = self.root/COHORTS['clarification-r01-r08'][0]
        pin = QualificationPin(self.root, fixture, NEW_FREEZE)
        old = self.root/FREEZE;old.write_bytes(old.read_bytes()+b'\n')
        pin.check()
        selected = self.root/NEW_FREEZE;selected.write_bytes(selected.read_bytes()+b'\n')
        with self.assertRaises(RunRejected):pin.check()
        pin = QualificationPin(self.root, fixture, NEW_FREEZE)
        product = self.root/'pal/primary.py';product.write_bytes(product.read_bytes()+b'\n')
        with self.assertRaises(RunRejected):pin.check()

    def test_source_drift_stops_runner_before_provider_invocation(self):
        runner = self.recognition_runner(response=self.delegate, cohort='clarification-r01-r08')
        product = self.root/'pal/primary.py';product.write_bytes(product.read_bytes()+b'\n')
        with self.assertRaises(RunRejected):runner.run_next()
        self.assertFalse(self.provider.prompts)

    def test_new_opened_record_binds_selected_freeze_and_verifier_rejects_tampering(self):
        runner = self.recognition_runner(response=self.delegate, cohort='clarification-r01-r08')
        runner.run_next();runner.judge(True, 'Scripted delegation.');runner.finish()
        records = verify_journal(self.directory/'journal.jsonl')
        opened = records[0]
        self.assertEqual(opened['freeze'], NEW_FREEZE)
        self.assertEqual(opened['freeze_sha256'], hashlib.sha256((self.root/NEW_FREEZE).read_bytes()).hexdigest())
        self.assertEqual(opened['product_identity'], validate_freeze(self.root, NEW_FREEZE)['candidate'])
        self.assertEqual(opened['cohort_sha256'], COHORTS['clarification-r01-r08'][1])
        self.assertTrue(verify_run(self.directory)['completed'])
        for mutation in ('old_freeze', 'missing_freeze', 'freeze_hash', 'identity', 'cohort_hash',
                         'missing_hash_pair', 'missing_identity_pair', 'fixture_hash', 'missing_cohort'):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(records);record = changed[0]
                if mutation=='old_freeze':record['freeze']=FREEZE
                elif mutation=='missing_freeze':record.pop('freeze')
                elif mutation=='freeze_hash':record['freeze_sha256']='0'*64
                elif mutation=='identity':record['product_identity']='other'
                elif mutation=='cohort_hash':record['cohort_sha256']='0'*64
                elif mutation=='missing_hash_pair':
                    record.pop('freeze_sha256');record['hashes'].pop(NEW_FREEZE)
                elif mutation=='missing_identity_pair':
                    record.pop('product_identity');record.pop('product_candidate')
                elif mutation=='fixture_hash':record['hashes'][record['fixture']]='0'*64
                elif mutation=='missing_cohort':record.pop('cohort')
                with self.assertRaises(RunRejected):verify_run(self.rewritten_evidence(changed))

    def test_legacy_old_cohort_record_remains_verifiable_without_new_fields(self):
        runner = self.recognition_runner(response=self.delegate)
        runner.run_next();runner.judge(True, 'Scripted delegation.');runner.finish()
        records = verify_journal(self.directory/'journal.jsonl')
        for field in ('freeze', 'freeze_sha256', 'product_identity', 'cohort_sha256'):
            records[0].pop(field)
        directory = self.rewritten_evidence(records)
        before = (directory/'journal.jsonl').read_bytes()
        self.assertTrue(verify_run(directory)['completed'])
        self.assertEqual(before, (directory/'journal.jsonl').read_bytes())


class RepositoryFreezeTests(unittest.TestCase):
    def test_retained_freezes_and_current_runtime_change_are_distinct(self):
        self.assertEqual(hashlib.sha256((ROOT/FREEZE).read_bytes()).hexdigest(), OLD_FREEZE_SHA)
        old = json.loads((ROOT/FREEZE).read_text())
        clarification_path = ROOT/NEW_FREEZE
        self.assertEqual(hashlib.sha256(clarification_path.read_bytes()).hexdigest(),
                         '95c85537542df7747660c7917a0bcae580f06476e2f71c5b6945bc5434fe0885')
        clarification = json.loads(clarification_path.read_text())
        compound_path = ROOT/COMPOUND_FREEZE
        self.assertEqual(hashlib.sha256(compound_path.read_bytes()).hexdigest(),
                         'edf9f17986c783c83dba718ecdfdd705c99024c6d0e0882f619cf37609c377b2')
        compound = json.loads(compound_path.read_text())
        intent_path = ROOT/INTENT_LIMITS_FREEZE
        self.assertEqual(hashlib.sha256(intent_path.read_bytes()).hexdigest(),
                         '710bc2bf6bab2529b62cbbadcf0b2abc3e4c97fc8a406b00f35d18cc41ab3062')
        new = json.loads(intent_path.read_text())
        self.assertEqual(set(compound['files']), set(new['files']))
        self.assertEqual({path for path in new['files'] if new['files'][path]!=compound['files'][path]},
                         {'pal/primary.py'})
        self.assertEqual(set(clarification['files']), set(new['files']))
        self.assertEqual({path for path in new['files'] if new['files'][path]!=clarification['files'][path]},
                         {'pal/primary.py'})
        self.assertEqual(set(old['files']), set(new['files']))
        self.assertEqual({path for path in old['files'] if old['files'][path]!=new['files'][path]},
                         {'pal/primary.py'})
        self.assertEqual(new['heldout_sha256'], COHORTS['intent-limits-heldout'][1])
        self.assertFalse(new['heldout_contents_opened_before_freeze'])
        expert_path = 'evidence/reviews/judgment-boundary/expert-commitment-candidate-freeze.json'
        self.assertEqual(hashlib.sha256((ROOT/expert_path).read_bytes()).hexdigest(),
                         '1bf45e0fe170d05433570026d7131b5f454e7a85075a554787a85d0e06e13691')
        expert = json.loads((ROOT/expert_path).read_text())
        self.assertEqual(set(expert['files']), set(new['files']))
        self.assertEqual({path for path in new['files'] if new['files'][path]!=expert['files'][path]},
                         {'pal/runtime.py'})
        self.assertEqual(hashlib.sha256((ROOT/ASK_FIRST_FREEZE).read_bytes()).hexdigest(),
                         '3ed3c7d7e32b080313695d3bcfa4c5d3163251c05ba481ff74bb312af522145e')
        current = json.loads((ROOT/ASK_FIRST_FREEZE).read_text())
        self.assertEqual(set(current['files']), set(expert['files']))
        self.assertEqual({path for path in current['files']
                          if current['files'][path]!=expert['files'][path]}, {'pal/primary.py'})
        self.assertEqual(current['heldout_sha256'], COHORTS['ask-first-heldout'][1])
        self.assertFalse(current['heldout_contents_opened_before_freeze'])
        self.assertEqual(hashlib.sha256((ROOT/GROUNDING_FREEZE).read_bytes()).hexdigest(),
                         '0161c50a0d80dc0aed8b7d69b7dbcef266e530344d5d545c1029bc8ab80a1e29')
        grounding = json.loads((ROOT/GROUNDING_FREEZE).read_text())
        self.assertEqual(set(grounding['files']), set(current['files']))
        self.assertEqual({path for path in grounding['files']
                          if grounding['files'][path]!=current['files'][path]}, {'pal/primary.py'})
        self.assertEqual(grounding['heldout_sha256'], COHORTS['grounding-heldout'][1])
        self.assertFalse(grounding['heldout_contents_opened_before_freeze'])
        trial = validate_freeze(ROOT, 'evidence/reviews/two-hour-trial/candidate-freeze.json')
        self.assertEqual(set(trial['files']), set(grounding['files']))
        self.assertEqual({path for path in trial['files']
                          if trial['files'][path]!=grounding['files'][path]},
                         {'pal/native.py','pal/server.py','pal/web/app.js'})
        with self.assertRaises(RunRejected):validate_freeze(ROOT, GROUNDING_FREEZE)
        with self.assertRaises(RunRejected):validate_freeze(ROOT, ASK_FIRST_FREEZE)
        with self.assertRaises(RunRejected):validate_freeze(ROOT, expert_path)
        with self.assertRaises(RunRejected):validate_freeze(ROOT, FREEZE)
        with self.assertRaises(RunRejected):validate_freeze(ROOT, NEW_FREEZE)
        with self.assertRaises(RunRejected):validate_freeze(ROOT, COMPOUND_FREEZE)
        with self.assertRaises(RunRejected):validate_freeze(ROOT, INTENT_LIMITS_FREEZE)


if __name__=='__main__':
    unittest.main()
