"""Independent PRI-owned binding/fault probes; actual owners, temporary DB only."""
import copy
import sqlite3
import unittest
from unittest.mock import patch
from pal.contracts_v5 import dumps,loads
import test_primary_host_v5 as fixtures

class CommitLossConnection(sqlite3.Connection):
    lose_admission=False
    admission_armed=False
    def execute(self,sql,parameters=()):
        result=super().execute(sql,parameters)
        if self.lose_admission and sql.startswith('INSERT INTO v5_pri_call'):
            self.admission_armed=True
        if sql=='COMMIT' and self.admission_armed:
            self.admission_armed=False;self.lose_admission=False
            raise sqlite3.OperationalError('PRIVATE_CANARY committed response lost')
        return result

class PrimaryBindingReview(unittest.TestCase):
    def fixture(self,fault_connection=False):
        f=fixtures.PrimaryHostTests()
        if fault_connection:
            connect=sqlite3.connect
            def fault_connect(*a,**kw):return connect(*a,**{**kw,'factory':CommitLossConnection})
            with patch.object(fixtures.sqlite3,'connect',side_effect=fault_connect):f.setUp()
        else:f.setUp()
        self.addCleanup(f.doCleanups)
        return f
    def unavailable_without_reply(self,f,turn):
        before=f.snapshot();result=f.host.get_turn({'turn_id':turn})
        f.error(result,'unavailable');self.assertEqual(f.snapshot(),before);self.assertEqual(len(f.calls),1)
    def test_terminal_turn_call_and_session_one_sided_corruption(self):
        mutations=[('v5_pri_turn','nonce','forged'),('v5_pri_call','id','forged-call'),
                   ('v5_pri_call','input_hash','0'*64),('v5_pri_call','reservation_id','foreign'),
                   ('v5_pri_call','status','admitted'),('v5_pri_session','runner','foreign')]
        for table,column,value in mutations:
            with self.subTest(table=table,column=column):
                f=self.fixture();turn=f.submit();f.run_turn(turn)
                if table=='v5_pri_session':f.conn.execute(f'UPDATE {table} SET {column}=?',(value,))
                else:f.conn.execute(f'UPDATE {table} SET {column}=? WHERE '+('id' if table=='v5_pri_turn' else 'turn_id')+'=?',(value,turn))
                self.unavailable_without_reply(f,turn)
    def test_saved_exposure_cannot_drop_stopped_uncited_source(self):
        f=self.fixture();optional=f.record('uncited body');turn=f.submit();f.run_turn(turn)
        raw=f.conn.execute('SELECT snapshot_json FROM v5_pri_turn WHERE id=?',(turn,)).fetchone()[0];meta=loads(raw)
        self.assertIn(optional,[i['ref'] for i in meta['exposure']]);meta['exposure']=[i for i in meta['exposure'] if i['ref']!=optional]
        f.conn.execute('UPDATE v5_pri_turn SET snapshot_json=? WHERE id=?',(dumps(meta),turn));f.stop(optional)
        self.unavailable_without_reply(f,turn)
    def test_stored_outcome_error_cannot_publish_raw_canary(self):
        f=self.fixture();f.host=f.make_host(invoke=lambda req:(_ for _ in ()).throw(RuntimeError('private')))
        turn=f.submit();f.run_turn(turn,'failed');row=f.conn.execute('SELECT outcome_json FROM v5_pri_turn WHERE id=?',(turn,)).fetchone()[0]
        out=loads(row);out['error']['message']='PRIVATE_CANARY stored error';f.conn.execute('UPDATE v5_pri_turn SET outcome_json=? WHERE id=?',(dumps(out),turn))
        result=f.host.get_turn({'turn_id':turn});self.assertNotIn('PRIVATE_CANARY',dumps(result));f.error(result,'unavailable')
    def test_committed_admission_reply_loss_never_enters_callback_or_leaves_admitted_terminal(self):
        f=self.fixture(True);turn=f.submit();f.conn.lose_admission=True
        out=f.ok(f.host.run_turn({'turn_id':turn}));self.assertEqual(out['status'],'failed');self.assertNotIn('reply',out)
        self.assertEqual(f.calls,[]);self.assertEqual(f.used(),1)
        row=f.conn.execute('SELECT status FROM v5_pri_call WHERE turn_id=?',(turn,)).fetchone();self.assertEqual(row,('not_entered',))
        before=f.snapshot();self.assertEqual(f.ok(f.host.run_turn({'turn_id':turn})),out);self.assertEqual(f.snapshot(),before);self.assertEqual(f.calls,[])
    def test_invalid_utf8_callback_is_known_returned_failed_no_reentry(self):
        f=self.fixture();entered=[]
        def invoke(req):entered.append(1);return '\ud800'
        f.host=f.make_host(invoke=invoke);turn=f.submit();out=f.ok(f.host.run_turn({'turn_id':turn}))
        self.assertEqual(out['status'],'failed');self.assertNotIn('reply',out)
        self.assertEqual(f.conn.execute('SELECT status FROM v5_pri_call WHERE turn_id=?',(turn,)).fetchone(),('returned',))
        before=f.snapshot();self.assertEqual(f.ok(f.host.run_turn({'turn_id':turn})),out);self.assertEqual(f.snapshot(),before);self.assertEqual(entered,[1])
    def test_applying_intent_one_sided_tamper_holds_without_owner_replay(self):
        f=self.fixture();f.proposal={'kind':'new_work','brief':f.draft()};create=f.tasks.create;effects=[]
        def lost(*a,**kw):effects.append(1);f.ok(create(*a,**kw));raise RuntimeError('private lost response')
        f.tasks.create=lost;turn=f.submit();f.run_turn(turn,'pending');row=f.conn.execute('SELECT intent_json FROM v5_pri_turn WHERE id=?',(turn,)).fetchone()[0]
        intent=loads(row);intent['reply']='forged reply';f.conn.execute('UPDATE v5_pri_turn SET intent_json=? WHERE id=?',(dumps(intent),turn));f.restart()
        before=f.snapshot();out=f.ok(f.host.recover_turns());self.assertIn(turn,out['held_turn_ids']);self.assertEqual(f.snapshot(),before);self.assertEqual(effects,[1]);self.assertEqual(len(f.calls),1)
    def test_c11_read_mutation_or_transaction_replacement_suppresses_reply(self):
        for mode in ('write','rollback_begin'):
            with self.subTest(mode=mode):
                f=self.fixture();turn=f.submit();f.run_turn(turn);read=f.mem.read
                def corrupt(request,**kw):
                    body=read(request,**kw)
                    if mode=='write':f.conn.execute("UPDATE v5_tsk_host SET used=used+1 WHERE kind='model'")
                    else:f.conn.execute('ROLLBACK');f.conn.execute('BEGIN')
                    return body
                f.mem.read=corrupt;before=f.snapshot();out=f.ok(f.host.get_turn({'turn_id':turn}))
                self.assertNotIn('reply',out);self.assertEqual(out['status'],'committed');self.assertEqual(f.snapshot(),before);self.assertFalse(f.conn.in_transaction);self.assertEqual(len(f.calls),1)
    def test_c11_read_write_failure_preserves_existing_caller_transaction(self):
        f=self.fixture();turn=f.submit();f.run_turn(turn);read=f.mem.read
        f.conn.execute('CREATE TABLE caller_owned(value)');f.conn.execute('BEGIN');f.conn.execute('INSERT INTO caller_owned VALUES(7)')
        def corrupt(request,**kw):
            body=read(request,**kw);f.conn.execute("UPDATE v5_tsk_host SET used=used+1 WHERE kind='model'");return body
        f.mem.read=corrupt;before=f.snapshot();out=f.ok(f.host.get_turn({'turn_id':turn}))
        self.assertNotIn('reply',out);self.assertEqual(out['status'],'committed');self.assertEqual(f.snapshot(),before)
        self.assertTrue(f.conn.in_transaction);self.assertEqual(f.conn.execute('SELECT * FROM caller_owned').fetchall(),[(7,)]);f.conn.execute('ROLLBACK')
