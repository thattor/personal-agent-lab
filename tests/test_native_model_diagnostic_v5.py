"""Pure public-hook fixtures; no model identity or protocol coverage proof."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REQUEST='1'*64
PROFILE='2'*64
ATTEMPT={'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'fixture-attempt'}
LIMITS={'max_observations':32,'max_options':16,'max_values':32,'max_string_bytes':256,'max_record_bytes':32768}
def option(value='swe-2-high', **extra):
    return {'id':'model','type':'select','currentValue':value,'options':[{'value':value}],**extra}
def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

class NativeModelDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.cls=getattr(importlib.import_module('pal.native_text_v5'),'NativeModelDiagnostic')
        self.d=self.make()
    def make(self,**kw):
        return self.cls(**{'request_sha256':REQUEST,'profile_sha256':PROFILE,'attempt_ref':copy.deepcopy(ATTEMPT),'model_id':'swe-2-high',**kw})
    def observe(self,fields,**kw):
        self.assertIsNone(self.d.observe(fields,hook='observe',**kw))
        return self.d.snapshot()['observations'][-1]
    def test_empty_closed_snapshot_and_bindings(self):
        self.assertEqual(self.d.snapshot(),{'version':'PRI02-MODEL-DIAGNOSTIC/1','authority':'unqualified','request_sha256':REQUEST,'profile_sha256':PROFILE,'attempt_ref':ATTEMPT,'requested_model_id':'swe-2-high','status':'complete','observations':[],'limits':LIMITS})
    def test_constructor_rejects_bad_closed_bindings(self):
        for kw in ({'request_sha256':'A'*64},{'profile_sha256':True},{'attempt_ref':{**ATTEMPT,'extra':1}},{'attempt_ref':{**ATTEMPT,'job_id':''}},{'model_id':'\ud800'},{'model_id':'日'*171}):
            with self.subTest(kw=list(kw)),self.assertRaises(ValueError):self.make(**kw)
    def test_projection_closed_and_raw_unknown_fields_ignored(self):
        raw={'sessionId':'日本語','configOptions':[option(name='PRIVATE_CANARY',_meta=object(),category='model')]}
        o=self.observe(raw,current_update=True)
        self.assertEqual(o,{'delivery_index':0,'hook':'observe','shape':'field_snapshot','original_hook':'returned','session_sha256':hashlib.sha256('日本語'.encode()).hexdigest(),'current_update':True,'projection_status':'valid','options':[{'id':'model','category':'model','type':'select','current_value':'swe-2-high','available_values':['swe-2-high']}],'effective_model_hint':{'option_id':'model','current_value':'swe-2-high'}})
        self.assertNotIn('PRIVATE_CANARY',canonical(self.d.snapshot()).decode())
    def test_group_boolean_duplicates_and_source_order(self):
        raw=[{'id':'model','type':'select','currentValue':'b','options':[{'group':'G','options':[{'value':'a'},{'value':'b'},{'value':'a'}]},{'group':'H','options':[{'value':'c'}]}]}, {'id':'flag','type':'boolean','currentValue':False}]
        o=self.observe({'configOptions':raw});self.assertEqual(o['options'][0]['available_values'],['a','b','a','c']);self.assertEqual(o['options'][1],{'id':'flag','category':None,'type':'boolean','current_value':False,'available_values':[]})
    def test_hint_requires_unique_exact_model_select_membership(self):
        for opts in ([option(),option()],[option(id='Model')],[option(id='configId',category='model')],[{**option(),'currentValue':'absent'}],[{'id':'model','type':'boolean','currentValue':True}]):
            with self.subTest(opts=opts):self.assertIsNone(self.observe({'configOptions':opts})['effective_model_hint'])
    def test_irrelevant_chunks_ignored_and_absent_options_valid(self):
        for i in range(40):self.d.observe({'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':'PRIVATE'}},hook='observe')
        self.assertEqual(self.d.snapshot()['observations'],[])
        self.assertEqual(self.observe({'sessionId':'fixture'})['options'],[])
        self.d.observe({},hook='verify_session');self.assertEqual(self.d.snapshot()['observations'][-1]['shape'],'preprompt_snapshot')
    def test_update_duplicate_changed_hints_remain_separate(self):
        for v in ['a','a','b']:self.observe({'sessionUpdate':'config_option_update','configOptions':[option(v)]},current_update=True)
        rows=self.d.snapshot()['observations'];self.assertEqual([o['delivery_index'] for o in rows],[0,1,2]);self.assertEqual([o['effective_model_hint']['current_value'] for o in rows],['a','a','b']);self.assertTrue(all(o['shape']=='config_option_update' and o['session_sha256'] is None for o in rows))
    def test_malformed_projection_consumes_one_and_later_good_survives(self):
        bad=[None,{'sessionUpdate':'config_option_update'},{'configOptions':[option(options=[{'value':'x'},{'group':'G','options':[{'value':'x'}]}])]},{'configOptions':[{'id':'flag','type':'boolean','currentValue':1}]},{'configOptions':[option(id='\ud800')]}]
        for fields in bad:
            o=self.observe(fields);self.assertEqual((o['projection_status'],o['options'],o['effective_model_hint']),('malformed',[],None))
        self.assertEqual(self.observe({'configOptions':[option()]})['projection_status'],'valid')
    def test_invalid_hook_metadata_uses_conservative_defaults(self):
        for kw in ({'hook':'PRIVATE'},{'current_update':1},{'original_hook':'PRIVATE'}):
            self.d.observe({'configOptions':[option()]},**{'hook':'observe',**kw})
            o=self.d.snapshot()['observations'][-1];self.assertEqual((o['hook'],o['shape'],o['original_hook'],o['current_update'],o['projection_status']),('observe','field_snapshot','raised',False,'malformed'))
    def test_defensive_input_and_snapshot_copies(self):
        a=copy.deepcopy(ATTEMPT);d=self.make(attempt_ref=a);a['run_id']='changed';fields={'configOptions':[option()]};saved=copy.deepcopy(fields);d.observe(fields,hook='observe');self.assertEqual(fields,saved);fields['configOptions'][0]['currentValue']='changed';s=d.snapshot();s['observations'][0]['options'][0]['available_values'].append('changed');s['attempt_ref']['run_id']='changed';self.assertEqual(d.snapshot()['attempt_ref'],ATTEMPT);self.assertEqual(d.snapshot()['observations'][0]['options'][0]['available_values'],['swe-2-high'])
    def test_count_and_option_value_caps_freeze_prefix(self):
        for fields in ({'configOptions':[option(id=str(i)) for i in range(17)]},{'configOptions':[option(options=[{'value':str(i)} for i in range(33)])]}):
            d=self.make();d.observe({'sessionId':'good'},hook='observe');prefix=d.snapshot()['observations'];d.observe(fields,hook='observe');d.observe({'sessionId':'later'},hook='observe');self.assertEqual(d.snapshot()['observations'],prefix);self.assertEqual(d.snapshot()['status'],'incomplete')
        d=self.make()
        for i in range(32):d.observe({'sessionId':str(i)},hook='observe')
        self.assertEqual(len(d.snapshot()['observations']),32);d.observe({'sessionId':'overflow'},hook='observe');self.assertEqual((len(d.snapshot()['observations']),d.snapshot()['status']),(32,'incomplete'))
    def test_token_byte_overflow_freezes_but_malformed_utf8_can_continue(self):
        self.observe({'configOptions':[option('日'*85+'x')]})
        prefix=self.d.snapshot()['observations']
        self.observe({'configOptions':[option('日'*85+'xx')]})
        self.assertEqual(self.d.snapshot()['status'],'incomplete')
        self.assertEqual(self.d.snapshot()['observations'],prefix)
        self.d.observe({'configOptions':[option('later')]},hook='observe')
        self.assertEqual(self.d.snapshot()['observations'],prefix)
        d=self.make()
        d.observe({'configOptions':[option('\ud800')]},hook='observe')
        row=d.snapshot()['observations'][0]
        self.assertEqual((row['projection_status'],row['options'],row['effective_model_hint']),('malformed',[],None))
        d.observe({'configOptions':[option('good')]},hook='observe')
        self.assertEqual(d.snapshot()['status'],'complete')
        self.assertEqual(d.snapshot()['observations'][1]['effective_model_hint']['current_value'],'good')
    def test_utf8_token_boundary_and_total_byte_cap(self):
        self.assertEqual(self.observe({'configOptions':[option('日'*85+'x')]})['projection_status'],'valid')
        d=self.make();fields={'configOptions':[option('x'*256, id=str(i),options=[{'value':str(j)+'x'*250} for j in range(32)]) for i in range(16)]};d.observe({'sessionId':'prefix'},hook='observe');prefix=d.snapshot()['observations'];d.observe(fields,hook='observe');self.assertEqual(d.snapshot()['status'],'incomplete');self.assertEqual(d.snapshot()['observations'],prefix);self.assertLessEqual(len(canonical(d.snapshot())),32768)

if __name__=='__main__':unittest.main()
