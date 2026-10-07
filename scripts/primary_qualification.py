"""Finite Primary-only measurement; no workers, run resume or human attestation."""
import argparse
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

from pal.native import AccessProof, ProviderUnavailable, native_environment
from pal.primary import decode_primary, primary_prompt
from pal.sanitize import sanitize
from pal.store import Store
from scripts.live_evidence import EvidenceJournal, RunWatchdog, verify_journal
from scripts.live_operator import AuditedNative, clean_candidate
from scripts.live_runner import RunRejected, SourcePin

FIXTURE = 'evidence/reviews/judgment-boundary/primary-heldout.json'
FREEZE = 'evidence/reviews/judgment-boundary/primary-candidate-freeze.json'
FIXTURE_SHA = '523d6b859e67d9f84162cdf6299e12a835c8ba920724442b68df3b81c9fe62a0'
COHORTS = {
    'heldout-v1': (FIXTURE, FIXTURE_SHA),
    'remaining-after-c031': ('evidence/reviews/judgment-boundary/primary-remaining.json',
                             '34baf6e4969d8e1d0e6fb36bd1fe86721e6364cf958524f556fc3ea3f474351d'),
    'unseen-plus-contrasts': ('evidence/reviews/judgment-boundary/primary-unseen-contrasts.json',
                             '39046068664082dcbd1afb0aace9425b79da44a0a7298ff4e9a501ae28c28608'),
    'recognition-r01-r08': ('evidence/reviews/judgment-boundary/recognition-r01-r08.json',
                           'ffc83ef138739495bf31ba37991b43ddd226d3f1429f854b46c2885d15f16e23'),
    'recognition-r09-r16': ('evidence/reviews/judgment-boundary/recognition-r09-r16.json',
                           'fea4c3df865c9a32e9f2c37cb3286d65c152b07a8317170d8c79379c2ec05e91'),
    'recognition-n01-n24': ('evidence/reviews/judgment-boundary/recognition-n01-n24.json',
                           '9ae4c340caf6d2795b75565a530704885b9a7fe1fd72be5e9e07919d7650138a'),
}
ORACLE_FIELDS = ('PAL_ORACLE_ONLY','acceptable_outcome_set','required_observations',
                 'disallowed_effects','interpretation_reason','target_ref','only_if_prior_action')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_matrix(path, expected_sha=FIXTURE_SHA):
    raw = Path(path).read_bytes()
    if digest(raw) != expected_sha:
        raise RunRejected('frozen corpus changed')
    return json.loads(raw)


def validate_matrix(matrix):
    """Check the frozen measurement envelope before files, proof or native owner."""
    max_calls = matrix.get('max_primary_calls',24)
    if type(max_calls) is not int or max_calls not in (16,24):
        raise RunRejected('unsupported cohort call bound')
    recognition = matrix.get('recognition_regression',False)
    if type(recognition) is not bool:
        raise RunRejected('invalid recognition scope')
    cases = matrix['cases']
    if not cases or len({c['id'] for c in cases})!=len(cases):
        raise RunRejected('empty or duplicate cohort cases')
    if sum(len(c['turns']) for c in cases)>max_calls:
        raise RunRejected('worst-case cohort calls exceed bound')
    for case in cases:
        turns = case['turns']
        if recognition and (case['setup']['goals'] or not 1<=len(turns)<=2):
            raise RunRejected('recognition fixture must start without Goals')
        for ti,turn in enumerate(turns):
            expected = turn['acceptable_outcome_set']
            if not expected or any('goal_count' in e and
                    (type(e['goal_count']) is not int or e['goal_count'] not in (0,1)) for e in expected):
                raise RunRejected('invalid frozen Goal count')
            if 'only_if_prior_action' not in turn:
                continue
            first_kinds = {e['action_kind'] for e in turns[0]['acceptable_outcome_set']}
            if (not recognition or case['id'].startswith('N') or ti!=1 or len(turns)!=2 or
                    turn['only_if_prior_action']!='none' or
                    not first_kinds or not first_kinds<={'none','local_draft'} or
                    {e['action_kind'] for e in expected}!={'local_draft'} or
                    not isinstance(turn['user_text'],str) or not turn['user_text'].strip()):
                raise RunRejected('invalid conditional answer')
    return max_calls


