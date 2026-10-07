import hashlib
import json
import tempfile
import unittest
import urllib.request
from unittest.mock import patch
from pathlib import Path

from pal.runtime import MockProvider
from scripts.live_runner import MatrixRunner, RunRejected

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT/'tests/fixtures/p002_real_ui_v1.json'


class ScriptedNative(MockProvider):
    identity = 'scripted_matrix_fixture_only'
    def __init__(self, proposals):
        super().__init__(); self.proposals = iter(proposals); self.calls = []; self.stops = 0
    def complete(self, prompt):
        self.calls.append(prompt)
        return json.dumps(next(self.proposals),ensure_ascii=False)
    def stop(self): self.stops += 1
    def status(self): return {'mode':'scripted_matrix_fixture_only'}


def complete(text): return {'kind':'complete','content':text,'citations':[]}
def ask(text): return {'kind':'needs_input','question':text,'citations':[]}


class LiveRunnerTests(unittest.TestCase):
    def test_initial_evidence_failure_closes_real_watchdog_and_journal(self):
        from scripts.live_evidence import EvidenceJournal, RunWatchdog
        journals, watchdogs = [], []
        def journal_factory(*args):
            journal = EvidenceJournal(*args); journals.append(journal)
            self.addCleanup(journal.close)
            return journal
        def watchdog_factory(*args):
            watchdog = RunWatchdog(*args); watchdogs.append(watchdog)
            self.addCleanup(watchdog.close)
            return watchdog
        provider = ScriptedNative([])
        with tempfile.TemporaryDirectory() as directory, \
                patch('scripts.live_runner.EvidenceJournal', side_effect=journal_factory), \
                patch('scripts.live_runner.RunWatchdog', side_effect=watchdog_factory), \
                patch.object(EvidenceJournal, 'append', side_effect=OSError('injected startup write')):
            with self.assertRaisesRegex(OSError, 'injected startup write'):
                MatrixRunner(ROOT,Path(directory)/'run',MATRIX,provider,
                             scope='scripted',candidate='fixture')
            self.assertEqual(provider.stops, 1)
            self.assertEqual(provider.calls, [])
            self.assertEqual(journals[0]._fd, -1)
            self.assertFalse(watchdogs[0]._thread.is_alive())
            self.assertEqual((Path(directory)/'run/journal.jsonl').read_bytes(), b'')

    def test_fixture_assembly_cannot_claim_live_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                MatrixRunner(ROOT,Path(directory)/'run',MATRIX,ScriptedNative([]),
                             scope='live_synthetic',candidate='unverified')
            self.assertFalse((Path(directory)/'run').exists())

    def make(self, proposals):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        provider = ScriptedNative(proposals)
        runner = MatrixRunner(ROOT,Path(temp.name)/'run',MATRIX,provider,
                              scope='scripted',candidate='scripted-source-not-release')
        self.addCleanup(runner.close)
        return runner,provider

    def post(self, runner, text, goal=None):
        payload = {'key':'synthetic:'+runner.case['id']+':'+str(runner.phase),'text':text}
        if goal is not None:
            payload.update(goal_id=goal['id'],control={'action':'input','text':text,
                           'question_id':goal['question_id'],'epoch':goal['epoch']})
        request = urllib.request.Request(runner.url+'/api/message',
                    json.dumps(payload,ensure_ascii=False).encode(),
                    headers={'Content-Type':'application/json','Origin':runner.url},method='POST')
        with urllib.request.urlopen(request,timeout=3) as response:
            self.assertEqual(response.status,202)
            return json.load(response)

    def test_all_frozen_case_shapes_with_seed_forget_and_same_goal_answers(self):
        proposals = [complete('Mikaへ。10月12日18:00、架空の青葉会館へどうぞ。'),
                     ask('日時と場所を教えてください。'), complete('Mikaへ。10月12日18:00、架空の青葉会館へどうぞ。'),
                     complete('よろしければ集まりにご参加ください。'),
                     {'kind':'incomplete_preview','content':'日時 {{date}}、場所 {{place}}','missing':'{{date}} {{place}}','citations':[]},
                     ask('日時と場所は？'),ask('場所は？'),ask('場所はまだ不明ですか？'),
                     ask('確定した日時と場所は？')]
        runner,provider = self.make(proposals)
        expected_ids = [c['id'] for c in json.loads(MATRIX.read_text())['cases']]
        seen = []
        for case_id in expected_ids:
            info = runner.start_next(); self.assertEqual(info['case'],case_id); seen.append(case_id)
            ack = self.post(runner,runner.case['request']); first_goal = ack['goal']['id']
            while True:
                observation = runner.capture(timeout=3)
                self.assertEqual(observation['goal']['id'],first_goal)
                if observation['phase_complete']: break
                self.post(runner,observation['next_answer'],observation['goal'])
            if case_id=='K1': self.assertIn('青葉会館',provider.calls[0])
            if case_id=='F1':
                self.assertNotIn('10月12日',provider.calls[-1]); self.assertNotIn('青葉会館',provider.calls[-1])
                self.assertEqual(runner.runtime.store.inspect()['records'][0]['usable'],0)
            runner.accept_case('scripted fixture shape only, not real semantic or human proof',
                               'scripted HTTP observation only')
        self.assertEqual(seen,expected_ids)
        self.assertEqual(len(provider.calls),9)
        self.assertEqual(provider.stops,0)
        result = runner.finish()
        self.assertEqual(result['scope'],'scripted')
        self.assertFalse(result['human_evaluation'])
        self.assertEqual(provider.stops,1)
        self.assertEqual(len(set(x['db'] for x in runner.hosts)),6)

    def test_unexpected_case_shape_stops_without_another_generation(self):
        runner,provider = self.make([ask('unnecessary question')])
        runner.start_next(); self.post(runner,runner.case['request'])
        with self.assertRaises(RunRejected): runner.capture(timeout=3)
        self.assertEqual(len(provider.calls),1)
        self.assertEqual(provider.stops,1)
        with self.assertRaises(RunRejected): runner.start_next()

    def test_source_drift_is_detected_before_next_case(self):
        runner,provider = self.make([])
        runner.pin.hashes['pal/runtime.py'] = hashlib.sha256(b'wrong bytes').hexdigest()
        with self.assertRaises(RunRejected): runner.start_next()
        self.assertEqual(provider.calls,[])
        self.assertEqual(provider.stops,1)

    def test_case_cannot_advance_without_capture_and_controller_observation(self):
        runner,provider = self.make([complete('Mikaへ。10月12日18:00、架空の青葉会館へどうぞ。')])
        runner.start_next(); self.post(runner,runner.case['request'])
        with self.assertRaises(RunRejected): runner.accept_case('premature','no observation')
        self.assertEqual(provider.stops,1)
