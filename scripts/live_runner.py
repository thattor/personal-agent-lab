"""Finite matrix observer. Scripted results never establish live or human proof.

The controller performs inputs through the owned UI and explicitly accepts each
observed case. This module does not create access proofs or human evaluations.
"""
import hashlib
import json
import os
import threading
import time
from pathlib import Path

from pal.runtime import Runtime
from pal.server import make_server
from scripts.live_gate import GatedProvider
from scripts.live_evidence import EvidenceJournal, RunWatchdog, verify_journal


class RunRejected(RuntimeError):
    pass


def product_rel_paths(root):
    root = Path(root).resolve()
    if (root/'pal').is_symlink():
        raise RunRejected('product source is a symlink')
    paths = set(root.joinpath('pal').rglob('*.py')) | set(root.joinpath('pal/web').rglob('*'))
    files = set()
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise RunRejected('product source leaves checkout')
        if path.is_file():
            files.add(str(path.relative_to(root)))
    return files


class SourcePin:
    def __init__(self, root, matrix):
        self.root = root
        self.matrix = matrix
        paths = sorted({root/p for p in product_rel_paths(root)} |
                       set(root.joinpath('scripts').glob('live_*.py')) | {matrix})
        self.hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in paths if p.is_file()}

    def check(self):
        current = SourcePin(self.root, self.matrix)
        if current.hashes != self.hashes:
            raise RunRejected('source drift')


