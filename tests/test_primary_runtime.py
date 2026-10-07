import concurrent.futures
import json
import tempfile
import threading
import time
import subprocess
import sys
import unittest
from pathlib import Path

from pal.runtime import Runtime, MockProvider
from pal.store import Store, Conflict


def value(kind='none',reply='理解しました。',**kwargs):
    return json.dumps({'reply':reply,'action':dict(kind=kind,**kwargs)},ensure_ascii=False)


class PrimaryProvider(MockProvider):
    def __init__(self,action=None,block=False,fail=False):
        super().__init__()
        self.prompts=[]
        self.action=action or (lambda context:value())
        self.block=block
        self.fail=fail
        self.started=threading.Event()
        self.release=threading.Event()

    def complete(self,prompt):
        self.prompts.append(prompt)
        if not prompt.startswith('PRIMARY\n'):
            return super().complete(prompt)
        self.started.set()
        if self.block and not self.release.wait(4): raise TimeoutError('fixture barrier')
        if self.fail: raise RuntimeError('fixture failure')
        context=json.loads(prompt.split('\nINPUT_JSON\n',1)[1])
        return self.action(context)

    def stop(self):
        self.release.set()
        super().stop()


class PrimaryRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'state.db'

    def start(self,provider):
        runtime=Runtime(self.path,provider=provider)
        self.addCleanup(runtime.close)
        return runtime

    def test_every_ordinary_input_uses_one_primary_call_without_regex_preemption(self):
        provider=PrimaryProvider()
        runtime=self.start(provider)
        for i,text in enumerate(('Make a draft','stop that','answer: Sunday','remember my color','forget that','一時停止して','これを送って')):
            ack=runtime.submit(str(i),text)
            self.assertIn('primary_status',ack)
            self.assertEqual(ack['response'].result(2)['content'],'理解しました。')
            self.assertEqual(runtime.store.operation(str(i))['result']['primary_status'],'complete')
        self.assertEqual(len(provider.prompts),7)
        self.assertTrue(all(p.startswith('PRIMARY\n') for p in provider.prompts))
        state=runtime.store.inspect()
        self.assertFalse(state['goals'])
        self.assertFalse(state['notes'])
        self.assertTrue(all(r['usable'] for r in state['records']))

    def test_concurrent_same_key_is_one_inference_and_immediate_explicit_cancel(self):
        provider=PrimaryProvider(block=True)
        runtime=self.start(provider)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as workers:
            results=list(workers.map(lambda _:runtime.submit('one','相談です'),range(6)))
        self.assertTrue(provider.started.wait(1))
        self.assertTrue(all(r['response'] is results[0]['response'] for r in results))
        self.assertEqual(runtime.store.operation('one')['status'],'pending')
        goal=runtime.store.create_goal('synthetic','draft',{'kind':'local_draft','max_bytes':4096})
        # Store fixture is queued; no worker wake is issued before explicit cancellation.
        before=time.monotonic()
        ack=runtime.submit('cancel','中止',goal_id=goal['id'],control={'action':'cancel'})
        self.assertEqual(ack['goal']['state'],'cancelled')
        self.assertTrue(ack['response'].done())
        self.assertLess(time.monotonic()-before,0.5)
        self.assertEqual(len(provider.prompts),1)
        provider.release.set()
        results[0]['response'].result(2)
        self.assertEqual(runtime.submit('one','相談です')['response'].result(1)['id'],results[0]['response'].result()['id'])
        with self.assertRaises(Conflict):runtime.submit('one','別の内容')

    def test_provider_failure_is_visible_and_same_key_never_retries_or_creates_goal(self):
        provider=PrimaryProvider(fail=True)
        runtime=self.start(provider)
        first=runtime.submit('failure','Make a draft')['response'].result(2)
        self.assertIn('反映できません',first['content'])
        self.assertFalse(runtime.store.inspect()['goals'])
        self.assertEqual(runtime.store.operation('failure')['result']['primary_status'],'rejected')
        runtime.close()
        runtime=self.start(provider)
        self.assertEqual(runtime.submit('failure','Make a draft')['response'].result(1),first)
        self.assertEqual(len(provider.prompts),1)

    def test_natural_answer_targets_nonlatest_question_with_original_text(self):
        store=Store(self.path)
        goals=[]
        for name in ('A','B'):
            goal=store.create_goal('g'+name,'draft '+name,{'kind':'local_draft','max_bytes':4096})
            attempt=store.claim()
            store.request_clarification(attempt['id'],'When for '+name+'?')
            goals.append(store.get_goal(goal['id']))
        provider=PrimaryProvider(action=lambda context:value('answer',question_id=goals[0]['question_id']))
        runtime=self.start(provider)
        ack=runtime.submit('answer','Aは来週火曜日でお願いします。')
        ack['response'].result(2)
        state=runtime.store.inspect()
        question=next(q for q in state['questions'] if q['id']==goals[0]['question_id'])
        self.assertEqual(question['answer_record_id'],ack['record_id'])
        self.assertEqual(runtime.store.get_goal(goals[1]['id'])['state'],'waiting_input')
        self.assertEqual(len(state['goals']),2)

    def test_primary_clarifies_then_hands_context_to_one_expert(self):
        def choose(context):
            original=next(r for r in context['records'] if r['id']==context['input_record_id'])
            if original['content']=='招待文を用意して':
                return value(reply='誰への、何の招待ですか？')
            return value('local_draft',spec='友人への土曜の食事の招待文',source_ids=[context['input_record_id']])
        runtime=self.start(PrimaryProvider(action=choose))
        runtime.submit('question','招待文を用意して')['response'].result(2)
        self.assertFalse(runtime.store.inspect()['goals'])
        runtime.submit('details','友人を土曜の食事に招待します')['response'].result(2)
        outcome=runtime.store.operation('details')['result']
        self.assertEqual(outcome['intent'],'draft')
        self.assertIsNotNone(outcome['goal'])
        self.assertTrue(runtime.idle.wait(2))
        self.assertEqual(len(runtime.store.inspect()['goals']),1)
        self.assertEqual(len(runtime.store.inspect()['receipts']),1)

    def test_explicit_control_with_max_length_key_commits_reply_and_effect_once(self):
        runtime=self.start(PrimaryProvider())
        self.assertTrue(runtime.idle.wait(2))
        goal=runtime.store.create_goal('fixture','draft',{'kind':'local_draft','max_bytes':4096})
        result=runtime.submit('k'*200,'cancel',goal_id=goal['id'],control={'action':'cancel','epoch':goal['epoch']})
        self.assertEqual(result['goal']['state'],'cancelled')
        self.assertTrue(result['response'].done())
        again=runtime.submit('k'*200,'cancel',goal_id=goal['id'],control={'action':'cancel','epoch':goal['epoch']})
        self.assertEqual(result['response'].result(),again['response'].result())
        self.assertFalse(runtime.provider.prompts)

    def test_terminal_replay_after_forget_never_returns_cached_source_content(self):
        runtime=self.start(PrimaryProvider(action=lambda c:value(reply='The source said Friday.')))
        source=runtime.store.record('source','user','Friday')
        first=runtime.submit('reply','何曜日でしたか')['response'].result(2)
        self.assertIn('Friday',first['content'])
        runtime.submit('forget','forget source',control={'source_id':source['id']})
        second=runtime.submit('reply','何曜日でしたか')['response'].result(2)
        self.assertEqual(second,runtime.store.stored_reply('reply'))
        self.assertNotIn('Friday',second['content'])
        self.assertEqual(len(runtime.provider.prompts),1)

    def test_killed_primary_never_replays_model_after_restart(self):
        code='''import os,signal,sys,threading,json
from pathlib import Path
from pal.runtime import Runtime,MockProvider
class Spy(MockProvider):
    def complete(self,prompt):
        Path(sys.argv[3]).write_text('called')
        return json.dumps({'reply':'proposal','action':{'kind':'local_draft','spec':'draft','source_ids':[]}})
def die(point):
    if point==sys.argv[2]:
        os.kill(os.getpid(),signal.SIGKILL)
        # A worker can resume after kill(2) returns but before process termination.
        threading.Event().wait()
r=Runtime(sys.argv[1],provider=Spy(),fault=die)
r.submit('turn','actual input')
threading.Event().wait(4)
'''
        for point in ('primary.before_model','primary.after_model_before_apply'):
            with self.subTest(point=point):
                path=Path(self.temp.name)/(point+'.db')
                marker=Path(self.temp.name)/(point+'.called')
                child=subprocess.run([sys.executable,'-c',code,str(path),point,str(marker)],capture_output=True,timeout=6)
                self.assertEqual(child.returncode,-9,child.stderr)
                self.assertEqual(marker.exists(),point=='primary.after_model_before_apply')
                provider=PrimaryProvider()
                runtime=Runtime(path,provider=provider)
                try:
                    response=runtime.submit('turn','actual input')['response'].result(1)
                    self.assertIn('中断',response['content'])
                    self.assertFalse(provider.prompts)
                    self.assertFalse(runtime.store.inspect()['goals'])
                    self.assertEqual(runtime.store.operation('turn')['result']['primary_status'],'interrupted')
                finally:runtime.close()

    def test_target_clarification_and_correction_commit_crashes_never_rerun_primary(self):
        code='''import os,signal,sys,threading,json
from pathlib import Path
from pal.runtime import Runtime,MockProvider
class Spy(MockProvider):
    def complete(self,prompt):
        if not prompt.startswith('PRIMARY\\n'):raise AssertionError('unexpected worker before crash')
        Path(sys.argv[3]).write_text('one Primary call')
        if sys.argv[4]=='none':
            action={'kind':'none'};reply='AとBのどちらの案内ですか？'
        else:
            action={'kind':'control','op':'correct','goal_id':sys.argv[5],
                    'spec':'Aの日曜案内','source_ids':[sys.argv[6]]};reply='修正します。'
        return json.dumps({'reply':reply,'action':action},ensure_ascii=False)
def die(point):
    if point==sys.argv[2]:os.kill(os.getpid(),signal.SIGKILL)
r=Runtime(sys.argv[1],provider=Spy())
r.store.fault=die
r.submit('turn',sys.argv[7])
threading.Event().wait(5)
'''
        for kind in ('none','correct'):
            for point in ('primary_finish.before_commit','primary_finish.after_commit'):
                with self.subTest(kind=kind,point=point):
                    path=Path(self.temp.name)/(kind+'-'+point+'.db')
                    marker=path.with_suffix('.called')
                    store=Store(path);goals=[];sources=[]
                    for name in ('A','B'):
                        source=store.record('source'+name,'user',name+'の案内は土曜日です。')
                        goal=store.create_goal('goal'+name,name+'の土曜案内',
                                               {'kind':'local_draft','max_bytes':4096},[source['id']])
                        store.control('pause'+name,goal['id'],'pause')
                        goals.append(store.get_goal(goal['id']));sources.append(source['id'])
                    text='その案内を短くして。' if kind=='none' else 'Aの案内だけ日曜日に変えて。'
                    child=subprocess.run([sys.executable,'-c',code,str(path),point,str(marker),kind,
                                          goals[0]['id'],sources[0],text],capture_output=True,timeout=7)
                    self.assertEqual(child.returncode,-9,child.stderr)
                    self.assertEqual(marker.read_text(),'one Primary call')
                    provider=PrimaryProvider();runtime=Runtime(path,provider=provider)
                    try:
                        first=runtime.submit('turn',text)['response'].result(2)
                        self.assertTrue(runtime.idle.wait(2))
                        committed=point.endswith('after_commit')
                        outcome=runtime.store.operation('turn')['result']
                        self.assertEqual(outcome['primary_status'],'complete' if committed else 'interrupted')
                        self.assertFalse(any(p.startswith('PRIMARY\n') for p in provider.prompts))
                        state=runtime.store.inspect()
                        self.assertEqual(len(state['goals']),2)
                        self.assertEqual(runtime.store.get_goal(goals[1]['id']),goals[1])
                        self.assertEqual(len(state['primary_turns']),1)
                        self.assertEqual(sum(r['id']==outcome['response_id'] for r in state['records']),1)
                        if kind=='none':
                            self.assertEqual(state['goals'],goals)
                            self.assertEqual(first['content']=='AとBのどちらの案内ですか？',committed)
                            self.assertFalse(state['questions'])
                            self.assertFalse(runtime.store.selections())
                            self.assertFalse(provider.prompts)
                        else:
                            target=runtime.store.get_goal(goals[0]['id'])
                            self.assertEqual(target['revision'],2 if committed else 1)
                            self.assertEqual(target['acceptance_id'],goals[0]['acceptance_id'])
                            self.assertEqual(sum(e['kind']=='goal.correct' for e in state['events']),int(committed))
                            revisions=[r for r in state['revisions'] if r['goal_id']==target['id']]
                            if committed:
                                self.assertEqual(revisions[-1]['criteria'],revisions[0]['criteria'])
                                self.assertEqual(set(json.loads(revisions[-1]['sources'])),
                                                 {sources[0],outcome['record_id']})
                        again=runtime.submit('turn',text)['response'].result(1)
                        self.assertEqual(again,first)
                        self.assertEqual(runtime.store.inspect(),state)
                        self.assertFalse(any(p.startswith('PRIMARY\n') for p in provider.prompts))
                    finally:runtime.close()


if __name__=='__main__':unittest.main()
