import json
import concurrent.futures
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pal.store import Store, Conflict
from pal.primary import decode_primary


def proposal(kind='none', reply='了解しました。', **fields):
    return {'reply':reply, 'action':dict(kind=kind, **fields)}


class PrimaryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'state.db'
        self.store = Store(self.path)

    def prepare(self, key, text='この内容をお願いします。'):
        return self.store.prepare_primary(key, text)

    def finish(self, key, value=None, **kwargs):
        return self.store.finish_primary(key, value or proposal(), **kwargs)

    def pending_question(self, name='依頼A'):
        record = self.store.record('source:'+name, 'user', name)
        goal = self.store.create_goal('goal:'+name,name,{'kind':'local_draft','max_bytes':4096},[record['id']])
        attempt = self.store.claim()
        self.store.request_clarification(attempt['id'], '必要な日時を教えてください。')
        return self.store.get_goal(goal['id'])

    def test_closed_json_rejects_duplicates_authority_and_paraphrased_answer(self):
        self.assertEqual(decode_primary(json.dumps(proposal()))['action'], {'kind':'none'})
        bad = [
            '{"reply":"a","reply":"b","action":{"kind":"none"}}',
            json.dumps(proposal('answer',question_id='q',text='model paraphrase')),
            json.dumps(proposal('local_draft',spec='draft',source_ids=[],criteria={'kind':'shell'})),
            json.dumps(proposal('control',op='approve',goal_id='g')),
            json.dumps(proposal('remember',source_id='s',content='invented preference')),
            json.dumps(proposal('none',reply='\ud800')),
        ]
        for raw in bad:
            with self.subTest(raw=ascii(raw)), self.assertRaises(ValueError):
                decode_primary(raw)

    def test_admission_is_durable_and_same_key_conflicts_before_any_effect(self):
        for key in ([], {}, 1, None, '', 'x'*201):
            with self.subTest(key=key), self.assertRaises(ValueError): self.prepare(key)
        self.assertFalse(self.store.inspect()['records'])
        admission = self.prepare('one','original user input')
        self.assertEqual(self.store.operation('one')['status'],'pending')
        again = self.prepare('one','original user input')
        self.assertEqual(again['record_id'],admission['record_id'])
        with self.assertRaises(Conflict): self.prepare('one','different')
        with self.assertRaises(Conflict): self.store.record('one','user','other operation')
        with self.assertRaises(Conflict):
            self.store.ingress('one','original user input','draft')
        self.assertEqual(len(self.store.inspect()['records']),1)

    def test_draft_commit_reply_and_replay_are_one_atomic_outcome(self):
        admitted = self.prepare('draft','招待文を用意して。')
        value = proposal('local_draft',spec='短い招待文を準備する',source_ids=[admitted['record_id']])
        first = self.finish('draft',value)
        second = self.finish('draft',proposal('forget',source_id=admitted['record_id']))
        self.assertEqual(first,second)
        state = self.store.inspect()
        self.assertEqual(len(state['goals']),1)
        self.assertEqual(state['goals'][0]['state'],'queued')
        self.assertEqual(self.store.operation('draft')['result'],first)
        self.assertEqual(len(state['records']),2)
        self.assertIn('短い招待文',self.store.stored_reply('draft')['content'])
        self.assertEqual(self.prepare('draft','招待文を用意して。')['primary_status'],'complete')

    def test_none_and_fabricated_target_never_fall_back_to_latest_goal(self):
        goal = self.pending_question()
        self.prepare('chatter','answer: 今日は暑いですね')
        self.finish('chatter')
        self.assertEqual(self.store.get_goal(goal['id'])['state'],'waiting_input')
        self.prepare('fabricated')
        result = self.finish('fabricated',proposal('answer',reply='記録済みです。',question_id='invented'))
        self.assertEqual(result['primary_status'],'rejected')
        self.assertNotIn('記録済みです',self.store.stored_reply('fabricated')['content'])
        self.assertEqual(self.store.get_goal(goal['id'])['state'],'waiting_input')

    def test_answer_uses_original_ingress_and_binds_nonlatest_question_once(self):
        first = self.pending_question('A')
        second = self.pending_question('B')
        raw = 'Aの日時は、来週の火曜日です。'
        admitted = self.prepare('answer',raw)
        result = self.finish('answer',proposal('answer',question_id=first['question_id']))
        self.assertEqual(result['goal']['id'],first['id'])
        self.assertEqual(self.store.get_goal(second['id'])['state'],'waiting_input')
        q = next(q for q in self.store.inspect()['questions'] if q['id']==first['question_id'])
        self.assertEqual(q['answer_record_id'],admitted['record_id'])
        record = next(r for r in self.store.inspect()['records'] if r['id']==q['answer_record_id'])
        self.assertEqual(record['content'],raw)
        self.prepare('second-answer',raw)
        self.assertEqual(self.finish('second-answer',proposal('answer',question_id=q['id']))['primary_status'],'rejected')

    def test_cancel_and_forget_between_prepare_and_finish_reject_stale_result(self):
        goal = self.pending_question()
        admitted = self.prepare('answer')
        self.store.control('cancel',goal['id'],'cancel')
        self.assertEqual(self.finish('answer',proposal('answer',question_id=goal['question_id']))['primary_status'],'rejected')
        admitted = self.prepare('draft')
        self.store.forget('stop-source',admitted['record_id'])
        with self.assertRaises(ValueError): self.store.primary_context('draft')
        self.assertEqual(self.finish('draft',proposal('local_draft',spec='draft',source_ids=[]))['primary_status'],'rejected')
        self.assertEqual(len(self.store.inspect()['goals']),1)

    def test_expected_mid_effect_failure_rolls_back_before_rejection_is_saved(self):
        admitted = self.prepare('draft')
        def fail(point):
            if point=='create.mid_transaction': raise Conflict('injected after insert')
        self.store.fault = fail
        result = self.finish('draft',proposal('local_draft',spec='draft',source_ids=[admitted['record_id']]))
        self.assertEqual(result['primary_status'],'rejected')
        self.assertFalse(self.store.inspect()['goals'])
        self.assertFalse(self.store.inspect()['events'])

    def test_diagnostic_wait_not_in_snapshot_and_overflow_has_no_partial_target_set(self):
        goal = self.store.create_goal('g','draft',{'kind':'local_draft','max_bytes':4096})
        attempt = self.store.claim()
        self.store.fail(attempt['id'],'diagnostic wait','unverified')
        self.store.fail(self.store.claim()['id'],'diagnostic wait','unverified')
        self.prepare('ordinary')
        context = self.store.primary_context('ordinary')
        self.assertFalse(context['questions'])
        for n in range(10): self.store.create_goal('extra'+str(n),'draft',{'kind':'local_draft','max_bytes':4096})
        self.prepare('overflow')
        context = self.store.primary_context('overflow')
        self.assertTrue(context['goals_overflow'])
        self.assertFalse(context['goals'])
        result = self.finish('overflow',proposal('control',op='cancel',goal_id=goal['id']))
        self.assertEqual(result['primary_status'],'rejected')

    def test_correct_retains_fixed_criteria_and_source_bindings(self):
        goal = self.pending_question()
        source = self.store.record('detail','user','開催地は東京。')
        admitted = self.prepare('correct','大阪へ変更してください。')
        result = self.finish('correct',proposal('control',op='correct',goal_id=goal['id'],spec='大阪で開催する招待文',source_ids=[source['id']]))
        current = self.store.get_goal(goal['id'])
        self.assertEqual(result['primary_status'],'complete')
        self.assertEqual(current['acceptance_id'],goal['acceptance_id'])
        revision = self.store.inspect()['revisions'][-1]
        self.assertEqual(set(json.loads(revision['sources'])),{admitted['record_id'],source['id']})

    def test_remember_keeps_original_source_and_forget_stops_reference_without_purge(self):
        admitted = self.prepare('remember','好きな色は青です。')
        self.finish('remember',proposal('remember',source_id=admitted['record_id']))
        self.assertEqual(self.store.context()['notes'][0]['content'],'好きな色は青です。')
        self.prepare('forget','その色の記録は忘れて。')
        self.finish('forget',proposal('forget',source_id=admitted['record_id']))
        self.assertFalse(self.store.context()['notes'])
        self.assertNotIn(admitted['record_id'],self.store.context()['manifest'])
        self.assertTrue(any(r['id']==admitted['record_id'] for r in self.store.inspect()['records']))

    def test_recovery_interruption_and_provider_failure_are_terminal_without_retry(self):
        self.prepare('interrupted','original')
        self.store = Store(self.path)
        self.store.recover()
        self.assertEqual(self.prepare('interrupted','original')['primary_status'],'interrupted')
        self.assertEqual(self.store.operation('interrupted')['result']['primary_status'],'interrupted')
        self.assertIn('中断',self.store.stored_reply('interrupted')['content'])
        self.prepare('provider-failed')
        result = self.store.finish_primary('provider-failed',error='provider_unavailable')
        self.assertEqual(result['primary_status'],'rejected')
        self.assertEqual(self.prepare('provider-failed')['primary_status'],'rejected')
        self.assertFalse(self.store.inspect()['goals'])

    def test_primary_snapshot_has_no_content_and_long_keys_have_bounded_internal_keys(self):
        secret_text = 'private test content only'
        self.prepare('x'*200,secret_text)
        with self.store._connection() as db:
            snapshot = db.execute('SELECT snapshot FROM primary_turns').fetchone()[0]
        self.assertNotIn(secret_text,snapshot)
        self.finish('x'*200,proposal('local_draft',spec='draft',source_ids=[]))
        self.assertEqual(len(self.store.inspect()['goals']),1)
        self.assertNotIn('snapshot',self.store.inspect()['primary_turns'][0])

    def test_concurrent_admission_and_finish_publish_one_effect_and_reply(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as workers:
            admitted = list(workers.map(lambda _: self.prepare('parallel'), range(8)))
            self.assertEqual(len({row['record_id'] for row in admitted}), 1)
            value = proposal('local_draft',spec='one draft',source_ids=[])
            results = list(workers.map(lambda _: self.finish('parallel',value), range(8)))
        self.assertTrue(all(result == results[0] for result in results))
        state = self.store.inspect()
        self.assertEqual(len(state['goals']), 1)
        self.assertEqual(len(state['records']), 2)
        self.assertEqual(len(state['events']), 1)

    def test_real_process_deaths_do_not_leave_partial_effects_or_replay_inference(self):
        code = '''import os, signal, sys
from pal.store import Store
s = Store(sys.argv[1])
def die(point):
    if point == sys.argv[2]: os.kill(os.getpid(), signal.SIGKILL)
s.fault = die
if sys.argv[2].startswith('primary_prepare'):
    s.prepare_primary('turn','actual input')
else:
    s.finish_primary('turn',{'reply':'untrusted','action':{'kind':'local_draft','spec':'draft','source_ids':[]}})
'''
        for point in ('primary_prepare.before_commit','primary_prepare.after_commit',
                      'primary_finish.mid_transaction','primary_finish.before_commit','primary_finish.after_commit'):
            with self.subTest(point=point):
                path = Path(self.temp.name)/(point+'.db')
                store = Store(path)
                if point.startswith('primary_finish'):
                    store.prepare_primary('turn','actual input')
                before = store.inspect()
                child = subprocess.run([sys.executable,'-c',code,str(path),point],capture_output=True,timeout=10)
                self.assertEqual(child.returncode,-9,child.stderr)
                reopened = Store(path)
                if not point.endswith('after_commit'):
                    self.assertEqual(reopened.inspect(),before)
                reopened.recover()
                if point == 'primary_prepare.before_commit':
                    self.assertEqual(reopened.operation('turn')['status'],'absent')
                elif point == 'primary_finish.after_commit':
                    outcome = reopened.operation('turn')['result']
                    self.assertEqual(outcome['primary_status'],'complete')
                    self.assertEqual(reopened.finish_primary('turn'),outcome)
                    self.assertEqual(len(reopened.inspect()['goals']),1)
                    self.assertEqual(len(reopened.inspect()['records']),2)
                else:
                    self.assertEqual(reopened.operation('turn')['result']['primary_status'],'interrupted')
                    self.assertFalse(reopened.inspect()['goals'])
                with reopened._connection() as db:
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')


if __name__=='__main__': unittest.main()
