"""Real Runtime SIGKILL recovery against disposable scripted-provider stores."""
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from pal.runtime import Runtime
from pal.store import Store
from test_runtime_envelope import ScriptedProvider

_CHILD = r'''
import json,os,signal,sys,threading
from pal.runtime import Runtime,MockProvider
class AskProvider(MockProvider):
    def complete(self,prompt):
        if prompt.startswith('DRAFT\n'):
            return json.dumps({'kind':'needs_input','question':'Which date?','citations':[]})
        return super().complete(prompt)
runtime=Runtime(sys.argv[1],provider=AskProvider())
if not runtime.idle.wait(2): raise RuntimeError('initial idle timeout')
def die(point):
    if point==sys.argv[2]: os.kill(os.getpid(),signal.SIGKILL)
runtime.store.fault=die
runtime.submit('draft','Make a draft invitation')
threading.Event().wait(8)
'''


class RuntimeQuestionCrashTests(unittest.TestCase):
    def test_question_commit_and_rollback_resume_same_goal_after_process_death(self):
        for boundary in ('question.mid_transaction','clarification.before_commit','clarification.after_commit'):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'state.db'
                child=subprocess.run([sys.executable,'-c',_CHILD,str(path),boundary],capture_output=True,timeout=12)
                self.assertEqual(child.returncode,-signal.SIGKILL,child.stderr.decode())
                store=Store(path)
                state=store.inspect();goal_id=state['goals'][0]['id']
                committed=boundary.endswith('after_commit')
                self.assertEqual(len(state['questions']), int(committed))
                payloads=[] if committed else [{'kind':'needs_input','question':'Which date?','citations':[]}]
                payloads.append({'kind':'complete','content':'Invitation Saturday','citations':[]})
                runtime=Runtime(path,provider=ScriptedProvider(payloads))
                try:
                    self.assertTrue(runtime.idle.wait(3))
                    goal=runtime.store.get_goal(goal_id)
                    self.assertEqual(goal['state'],'waiting_input')
                    runtime.submit('answer','Saturday',goal_id=goal_id,control={
                        'action':'input','text':'Saturday','question_id':goal['question_id'],'epoch':goal['epoch']})
                    self.assertTrue(runtime.idle.wait(3))
                    state=runtime.store.inspect()
                    self.assertEqual(runtime.store.get_goal(goal_id)['state'],'completed')
                    self.assertEqual(len(state['goals']),1)
                    self.assertEqual(len(state['questions']),1)
                    self.assertEqual(len(state['receipts']),1)
                    self.assertEqual(sum(e['kind']=='goal.waiting_input' for e in state['events']),1)
                    self.assertEqual(sum(e['kind']=='goal.completed' for e in state['events']),1)
                    runtime.store.deliver();before=runtime.store.inspect();runtime.store.deliver()
                    self.assertEqual(runtime.store.inspect(),before)
                finally:
                    runtime.close()
