"""Fixed pure first-overflow contract; synthetic values grant no model authority."""
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pal.native_text_v5 import NativeModelDiagnostic
REQ='1'*64;PROFILE='2'*64
ATT={'run_id':'fixture-run','job_id':'primary','attempt_id':'fixture-attempt'}
LIMITS={'max_observations':32,'max_options':16,'max_values':32,'max_string_bytes':256,'max_record_bytes':32768}
def make(**kw):return NativeModelDiagnostic(**{'request_sha256':REQ,'profile_sha256':PROFILE,'attempt_ref':copy.deepcopy(ATT),'model_id':'swe-2-high',**kw})
def opt(**kw):return {'id':'model','type':'select','currentValue':'swe-2-high','options':[{'value':'swe-2-high'}],**kw}
def payload(option):return {'configOptions':[option]}
class ModelOverflowTests(unittest.TestCase):
 def snapshot(self,d):return d.overflow_snapshot()
 def marker(self,d,reason,site,unit,limit,index=0,hint=False,**metadata):
  expected={'retained_index':index,'hook':'observe','shape':'field_snapshot','original_hook':'returned','current_update':False,'reason':reason,'site':site,'unit':unit,'limit':limit,'observed_at_least':limit+1,'valid_hint_retained':hint,**metadata}
  self.assertEqual(self.snapshot(d),{'version':'PRI02-MODEL-OVERFLOW/1','authority':'unqualified','request_sha256':REQ,'profile_sha256':PROFILE,'attempt_ref':ATT,'requested_model_id':'swe-2-high','status':'overflow','first_overflow':expected,'limits':{**LIMITS,'max_marker_record_bytes':4096}})
 def test_closed_empty_defensive_bindings_and_original_snapshot(self):
  a=copy.deepcopy(ATT);d=make(attempt_ref=a);a['run_id']='changed'
  old=d.snapshot();s=self.snapshot(d)
  self.assertEqual(s,{'version':'PRI02-MODEL-OVERFLOW/1','authority':'unqualified','request_sha256':REQ,'profile_sha256':PROFILE,'attempt_ref':ATT,'requested_model_id':'swe-2-high','status':'not_observed','first_overflow':None,'limits':{**LIMITS,'max_marker_record_bytes':4096}})
  s['attempt_ref']['run_id']='changed';s['limits']['max_options']=999
  self.assertEqual(self.snapshot(d)['attempt_ref'],ATT);self.assertEqual(d.snapshot(),old);self.assertEqual(len(old),9)
 def test_count_paths_and_first_refusal_order(self):
  cases=[({'configOptions':[opt() for _ in range(17)]},'option_count','configOptions',16),
   (payload(opt(options=[{'value':str(i)} for i in range(33)])),'value_count','select_options',32),
   (payload(opt(options=[{'group':'G','options':[{'value':str(i)} for i in range(33)]}])),'value_count','group_options',32),
   (payload(opt(options=[{'group':'A','options':[{'value':str(i)} for i in range(16)]},{'group':'B','options':[{'value':str(i)} for i in range(17)]}])),'value_count','flattened_options',32)]
  for fields,reason,site,limit in cases:
   with self.subTest(site=site):
    d=make();d.observe(fields,hook='observe');self.marker(d,reason,site,'count',limit);self.assertEqual(d.snapshot()['observations'],[])
  d=make();d.observe(payload(opt(id='x'*257,options=[{'value':'x'} for _ in range(33)])),hook='observe');self.marker(d,'token_length','option_id','codepoints',256)
 def test_all_token_sites_codepoints_and_utf8_units(self):
  for site in ('option_id','category','current_value','available_value','group_id'):
   for unit,value in (('codepoints','x'*257),('utf8_bytes','日'*86)):
    with self.subTest(site=site,unit=unit):
     field={'option_id':'id','category':'category','current_value':'currentValue'}.get(site)
     o=opt(**{field:value}) if field else opt(options=[{'value':value}]) if site=='available_value' else opt(options=[{'group':value,'options':[{'value':'swe-2-high'}]}])
     raw=payload(o);saved=copy.deepcopy(raw);d=make();d.observe(raw,hook='observe');self.marker(d,'token_length',site,unit,256);self.assertEqual(raw,saved)
 def test_prefix_hint_retention_first_marker_and_observation_count(self):
  d=make();d.observe(payload(opt()),hook='observe');prefix=d.snapshot()['observations'];d.observe({'sessionUpdate':'config_option_update','configOptions':[opt() for _ in range(17)]},hook='observe',current_update=False,original_hook='raised')
  self.marker(d,'option_count','configOptions','count',16,index=1,hint=True,shape='config_option_update',original_hook='raised')
  marker=self.snapshot(d);marker['first_overflow']['limit']=999
  d.observe(payload(opt(id='x'*257)),hook='verify_session');self.assertEqual(d.snapshot()['observations'],prefix);self.assertEqual(self.snapshot(d)['first_overflow']['reason'],'option_count')
  d=make()
  for _ in range(32):d.observe({'sessionId':'fixture'},hook='observe')
  d.observe({},hook='verify_session',original_hook='raised');self.marker(d,'observation_count','observations','count',32,index=32,hook='verify_session',shape='preprompt_snapshot',original_hook='raised')
  d=make()
  for _ in range(32):d.observe({'sessionId':'fixture'},hook='observe')
  d.observe({'configOptions':[opt() for _ in range(17)]},hook='invalid',current_update=1,original_hook='invalid');self.marker(d,'observation_count','observations','count',32,index=32,original_hook='raised')
 def test_record_bytes_and_no_raw_values_retained(self):
  d=make();d.observe(payload(opt()),hook='observe');prefix=d.snapshot()['observations']
  fields={'configOptions':[opt(id=str(i),currentValue='x'*256,options=[{'value':'x'*256} for _ in range(32)]) for i in range(16)]}
  d.observe(fields,hook='verify_session');self.marker(d,'record_bytes','snapshot','utf8_bytes',32768,index=1,hint=True,hook='verify_session',shape='preprompt_snapshot')
  self.assertEqual(d.snapshot()['observations'],prefix);self.assertNotIn('x'*256,json.dumps(self.snapshot(d)));self.assertLessEqual(len(json.dumps(d.snapshot()).encode()),32768)
 def test_ignored_malformed_session_and_utf8_do_not_mark(self):
  cases=[({'sessionId':'x'*513},'observe',{}),(payload(opt(id='\ud800')),'observe',{}),(payload(opt(currentValue=1)),'observe',{}),(payload(opt(id='x'*257)),'bad',{}),(payload(opt(id='x'*257)),'observe',{'current_update':1})]
  for fields,hook,kw in cases:
   with self.subTest(hook=hook,kw=kw):
    d=make();d.observe(fields,hook=hook,**kw);self.assertEqual(self.snapshot(d)['status'],'not_observed');self.assertIsNone(self.snapshot(d)['first_overflow']);self.assertEqual(d.snapshot()['observations'][0]['projection_status'],'malformed')
  d=make()
  for _ in range(40):d.observe({'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':'x'*10000}},hook='observe')
  self.assertEqual(d.snapshot()['observations'],[]);self.assertEqual(self.snapshot(d)['status'],'not_observed')
  d.observe(payload(opt(currentValue='日'*85+'x')),hook='observe');self.assertEqual(self.snapshot(d)['status'],'not_observed')
 def test_sidecar_size_refusal_preserves_original_state(self):
  d=make(attempt_ref={k:'\x01'*512 for k in ATT},model_id='\x01'*512);before=d.snapshot()
  with self.assertRaises(ValueError):self.snapshot(d)
  self.assertEqual(d.snapshot(),before)
  d.observe({'configOptions':[opt() for _ in range(17)]},hook='observe');before=d.snapshot()
  with self.assertRaises(ValueError):self.snapshot(d)
  self.assertEqual(d.snapshot(),before)
if __name__=='__main__':unittest.main()