def cohort_matrix(root, cohort):
    if cohort not in COHORTS:
        raise ValueError('unknown frozen qualification cohort')
    fixture, expected_sha = COHORTS[cohort]
    matrix = load_matrix(root/fixture,expected_sha)
    return fixture,matrix,validate_matrix(matrix)


class QualificationPin(SourcePin):
    def __init__(self, root, matrix):
        super().__init__(root,matrix)
        for path in sorted((root/'scripts').glob('primary_*.py')):
            self.hashes[str(path.relative_to(root))] = digest(path.read_bytes())
        self.hashes[FREEZE] = digest((root/FREEZE).read_bytes())

    def check(self):
        if QualificationPin(self.root,self.matrix).hashes != self.hashes:
            raise RunRejected('qualification source drift')


def seed_case(store, case):
    bindings = {}
    setup = case['setup']
    for source in setup['sources']:
        if source['usable'] is not True:
            raise RunRejected('unsupported unusable setup source')
        bindings[source['ref']] = store.record(source['ref'],source['role'],source['content'])['id']
    for note in setup.get('memory_notes',[]):
        if note['usable'] is not True:
            raise RunRejected('unsupported unusable setup note')
        bindings[note['ref']] = store.note(note['ref'],note['content'],
                                         [bindings[s] for s in note['source_refs']])['id']
    for goal in setup['goals']:
        ref = goal['ref']
        actual = store.create_goal(ref,goal['label'],goal['fixed_criteria'],
                                   [bindings[s] for s in goal['source_refs']])
        bindings[ref] = actual['id']
        state, epoch = goal['state'],goal['epoch']
        if goal['revision'] != 1 or state not in ('queued','paused','running','waiting_input'):
            raise RunRejected('unsupported fixture goal')
        cycles = epoch-1 if state in ('paused','running','waiting_input') else epoch
        for index in range(cycles):
            store.control(f'{ref}:pause:{index}',actual['id'],'pause')
            store.control(f'{ref}:resume:{index}',actual['id'],'resume')
        if state=='paused':
            store.control(ref+':paused',actual['id'],'pause')
        elif state in ('running','waiting_input'):
            attempt = store.claim()
            if attempt is None or attempt['goal_id'] != actual['id']:
                raise RunRejected('fixture claimed another Goal')
            if state=='waiting_input':
                question = next(q for q in setup['questions'] if q['goal_ref']==ref)
                actual = store.request_clarification(attempt['id'],question['text'])
                bindings[question['ref']] = actual['question_id']
    data = store.inspect()
    for expected in setup['goals']:
        goal = next(g for g in data['goals'] if g['id']==bindings[expected['ref']])
        revision = next(r for r in data['revisions'] if r['goal_id']==goal['id'])
        if (any(goal[k]!=expected[k] for k in ('state','epoch','revision')) or
                json.loads(revision['criteria'])!=expected['fixed_criteria'] or
                json.loads(revision['sources'])!=[bindings[s] for s in expected['source_refs']] or
                revision['specification']!=expected['label']):
            raise RunRejected('fixture Goal mismatch')
    for expected in setup['questions']:
        actual = next(q for q in data['questions'] if q['id']==bindings[expected['ref']])
        if (actual['goal_id']!=bindings[expected['goal_ref']] or actual['status']!='open' or
                actual['prompt']!=expected['text'] or
                any(actual[k]!=expected[k] for k in ('epoch','revision'))):
            raise RunRejected('fixture question mismatch')
    for expected in setup['sources']:
        actual = next(r for r in data['records'] if r['id']==bindings[expected['ref']])
        if actual['content']!=expected['content'] or actual['usable']!=1:
            raise RunRejected('fixture source mismatch')
    for expected in setup.get('memory_notes',[]):
        actual = next(n for n in data['notes'] if n['id']==bindings[expected['ref']])
        if (actual['content']!=expected['content'] or actual['usable']!=1 or
                json.loads(actual['sources'])!=[bindings[s] for s in expected['source_refs']]):
            raise RunRejected('fixture note mismatch')
    for field,table in (('latest_goal_ref','goals'),('latest_source_ref','records'),
                        ('latest_displayed_question_ref','questions')):
        if field in setup and data[table][-1]['id']!=bindings[setup[field]]:
            raise RunRejected('fixture ordering mismatch')
    return bindings


