"""Real process deaths against disposable databases, never runtime-state repair."""
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from pal.store import Store, StaleResult

_CHILD = r'''
import os,signal,sys
from pal.store import Store
path, operation, boundary = sys.argv[1:]
store = Store(path)
def die(point):
    if point == operation + '.' + boundary:
        os.kill(os.getpid(), signal.SIGKILL)
store.fault = die
if operation == 'ingress':
    store.ingress('ingress','Make a draft','draft')
elif operation == 'create':
    store.create_goal('create', 'draft', {'kind':'local_draft','max_bytes':200})
elif operation == 'claim':
    store.claim()
elif operation == 'artifact':
    store.write_draft(store.inspect()['attempts'][0]['id'], 'Draft')
elif operation == 'complete':
    store.complete(store.inspect()['attempts'][0]['id'], store.inspect()['receipts'][0]['id'])
elif operation == 'control':
    store.control('cancel',store.inspect()['goals'][0]['id'],'cancel')
elif operation == 'deliver':
    store.deliver()
'''


class CrashTests(unittest.TestCase):
    def test_transaction_crash_matrix(self):
        for operation in ('ingress', 'create', 'claim', 'artifact', 'complete', 'control', 'deliver'):
            for boundary in ('mid_transaction', 'before_commit', 'after_commit'):
                with self.subTest(operation=operation, boundary=boundary), tempfile.TemporaryDirectory() as temp:
                    path = Path(temp) / 'state.db'
                    store = Store(path)
                    if operation not in ('create', 'ingress'):
                        store.create_goal('create', 'draft', {'kind':'local_draft','max_bytes':200})
                    if operation in ('artifact', 'complete', 'control'):
                        store.claim()
                    if operation == 'complete':
                        store.write_draft(store.inspect()['attempts'][0]['id'], 'Draft')
                    before = store.inspect()
                    child = subprocess.run([sys.executable, '-c', _CHILD, str(path), operation, boundary], capture_output=True, timeout=10)
                    self.assertEqual(child.returncode, -signal.SIGKILL, child.stderr.decode())
                    reopened = Store(path)
                    after = reopened.inspect()
                    if boundary != 'after_commit':
                        self.assertEqual(after, before)
                    if operation == 'create' and boundary == 'after_commit':
                        original = reopened.create_goal('create', 'draft', {'kind':'local_draft','max_bytes':200})
                        self.assertEqual(original['id'], after['goals'][0]['id'])
                        self.assertEqual(len(after['events']), 1)
                    if operation == 'claim' and boundary == 'after_commit':
                        stale_id = after['attempts'][0]['id']
                        reopened.recover()
                        self.assertEqual(reopened.get_goal(after['goals'][0]['id'])['state'], 'queued')
                        self.assertNotEqual(reopened.claim()['id'], stale_id)
                        with self.assertRaises(StaleResult):
                            reopened.write_draft(stale_id, 'Late')
                    if operation == 'artifact' and boundary == 'after_commit':
                        self.assertEqual(len(after['receipts']), 1)
                        self.assertEqual(len(after['artifacts']), 1)
                        self.assertEqual(reopened.artifact(after['artifacts'][0]['id']), b'Draft')
                    if operation == 'complete' and boundary == 'after_commit':
                        self.assertEqual(after['goals'][0]['state'], 'completed')
                        reopened.recover()
                        self.assertEqual(reopened.get_goal(after['goals'][0]['id'])['state'], 'completed')
                    reopened.deliver()
                    delivered = reopened.inspect()
                    reopened.deliver()
                    self.assertEqual(reopened.inspect(), delivered)
                    self.assertEqual(len([r for r in delivered['records'] if r['source_event_id']]), len(delivered['events']))
                    with reopened._connection() as db:
                        self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_process_death_after_executor_return_recovers_without_result_apply(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'state.db'
            store = Store(path)
            goal = store.create_goal('g', 'Make a draft', {'kind':'local_draft','max_bytes':200})
            code = """
import os,signal,sys,threading
from pal.runtime import Runtime
def die(point):
    if point == 'worker.after_executor_before_apply':
        os.kill(os.getpid(),signal.SIGKILL)
runtime=Runtime(sys.argv[1],fault=die)
threading.Event().wait(8)
"""
            child = subprocess.run([sys.executable,'-c',code,str(path)],capture_output=True,timeout=10)
            self.assertEqual(child.returncode,-signal.SIGKILL,child.stderr.decode())
            self.assertEqual(store.inspect()['receipts'],[])
            store.recover()
            self.assertEqual(store.get_goal(goal['id'])['state'],'queued')
            self.assertEqual(store.inspect()['attempts'][0]['status'],'abandoned')

    def test_pause_resume_and_input_crash_replay_exactly_once(self):
        for action in ('pause','resume','input'):
            for boundary in ('mid_transaction','before_commit','after_commit'):
                with self.subTest(action=action,boundary=boundary),tempfile.TemporaryDirectory() as temp:
                    path=Path(temp)/'state.db'
                    store=Store(path)
                    goal=store.create_goal('g','Make a draft',{'kind':'local_draft','max_bytes':200})
                    attempt=store.claim()
                    kwargs={}
                    if action=='resume':
                        store.control('pause',goal['id'],'pause')
                    elif action=='input':
                        waiting=store.waiting(attempt['id'],'Audience needed')
                        kwargs={'text':'Synthetic colleagues','question_id':waiting['question_id'],'epoch':waiting['epoch']}
                    before=store.inspect()
                    code="""
import os,signal,sys,json
from pal.store import Store
def die(point):
    if point=='control.'+sys.argv[4]:os.kill(os.getpid(),signal.SIGKILL)
s=Store(sys.argv[1],fault=die)
s.control('command',sys.argv[2],sys.argv[3],**json.loads(sys.argv[5]))
"""
                    child=subprocess.run([sys.executable,'-c',code,str(path),goal['id'],action,boundary,json.dumps(kwargs)],capture_output=True,timeout=10)
                    self.assertEqual(child.returncode,-signal.SIGKILL,child.stderr.decode())
                    reopened=Store(path)
                    if boundary!='after_commit':self.assertEqual(reopened.inspect(),before)
                    first=reopened.control('command',goal['id'],action,**kwargs)
                    second=reopened.control('command',goal['id'],action,**kwargs)
                    self.assertEqual(first,second)
                    matching=[e for e in reopened.inspect()['events'] if e['kind']=='goal.'+action]
                    self.assertEqual(len(matching),1)
