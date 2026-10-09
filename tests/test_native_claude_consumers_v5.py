"""Real disposable v5 owners with typed Claude fixture endings; no real-model claim."""
import copy,importlib,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from pal.contracts_v5 import dumps,loads
import native_claude_fixtures_v5 as f
import test_native_primary_host_v5 as primary_fixture
import test_native_expert_runner_v5 as expert_fixture
from native_expert_fixtures_v5 import NativeFixture
class ClaudeConsumerTests(unittest.TestCase):
 def primary(self):
  class Provider(primary_fixture.Provider):
   def __init__(self,owner):super().__init__(owner);self.profile=f.profile()
   def returned(self,request,attempt):return f.returned(request,self.profile,dumps({'reply':'fixture reply','proposal':self.proposal}),attempt)
  c=primary_fixture.NativePrimaryTests(methodName='runTest');self.addCleanup(c.doCleanups)
  with patch.object(primary_fixture,'Provider',Provider):c.setUp()
  return c
 def expert(self):
  c=expert_fixture.NativeExpertRunnerTests(methodName='runTest');c.setUp();self.addCleanup(c.doCleanups)
  class Provider(expert_fixture.FixtureProvider):
   def ending(self,request,attempt,text):return f.returned(request,self.profile,text,attempt)
  c.provider=Provider(c);c.provider.profile=f.profile();c.runner=c.Runner(c.boundary,c.mem,provider=c.provider,artifacts=c.art,verifier=c.ver);return c
 def test_primary_complete_replay_selected_profile_exact_no_extra_charge(self):
  c=self.primary();turn=c.submit();before=c.used();out=c.run_turn(turn);self.assertEqual(out,{'status':'committed','effect_refs':[],'reply':'fixture reply'});self.assertEqual(c.used(),before+1);self.assertEqual(c.run_turn(turn),out);self.assertEqual(len(c.provider.calls),1)
  row=c.conn.execute('SELECT profile_json,phase,ending_json FROM v5_pri_native').fetchone();self.assertEqual(loads(row[0])['id'],f.ID);self.assertEqual(row[1],'returned');self.assertEqual(loads(row[2])['model_id'],f.MODEL);self.assertEqual(loads(row[2])['evidence_kind'],'fixture')
 def test_primary_unknown_restart_no_refund_no_reinvoke(self):
  c=self.primary();c.provider.behavior=c.unknown;turn=c.submit();out=c.run_turn(turn);c.held(out);used=c.used();c.restart();c.ok(c.host.recover_turns());c.ok(c.tasks.finish_startup());c.held(c.run_turn(turn));self.assertEqual(c.used(),used);self.assertEqual(len(c.provider.calls),1);self.assertEqual(c.get(turn)['status'],'held')
 def test_primary_parser_failure_after_known_ending_never_repairs_or_reinfers(self):
  c=self.primary()
  def behavior(request,hook):
   attempt=copy.deepcopy(f.ATTEMPT);hook(attempt);return f.returned(request,c.provider.profile,'not JSON',attempt)
  c.provider.behavior=behavior;turn=c.submit();out=c.run_turn(turn);self.assertEqual(out['status'],'failed');self.assertNotIn('reply',out);self.assertEqual(c.run_turn(turn),out);self.assertEqual(len(c.provider.calls),1);self.assertEqual(c.conn.execute('SELECT phase FROM v5_pri_native').fetchone()[0],'returned')
 def test_expert_saved_output_and_replay_readback_are_fixture_not_mock(self):
  c=self.expert();c.ok(c.execute());self.assertEqual(c.current()['state'],'completed');refs=c.current()['current_artifact_refs'];self.assertEqual(len(refs),1);request=c.provider.requests[0];self.assertEqual(set(request),{'call_id','reservation_id','role','work_ref','messages','source_refs','output_kind'});self.assertEqual(c.call()['profile_id'],f.ID);self.assertEqual(c.call()['native_phase'],'returned');self.assertIs(c.call()['may_enter'],False)
  used=c.conn.execute("SELECT used FROM v5_tsk_usage WHERE goal=? AND kind='model'",(c.work['goal_id'],)).fetchone()[0]
  c.execute();self.assertEqual(len(c.provider.requests),1);self.assertEqual(c.current()['current_artifact_refs'],refs);self.assertEqual(c.conn.execute("SELECT used FROM v5_tsk_usage WHERE goal=? AND kind='model'",(c.work['goal_id'],)).fetchone()[0],used)
 def test_expert_controls_and_stopped_source_after_ending_fence_effects(self):
  for operation in ('pause','stop'):
   with self.subTest(operation=operation):
    c=self.expert()
    def behavior(request,hook):
     attempt={**f.ATTEMPT,'job_id':'expert'};hook(attempt);returned=c.provider.ending(request,attempt,dumps({'kind':'compose','content':'saved body','media_type':'text/plain','source_refs':request['source_refs']}))
     c.stop() if operation=='stop' else c.control('pause');return returned
    c.provider.behavior=behavior;c.execute();c.no_effects();self.assertEqual(c.call()['status'],'returned');self.assertEqual(c.call()['profile_id'],f.ID);self.assertNotIn('begin_step',c.boundary.log);self.assertEqual(len(c.provider.requests),1)
 def test_expert_unknown_restart_held_zero_settlement_and_no_mock_downgrade(self):
  n=NativeFixture(self);n.profile=f.profile();n.prepare();self.assertTrue(n.admit().ok);self.assertTrue(n.enter().ok);self.assertTrue(n.t.mark_native_unknown({'call_id':n.call_id}).ok);used=n.f.usage();n.f.reopen();before=n.f.snapshot();out=n.f.value(n.f.recover());self.assertEqual(out['disposition'],'held');self.assertEqual(n.f.snapshot(),before);self.assertEqual(n.f.usage(),used);self.assertFalse(n.t.finish_startup().ok)
  call=n.f.value(n.t.get_call({'call_id':n.call_id}));self.assertEqual(call['profile_id'],f.ID);self.assertEqual(call['native_phase'],'unknown');self.assertIs(call['may_enter'],False)
  result=n.t.end_call({'call_id':n.call_id,'outcome':'returned'});self.assertFalse(result.ok);self.assertEqual(n.f.snapshot(),before)
 def test_tsk_current_raw_replay_and_historical_profile_decoder_integrity(self):
  n=NativeFixture(self);n.profile=f.profile();n.prepare();self.assertTrue(n.admit().ok);self.assertTrue(n.enter().ok);ending=f.returned(n.request,n.profile,dumps(n.action),n.attempt);self.assertTrue(n.end(ending).ok);before=n.f.snapshot();value=n.f.value(n.output());self.assertEqual(value['content'],dumps(n.action));self.assertEqual(value['model_id'],f.MODEL);self.assertTrue(n.end(ending).ok);self.assertEqual(n.f.snapshot(),before)
  self.assertTrue(n.stop().ok);before=n.f.snapshot();self.assertFalse(n.output().ok);self.assertEqual(n.f.snapshot(),before)
 def test_primary_typed_before_hook_refusal_is_not_entered_and_not_reinvoked(self):
  c=self.primary()
  def refused(request,hook):raise f.refusal(request,c.provider.profile)
  c.provider.behavior=refused;turn=c.submit();out=c.run_turn(turn);self.assertEqual(out['status'],'failed');self.assertNotIn('reply',out);self.assertEqual(c.conn.execute('SELECT phase FROM v5_pri_native').fetchone()[0],'not_entered');used=c.used();self.assertEqual(c.run_turn(turn),out);self.assertEqual(c.used(),used);self.assertEqual(len(c.provider.calls),1)
 def test_expert_typed_before_hook_refusal_records_known_end_without_effect_or_reinvoke(self):
  c=self.expert()
  def refused(request,hook):raise f.refusal(request,c.provider.profile)
  c.provider.behavior=refused;c.execute();c.no_effects();self.assertEqual(c.call()['native_phase'],'not_entered');self.assertEqual(c.call()['status'],'not_entered');self.assertIn('end_native_call',c.boundary.log);used=c.conn.execute("SELECT used FROM v5_tsk_usage WHERE goal=? AND kind='model'",(c.work['goal_id'],)).fetchone()[0];c.execute();self.assertEqual(len(c.provider.requests),1);self.assertEqual(c.conn.execute("SELECT used FROM v5_tsk_usage WHERE goal=? AND kind='model'",(c.work['goal_id'],)).fetchone()[0],used)
 def test_mock_and_devin_boundaries_refuse_claude_provider_without_entry(self):
  c=self.primary();Mock=importlib.import_module('pal.primary_host_v5').PrimaryHost
  for invoke in (c.provider,c.provider.invoke):
   with self.subTest(invoke=callable(invoke)),self.assertRaises((ValueError,TypeError)):Mock(c.conn,guard=c.guard,memory=c.mem,tasks=c.tasks,request_scope=c.grant,invoke=invoke,model_id=f.MODEL)
  self.assertEqual(c.provider.calls,[])
  from tools.native_devin_text_v5 import NativeDevinText
  with self.assertRaises((ValueError,RuntimeError,TypeError)):NativeDevinText(runtime=Path('/fixture-runtime'),state_dir=Path('/fixture-state'),attempt_root=Path('/fixture-attempt'),executable=Path('/fixture-devin'),credential_files=(),profile=f.profile())
if __name__=='__main__':unittest.main()