def verify_snapshot(store, context):
    data = store.inspect()
    usable = set(store.context()['manifest'])
    active = [g for g in data['goals'] if g['state'] not in ('completed','cancelled','unknown')]
    if len(active)>10 or context['goals_overflow']:
        raise RunRejected('unexpected fixture target overflow')
    expected = []
    for goal in active:
        revision = next(r for r in data['revisions'] if r['goal_id']==goal['id'] and r['revision']==goal['revision'])
        if set(json.loads(revision['sources']))<=usable:
            expected.append(goal)
    fields = ('id','state','revision','epoch','question_id')
    if {tuple(g[k] for k in fields) for g in context['goals']} != {tuple(g[k] for k in fields) for g in expected}:
        raise RunRejected('offered Goal snapshot differs from fixture')
    questions = [q for q in data['questions'] if q['status']=='open' and
                 any(g['id']==q['goal_id'] and g['question_id']==q['id'] and
                     g['epoch']==q['epoch'] and g['revision']==q['revision'] for g in expected)]
    if {q['id'] for q in context['questions']}!={q['id'] for q in questions}:
        raise RunRejected('offered question snapshot differs from fixture')
    if set(context['manifest'])!=usable:
        raise RunRejected('offered source manifest differs from fixture')


class PrimaryGate:
    def __init__(self, provider, sink, deadline, clock=time.monotonic, max_calls=24):
        if type(max_calls) is not int or max_calls not in (16,24):
            raise RunRejected('unsupported Primary gate bound')
        self.provider,self.sink,self.deadline,self.clock = provider,sink,deadline,clock
        self.max_calls = max_calls
        self.attempts = 0
        self._lock = threading.Lock()
        self._permit = None
        self._active = self.closed = False

    def close_run(self, reason):
        with self._lock:
            if self.closed: return
            self.closed = True
            self._permit = None
        try:
            self.provider.stop()
        finally:
            self.sink({'event':'run.closed','reason':reason,'attempts':self.attempts})

    def grant(self, case, turn, prompt):
        safe = sanitize(prompt)
        with self._lock:
            denied = (self.closed or self.clock()>=self.deadline or self.attempts>=self.max_calls or
                      self._active or self._permit is not None or not safe.startswith('PRIMARY\n'))
            if not denied:
                self._permit = (case,turn,digest(safe.encode('utf-8')))
        if denied:
            self.close_run('permit_denied')
            raise ProviderUnavailable('Primary permit denied')
        try:
            self.sink({'event':'permit.granted','case':case,'turn':turn,'prompt_sha256':self._permit[2]})
        except BaseException:
            self.close_run('permit_evidence_failed')
            raise

    def complete(self, prompt, record_response=None):
        raw = sanitize(prompt).encode('utf-8')
        with self._lock:
            permit = self._permit
            denied = (self.closed or self.clock()>=self.deadline or self.attempts>=self.max_calls or
                      self._active or permit is None or digest(raw)!=permit[2])
            if not denied:
                self._permit = None
                self._active = True
                self.attempts += 1
        if denied:
            self.close_run('unplanned_or_expired_call')
            raise ProviderUnavailable('Primary generation gate closed')
        event = {'case':permit[0],'turn':permit[1],'call_sequence':self.attempts}
        try:
            self.sink(dict(event,event='call.started',prompt_sha256=permit[2]))
            response = self.provider.complete(raw.decode('utf-8'))
            if record_response is not None:
                record_response(response)
            self.sink(dict(event,event='call.returned',response_sha256=digest(response.encode('utf-8')),
                           discarded=self.clock()>=self.deadline or self.closed))
            if self.clock()>=self.deadline or self.closed:
                raise ProviderUnavailable('Primary deadline at return')
            return response
        except BaseException as error:
            try:
                self.sink(dict(event,event='call.failed',error_type=type(error).__name__))
            finally:
                self.close_run('call_failed')
            raise
        finally:
            with self._lock:
                self._active = False