class MatrixRunner:
    def __init__(self, root, directory, matrix, provider, *, scope, candidate):
        self.root = Path(root).resolve()
        if scope not in ('scripted','live_synthetic'):
            raise ValueError('unsupported evidence scope')
        if scope=='live_synthetic':
            if Runtime.PRIMARY_PROTOCOL != 'legacy':
                raise ValueError('historical P002 matrix cannot qualify model-led Primary')
            # Only the operator-created audited owner may create live records.
            from scripts.live_operator import AuditedNative
            if (type(provider) is not AuditedNative or not provider._operator_ready
                    or provider._runner_claimed):
                raise ValueError('live scope requires audited official owner')
            provider.proof.check()
            provider._runner_claimed = True
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.matrix = json.loads(Path(matrix).read_text())
        if self.matrix['id'] != 'P002-LIVE-v1':
            raise ValueError('unsupported frozen matrix')
        self.pin = SourcePin(self.root, Path(matrix))
        self.scope = scope
        self.journal = EvidenceJournal(self.directory/'journal.jsonl', scope)
        self.deadline = time.monotonic()+self.matrix['limits']['wall_seconds']
        if scope=='live_synthetic':
            self.deadline = min(self.deadline,time.monotonic()+max(
                0,900-(time.time()-provider.proof.verified_at)))
        self.gate = GatedProvider(provider, self.journal.append, self.deadline,
                                  max_calls=self.matrix['limits']['total_provider_generations'])
        self.watchdog = RunWatchdog(self.gate, self.deadline)
        self.runtime = self.server = self.thread = None
        self.case = None
        self.phase = 0
        self.index = -1
        self.accepted = []
        self.hosts = []
        self.captured = False
        self.closed = False
        self.goal_id = None
        try:
            self.watchdog.start()
            self.journal.append({'event':'run.started','candidate':candidate,
                                 'hashes':self.pin.hashes,'pid':os.getpid(),
                                 'human_evaluation':False})
        except BaseException:
            self.close()
            raise

    def _check(self):
        if self.closed or self.gate.status()['run_gate_closed']:
            raise RunRejected('run closed')
        self.pin.check()

    def _reject(self, reason):
        self.gate.close_run(reason)
        raise RunRejected(reason)

    def _teardown_host(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(6)
            self.server = None
        if self.runtime is not None:
            self.runtime.close()
            self.runtime = None

    def start_next(self):
        try:
            self._check()
            if self.case is not None and self.case['id'] not in self.accepted:
                self._reject('prior case not accepted')
            self._teardown_host()
            self.index += 1
            if self.index >= len(self.matrix['cases']):
                self._reject('matrix exhausted')
            self.case = self.matrix['cases'][self.index]
            self.phase = 0
            self.captured = False
            self.goal_id = None
            db = self.directory/(self.case['id']+'.sqlite')
            self.runtime = Runtime(db, provider=self.gate)
            if 'given' in self.case:
                row = self.runtime.store.record('synthetic:seed','user',self.case['given'])
                if self.case['id'] == 'F1':
                    self.runtime.store.forget('synthetic:reference-stop',row['id'])
            self.server = make_server(self.runtime,0)
            self.url = 'http://127.0.0.1:'+str(self.server.server_address[1])
            self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
            self.thread.start()
            host = {'case':self.case['id'],'db':str(db),'url':self.url,
                    'pid':os.getpid(),'started_at':self.runtime.started_at}
            self.hosts.append(host)
            self.journal.append(dict(host,event='host.started'))
            self.gate.grant(self.case['id'],'0','DRAFT')
            return dict(host,request=self.case['request'])
        except Exception:
            self.gate.close_run('start_failed')
            raise

    def capture(self, timeout=30):
        try:
            self._check()
            if self.captured or self.runtime is None:
                self._reject('no uncaptured phase')
            end = min(time.monotonic()+timeout,self.deadline)
            while time.monotonic() < end:
                self._check()
                data = self.runtime.store.inspect()
                goals = data['goals']
                if len(goals) > 1:
                    self._reject('multiple goals')
                if goals and goals[0]['state'] in ('completed','failed','waiting_input'):
                    # Reply publication runs independently from task completion.
                    with self.runtime._reply_lock:
                        replies = list(self.runtime._responses.values())
                    if all(f.done() for f in replies):
                        break
                time.sleep(.01)
            else:
                self._reject('capture timeout')
            data = self.runtime.store.inspect()
            goal = data['goals'][0]
            if self.goal_id is not None and goal['id'] != self.goal_id:
                self._reject('answer changed goal')
            self.goal_id = goal['id']
            case = self.case['id']
            expected = ('completed' if case in ('K1','G1') or (case=='A1' and self.phase==1)
                        else 'failed' if case=='T1' or (case=='P1' and self.phase==2)
                        else 'waiting_input')
            questions = data['questions']
            answered = sum(q['status']=='answered' for q in questions)
            opened = sum(q['status']=='open' for q in questions)
            count = (0 if case in ('K1','G1','T1') else
                     min(self.phase+1,2) if case=='P1' else 1)
            if (goal['state'] != expected or len(questions)!=count or
                answered != self.phase or opened != (expected=='waiting_input')):
                self._reject('unexpected canonical question/state shape')
            receipts = data['receipts']
            terminal = expected in ('completed','failed')
            if len(receipts) != int(terminal):
                self._reject('unexpected receipt count')
            artifacts = []
            if terminal:
                receipt = receipts[0]
                body = self.runtime.store.artifact(receipt['artifact_id'])
                role = 'draft' if expected=='completed' else 'preview'
                if (receipt['role']!=role or hashlib.sha256(body).hexdigest()!=receipt['hash']
                    or len(body)!=receipt['size']):
                    self._reject('artifact receipt mismatch')
                outcomes = data['outcomes']
                if len([o for o in outcomes if o['check_status']=='pass']) != int(expected=='completed'):
                    self._reject('unexpected pass outcome')
                if (len(outcomes)!=1 or outcomes[0]['check_status'] !=
                        ('pass' if expected=='completed' else 'unverified')):
                    self._reject('unexpected outcome shape')
                if expected=='failed' and goal['reason'] != (
                        'incomplete_template' if case=='T1' else 'clarification_exhausted'):
                    self._reject('unexpected preview reason')
                artifacts.append({'receipt':receipt,'text':body.decode('utf-8'),
                                  'status':self.runtime.store.artifact_status(receipt['artifact_id'])})
            if case=='F1' and data['records'][0]['usable']!=0:
                self._reject('reference stop missing')
            if case=='F1':
                calls = [r for r in verify_journal(self.directory/'journal.jsonl')
                         if r['event']=='call.started' and r['case']=='F1']
                if len(calls)!=1 or any(v in calls[0]['prompt'] for v in ('10月12日','青葉会館')):
                    self._reject('stopped facts leaked into prompt')
            result = {'event':'phase.captured','case':case,'phase':self.phase,
                      'goal':goal,'snapshot':data,'artifacts':artifacts,
                      'phase_complete':terminal or case=='F1','human_evaluation':False}
            self.journal.append(result)
            if not result['phase_complete']:
                answers = self.case.get('answers',[self.case.get('answer')])
                result['next_answer'] = answers[self.phase]
                self.phase += 1
                self.gate.grant(case,str(self.phase),'DRAFT')
            else:
                self.captured = True
            return result
        except Exception:
            self.gate.close_run('capture_failed')
            raise

    def accept_case(self, rationale, browser_observation):
        self._check()
        if (not self.captured or not isinstance(rationale,str) or not rationale.strip()
            or not isinstance(browser_observation,str) or not browser_observation.strip()
            or self.case['id'] in self.accepted):
            self._reject('case lacks completed capture/controller observation')
        self.journal.append({'event':'case.accepted','case':self.case['id'],
                             'rationale':rationale,'browser_observation':browser_observation,
                             'human_evaluation':False})
        self.accepted.append(self.case['id'])

    def finish(self):
        self._check()
        if self.accepted != [c['id'] for c in self.matrix['cases']]:
            self._reject('matrix incomplete')
        self._teardown_host()
        self.pin.check()
        result = {'event':'matrix.finished','scope':self.scope,'cases':self.accepted,
                  'calls':self.gate.attempts,'human_evaluation':False}
        # Journal owns scope metadata; caller cannot supply the reserved key.
        self.journal.append({k:v for k,v in result.items() if k!='scope'})
        self.close()
        verify_journal(self.directory/'journal.jsonl')
        return result

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.gate.close_run('controller_teardown')
        finally:
            try:
                self.watchdog.close()
            finally:
                try:
                    self._teardown_host()
                finally:
                    self.journal.close()