class QualificationRunner:
    def __init__(self, root, directory, provider, *, scope, candidate, cohort='heldout-v1'):
        self.root,self.directory = Path(root).resolve(),Path(directory).resolve()
        self.provider,self.scope = provider,scope
        self.journal = self.gate = self.watchdog = None
        self.closed = False
        self.stores,self.bindings,self.accepted = [],[],[]
        self.skipped,self.prior = [],{}
        self.index,self.pending = 0,None
        try:
            if scope not in ('scripted','live_synthetic'):
                raise ValueError('unsupported qualification scope')
            fixture,self.matrix,self.max_calls = cohort_matrix(self.root,cohort)
            if scope=='live_synthetic':
                if type(provider) is not AuditedNative or not provider._operator_ready or provider._runner_claimed:
                    raise ValueError('qualification requires one audited official owner')
                if provider.initial_slots!=self.max_calls:
                    raise RunRejected('native owner differs from cohort bound')
                provider.proof.check()
                provider._runner_claimed = True
            self.pin = QualificationPin(self.root,self.root/fixture)
            freeze = json.loads((self.root/FREEZE).read_text())
            if any(digest((self.root/p).read_bytes())!=sha for p,sha in freeze['files'].items()):
                raise RunRejected('product candidate differs from pre-disclosure freeze')
            self.directory.mkdir(mode=0o700,parents=False,exist_ok=False)
            self.journal = EvidenceJournal(self.directory/'journal.jsonl',scope)
            remaining = 900 if scope=='scripted' else 900-(time.time()-provider.proof.verified_at)
            if remaining<=0: raise ProviderUnavailable('proof expired before run')
            self.deadline = time.monotonic()+min(900,remaining)
            self.gate = PrimaryGate(provider,self.journal.append,self.deadline,max_calls=self.max_calls)
            if scope=='live_synthetic': provider.sink = self.journal.append
            self.watchdog = RunWatchdog(self.gate,self.deadline)
            self.watchdog.start()
            self.journal.append({'event':'run.opened','candidate':candidate,'hashes':self.pin.hashes,
                                 'cohort':cohort,'fixture':fixture,
                                 'product_candidate':freeze['candidate'],'provider':provider.identity,
                                 'proof_remaining_seconds':remaining,'deadline_monotonic':self.deadline,
                                 'max_attempts':self.max_calls,'resume':False,'faults_disabled':True,
                                 'planned_turns':[{'case':c['id'],'turn':ti+1,
                                    **({'only_if_prior_action':t['only_if_prior_action']}
                                       if 'only_if_prior_action' in t else {})}
                                    for c in self.matrix['cases'] for ti,t in enumerate(c['turns'])],
                                 'claim':'Primary semantics and host application only; no workers/UI/Expert/race/human proof',
                                 'human_evaluation':False})
            for case in self.matrix['cases']:
                store = Store(self.directory/(case['id']+'.sqlite'))
                mapping = seed_case(store,case)
                self.stores.append(store)
                self.bindings.append(mapping)
                self.journal.append({'event':'fixture.verified','case':case['id'],'bindings':mapping,
                                     'snapshot':store.inspect()})
            self.turns = [(i,t) for i,c in enumerate(self.matrix['cases']) for t in range(len(c['turns']))]
        except BaseException:
            self.close()
            raise

    def _check(self):
        if self.closed or self.gate.closed:
            raise RunRejected('qualification run closed')
        self.pin.check()

    def _has_reply(self, case_index, key):
        reply = self.stores[case_index].stored_reply(key)
        return (isinstance(reply,dict) and isinstance(reply.get('content'),str) and
                bool(reply['content'].strip()))

    def _blob(self, name, text):
        raw = text.encode('utf-8',errors='strict')
        if len(raw)>131072: raise RunRejected('evidence blob too large')
        fd = os.open(self.directory/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try: os.fsync(directory)
        finally: os.close(directory)
        return {'name':name,'sha256':digest(raw),'bytes':len(raw)}

    def run_next(self):
        self._check()
        if self.pending is not None or self.index>=len(self.turns):
            raise RunRejected('prior turn needs judgment or corpus exhausted')
        case_index,turn_index = self.turns[self.index]
        case = self.matrix['cases'][case_index]
        turn = case['turns'][turn_index]
        store,mapping = self.stores[case_index],self.bindings[case_index]
        key = 'qualification:'+turn['input_record_ref']
        stage,prepared = 'prepare',False
        try:
            if 'only_if_prior_action' in turn:
                prior = self.prior.get(case_index)
                if (prior is None or prior['action']!='none' or
                        not self._has_reply(case_index,prior['key'])):
                    raise RunRejected('conditional answer lacks judged actual reply')
            before = store.inspect()
            admission = store.prepare_primary(key,turn['user_text'])
            prepared = True
            if admission['primary_status']!='pending':
                raise RunRejected('qualification does not replay inference')
            mapping[turn['input_record_ref']] = admission['record_id']
            stage = 'context'
            context = store.primary_context(key)
            verify_snapshot(store,context)
            self.journal.append({'event':'snapshot.verified','case':case['id'],'turn':turn_index+1,
                                 'key':key,'input_record_id':admission['record_id'],
                                 'offered_goals':context['goals'],'offered_questions':context['questions'],
                                 'manifest':context['manifest'],'before':before})
            stage = 'prompt'
            prompt = primary_prompt(context)
            if any(field in prompt for field in ORACLE_FIELDS):
                raise RunRejected('oracle field in model prompt')
            if prompt!=sanitize(prompt):
                raise RunRejected('prompt would change at transport boundary')
            blob = self._blob(f'{case["id"]}-{turn_index+1}.prompt.txt',prompt)
            self.journal.append({'event':'prompt.built','case':case['id'],'turn':turn_index+1,'blob':blob})
            self.pin.check()
            self.gate.grant(case['id'],turn_index+1,prompt)
            stage = 'call'
            def preserve_response(raw):
                blob = self._blob(f'{case["id"]}-{turn_index+1}.response.txt',raw)
                self.journal.append({'event':'proposal.received','case':case['id'],'turn':turn_index+1,'blob':blob})
            raw = self.gate.complete(prompt,preserve_response)
            stage = 'decode'
            proposal = decode_primary(raw)
            stage = 'finish'
            self.pin.check()
            outcome = store.finish_primary(key,proposal)
            self.pending = {'case':case['id'],'turn':turn_index+1,'key':key,
                            'input':turn['user_text'],'proposal':proposal,'outcome':outcome,
                            'after':store.inspect(),'reply':store.stored_reply(key),'bindings':dict(mapping)}
            self.journal.append(dict(self.pending,event='turn.captured'))
            return self.pending
        except BaseException as error:
            try:
                if prepared and store.operation(key)['status']=='pending':
                    store.finish_primary(key,error=type(error).__name__)
                self.journal.append({'event':'turn.failed','case':case['id'],'turn':turn_index+1,
                                     'stage':stage,'error_type':type(error).__name__,
                                     'operation':store.operation(key)})
            finally:
                self.close()
            raise

    def judge(self, passed, rationale):
        self._check()
        if self.pending is None or type(passed) is not bool or not isinstance(rationale,str) or not rationale.strip():
            raise RunRejected('a captured turn and explicit controller judgment are required')
        ci,ti = self.turns[self.index]
        expected = self.matrix['cases'][ci]['turns'][ti]['acceptable_outcome_set']
        action = self.pending['proposal']['action']
        following = self.matrix['cases'][ci]['turns'][ti+1:ti+2]
        conditional = following and 'only_if_prior_action' in following[0]
        if passed:
            matched = any(action['kind']==e['action_kind'] and ('target_ref' not in e or
                          self.bindings[ci][e['target_ref']]==action.get('goal_id',action.get('question_id',action.get('source_id'))))
                          and ('goal_count' not in e or len(self.pending['after']['goals'])==e['goal_count'])
                          for e in expected)
            if (not matched or self.pending['outcome']['primary_status']!='complete' or
                    (self.matrix.get('recognition_regression',False) and len(self.pending['after']['goals'])>1)):
                raise RunRejected('controller PASS conflicts with action/target or host rejection')
            if conditional and action['kind']=='none' and not self._has_reply(ci,self.pending['key']):
                raise RunRejected('conditional answer requires actual stored reply')
        self.journal.append({'event':'turn.judged','case':self.pending['case'],'turn':self.pending['turn'],
                             'passed':passed,'rationale':rationale,'judge':'controller','human_evaluation':False})
        if passed:
            self.accepted.append((self.pending['case'],self.pending['turn']))
            self.prior[ci] = {'action':action['kind'],'key':self.pending['key']}
            self.index += 1
            if conditional and action['kind']=='local_draft':
                skipped = (self.pending['case'],ti+2)
                self.journal.append({'event':'turn.skipped','case':skipped[0],'turn':skipped[1],
                                     'prior_turn':ti+1,'prior_action':action['kind'],
                                     'only_if_prior_action':following[0]['only_if_prior_action']})
                self.skipped.append(skipped)
                self.index += 1
            self.pending = None
        else:
            self.close()
        return {'accepted':passed,'accepted_turns':len(self.accepted),
                'skipped_turns':len(self.skipped),'human_evaluation':False}

    def finish(self):
        self._check()
        if len(self.accepted)+len(self.skipped)!=len(self.turns) or self.pending is not None:
            raise RunRejected('qualification incomplete')
        result = {'event':'qualification.finished','accepted_turns':len(self.accepted),
                  'skipped_turns':len(self.skipped),'covered_cases':len({c for c,t in self.accepted+self.skipped}),
                  'attempts':self.gate.attempts,'human_evaluation':False}
        try: self.journal.append(result)
        finally: self.close()
        verify_run(self.directory)
        return result

    def close(self):
        if self.closed: return
        self.closed = True
        try:
            if self.gate is not None: self.gate.close_run('operator_closed')
            else: self.provider.stop()
        finally:
            try:
                if self.watchdog is not None: self.watchdog.close()
            finally:
                if self.journal is not None: self.journal.close()


def verify_run(directory):
    directory = Path(directory)
    records = verify_journal(directory/'journal.jsonl')
    for record in records:
        blob = record.get('blob')
        if blob is None: continue
        if Path(blob['name']).name!=blob['name']:
            raise RunRejected('invalid evidence blob name')
        fd = os.open(directory/blob['name'],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise RunRejected('invalid evidence blob type')
            raw = stream.read(131073)
        if len(raw)!=blob['bytes'] or len(raw)>131072 or digest(raw)!=blob['sha256']:
            raise RunRejected('evidence blob mismatch')
    plan = records[0].get('planned_turns') if records else None
    planned = {(t['case'],t['turn']):t for t in plan} if plan is not None else {}
    captures,passes,skips,judged_captures = {},{},{},{}
    for record in records:
        event = record['event']
        if event=='turn.captured':
            pair = (record['case'],record['turn'])
            if pair in captures:
                raise RunRejected('duplicate captured turn')
            captures[pair] = record
        elif event=='turn.judged' and record['passed']:
            pair = (record['case'],record['turn'])
            if pair not in captures or pair in passes:
                raise RunRejected('judgment lacks unique captured turn')
            passes[pair] = record
            judged_captures[pair] = captures[pair]
        elif event=='turn.skipped':
            pair = (record['case'],record['turn'])
            prior = (record['case'],record['prior_turn'])
            if (pair in skips or pair in passes or pair not in planned or prior not in passes or
                    record['turn']!=2 or record['prior_turn']!=1 or
                    record['only_if_prior_action']!='none' or
                    planned[pair].get('only_if_prior_action')!='none' or
                    record['prior_action']!='local_draft' or
                    judged_captures[prior]['proposal']['action']['kind']!='local_draft'):
                raise RunRejected('unjustified conditional skip')
            skips[pair] = record
    for record in records:
        if ((record.get('case'),record.get('turn')) in skips and record['event'] in
                ('snapshot.verified','prompt.built','permit.granted','call.started','call.returned',
                 'call.failed','proposal.received','turn.captured','turn.failed','turn.judged')):
            raise RunRejected('skipped turn has input or call evidence')
    finished = [r for r in records if r['event']=='qualification.finished']
    if plan is not None and finished:
        result = finished[0]
        calls = sum(r['event']=='call.started' for r in records)
        if (len(planned)!=len(plan) or set(passes)|set(skips)!=set(planned) or
                len(finished)!=1 or any(r['event']=='turn.judged' and not r['passed'] for r in records) or
                result['accepted_turns']!=len(passes) or result.get('skipped_turns',0)!=len(skips) or
                result['attempts']!=calls or calls>records[0]['max_attempts'] or
                result.get('covered_cases')!=len({case for case,turn in planned})):
            raise RunRejected('qualification completion lacks full justified coverage')
        lifecycle_events = ('prompt.built','permit.granted','call.started',
                            'proposal.received','call.returned','turn.captured')
        lifecycles = {pair:{event:[] for event in lifecycle_events} for pair in passes}
        for record in records:
            event = record['event']
            if event in ('call.failed','turn.failed'):
                raise RunRejected('completed qualification contains failed call')
            if event in lifecycle_events:
                pair = (record.get('case'),record.get('turn'))
                if pair not in lifecycles:
                    raise RunRejected('completed qualification contains unplanned call')
                lifecycles[pair][event].append(record)
        if calls!=len(passes):
            raise RunRejected('accepted turn lacks exactly one call')
        call_sequences = []
        for pair,events in lifecycles.items():
            if any(len(events[event])!=1 for event in lifecycle_events):
                raise RunRejected('incomplete or repeated successful call lifecycle')
            prompt,permit,start,proposal,returned,capture = [events[event][0] for event in lifecycle_events]
            order = [r['sequence'] for r in (prompt,permit,start,proposal,returned,capture,passes[pair],result)]
            if (order!=sorted(order) or
                    permit.get('prompt_sha256')!=prompt['blob']['sha256'] or
                    start.get('prompt_sha256')!=permit.get('prompt_sha256') or
                    returned.get('response_sha256')!=proposal['blob']['sha256'] or
                    returned.get('discarded') is not False or
                    type(start.get('call_sequence')) is not int or
                    returned.get('call_sequence')!=start.get('call_sequence')):
                raise RunRejected('successful call lifecycle binding mismatch')
            call_sequences.append(start['call_sequence'])
        if sorted(call_sequences)!=list(range(1,calls+1)):
            raise RunRejected('successful call sequence accounting mismatch')
    return {'records':len(records),'completed':any(r['event']=='qualification.finished' for r in records),
            'judged_turns':sum(r['event']=='turn.judged' for r in records),
            'skipped_turns':len(skips),'covered_cases':len({case for case,turn in passes|skips})
                if finished else 0,
            'scope':records[0]['scope'] if records else None,'human_evaluation':False}


def build_live(root, directory, proof_path, candidate, cohort='heldout-v1'):
    root,directory = Path(root).resolve(),Path(directory).resolve()
    directory.relative_to(root/'runtime')
    if directory.exists(): raise FileExistsError(directory)
    _,_,max_calls = cohort_matrix(root,cohort)
    clean_candidate(root,candidate)
    proof = AccessProof.load(proof_path)
    owner = AuditedNative(proof,max_calls=max_calls)
    try:
        command = owner.command()
        owner._frozen_command = list(command)
        version = subprocess.run([command[0],'--version'],capture_output=True,text=True,
                                 check=True,timeout=10,env=native_environment())
        if len(version.stdout.encode('utf-8'))>4096: raise ValueError('CLI version bound')
        proof.consume(root/'runtime/native-proof-use')
        owner._operator_ready = True
        runner = QualificationRunner(root,directory,owner,scope='live_synthetic',candidate=candidate,
                                     cohort=cohort)
    except BaseException:
        owner.stop()
        raise
    try:
        runner.journal.append({'event':'operator.config','command':command,'cli_version':version.stdout.strip(),
                               'python_version':sys.version,'native_slots':max_calls,
                               'access_proof':{'verified_at':proof.verified_at,'route':proof.route,'no_extra_charge':True},
                               'actual_model':'official Claude --model opus (service revision not exposed)',
                               'qwen_qualification':False,'human_evaluation':False})
    except BaseException:
        runner.close()
        raise
    return runner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify')
    parser.add_argument('--run-directory')
    parser.add_argument('--access-proof')
    parser.add_argument('--candidate')
    parser.add_argument('--cohort',choices=sorted(COHORTS))
    args = parser.parse_args()
    if args.verify:
        if args.run_directory or args.access_proof or args.candidate or args.cohort:
            parser.error('verify is read-only and takes no execution arguments')
        print(json.dumps(verify_run(args.verify)),flush=True)
        return
    if not all((args.run_directory,args.access_proof,args.candidate)):
        parser.error('run directory, proof and candidate are required')
    root = Path(__file__).resolve().parents[1]
    runner = build_live(root,args.run_directory,args.access_proof,args.candidate,args.cohort or 'heldout-v1')
    def interrupted(signum, frame):
        raise SystemExit('qualification interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    try:
        print(json.dumps({'ready':True,'scope':'live_synthetic','human_evaluation':False}),flush=True)
        for line in sys.stdin:
            request = json.loads(line)
            if request=={'action':'next'}:
                result = runner.run_next()
            elif set(request)=={'action','passed','rationale'} and request['action']=='judge':
                result = runner.judge(request['passed'],request['rationale'])
            elif request=={'action':'finish'}:
                print(json.dumps(runner.finish(),ensure_ascii=False),flush=True)
                return
            else:
                raise ValueError('unsupported qualification command')
            print(json.dumps(result,ensure_ascii=False),flush=True)
    finally:
        runner.close()


if __name__=='__main__':
    from scripts.primary_qualification import main as entry
    entry()
