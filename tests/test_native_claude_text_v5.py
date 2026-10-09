"""Fixed local print protocol grammar/correlation; no prose quality grading."""
import copy,importlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
import native_claude_fixtures_v5 as f
class ClaudeBufferTests(unittest.TestCase):
 def module(self):return importlib.import_module('pal.native_claude_text_v5')
 def fail(self,rows=None,raw=None,**finish):
  b=f.buffer()
  with self.assertRaises((ValueError,TypeError)) as caught:
   b.feed(f.stream(rows) if raw is None else raw);b.finish(**{'stdout_eof':True,'stderr_eof':True,'exit_code':0,**finish})
  self.assertNotIn('PRIVATE_CANARY',str(caught.exception));self.assertLess(len(str(caught.exception)),160)
 def test_valid_two_frames_thinking_ads_hashes_closed_pair_and_incremental_utf8(self):
  m=self.module();self.assertEqual((m.CLAUDE_PROFILE_ID,m.CLAUDE_MODEL_ID,m.CLAUDE_CLI_VERSION),(f.ID,f.MODEL,f.VERSION))
  rows=f.frames();raw=f.stream(rows);b=f.buffer()
  for byte in raw:b.feed(bytes([byte]))
  pair=b.finish(stdout_eof=True,stderr_eof=True,exit_code=0);self.assertEqual(set(pair),{'capture','cessation'})
  capture=pair['capture'];ending=pair['cessation'];text=rows[-1]['result'];self.assertEqual(capture['text'],text);self.assertEqual(capture['chunks'],2);self.assertEqual(capture['utf8_bytes'],len(text.encode()))
  self.assertEqual(ending['stdout_sha256'],f.digest(raw));self.assertEqual(ending['frame_count'],6);self.assertEqual(ending['request_sha256'],ending['prompt_sha256']);self.assertEqual(len(ending),17)
  p=ending['protocol'];self.assertEqual(len(p),9);self.assertEqual(p['init_sha256'],f.digest(f.canonical(rows[0])));self.assertEqual(p['result_sha256'],f.digest(f.canonical(rows[-1])));self.assertEqual(p['assistant_sha256'],f.digest(f.canonical([f.digest(f.canonical(r)) for r in rows if r['type']=='assistant'])))
  self.assertEqual(ending['completion'],{'result_subtype':'success','result_is_error':False,'result_stop_reason':'end_turn','terminal_reason':'completed','num_turns':1,'queued_turn_count':0,'result_index':0,'stdout_eof':True,'stderr_eof':True,'exit_code':0,'tools':0,'permissions':0,'subagents':0})
  self.assertEqual(capture['cessation_sha256'],f.digest(f.canonical(ending)));self.assertEqual(capture['evidence_ref'],'pal-claude-text:'+capture['cessation_sha256'])
  with self.assertRaises(ValueError):b.finish(stdout_eof=True,stderr_eof=True,exit_code=0)
  with self.assertRaises(ValueError):b.feed(b'{}\n')
 def test_constructor_strict_bindings_copy_and_closed_profile_pair(self):
  cls=self.module().NativeClaudeBuffer
  valid={'request_sha256':'1'*64,'profile_sha256':'2'*64,'attempt_ref':copy.deepcopy(f.ATTEMPT),'session_id':f.SESSION,'argv_sha256':'3'*64}
  self.assertIsInstance(cls(**valid),cls)
  for change in ({'request_sha256':'A'*64},{'profile_sha256':False},{'session_id':'not-uuid'},{'argv_sha256':'x'},{'attempt_ref':{**f.ATTEMPT,'extra':1}}):
   with self.subTest(change=change),self.assertRaises((ValueError,TypeError)):cls(**{**valid,**change})
  native=importlib.import_module('pal.native_call_v5');p=f.profile();data=p.to_json();self.assertEqual(data['id'],f.ID);self.assertEqual(native.NativeProfile.from_json(data),p)
  for change in ({'extra':1},{'profile_sha256':'9'*64},{'evidence_kind':'native_like'}):
   with self.subTest(change=change),self.assertRaises(ValueError):native.NativeProfile.from_json({**p.to_json(),**change})
  data['id']='co-devin-acp-dynamic-text/1'
  with self.assertRaises(ValueError):native.NativeProfile.from_json(data)
  for pair in ((f.ID,'swe-2-high'),('other',f.MODEL)):
   with self.subTest(pair=pair),self.assertRaises(ValueError):native.NativeProfile(profile_id=pair[0],model_id=pair[1],qualification_sha256='4'*64,evidence_kind='fixture')
  old=native.NativeProfile(model_id='swe-2-high',qualification_sha256='4'*64,evidence_kind='fixture');self.assertEqual(old.id,'co-devin-acp-dynamic-text/1');self.assertEqual(native.NativeProfile.from_json(old.to_json()),old)
 def test_model_session_request_message_and_tool_mismatch(self):
  changes=[(0,lambda r:r.update(model='wrong')),(0,lambda r:r.update(claude_code_version='2.1.290')),(0,lambda r:r.update(tools=['Read'])),(0,lambda r:r.update(mcp_servers=[{'name':'x'}])),(0,lambda r:r.update(permissionMode='default')),
   (2,lambda r:r['message'].update(model='wrong')),(3,lambda r:r['message'].update(id='foreign')),(3,lambda r:r.update(request_id='foreign')),(2,lambda r:r.update(parent_tool_use_id='tool')),(2,lambda r:r['message'].update(content=[{'type':'tool_use','id':'PRIVATE_CANARY'}])),(2,lambda r:r.update(session_id=f.uid(99))),(4,lambda r:r['rate_limit_info'].update(isUsingOverage=True)),(4,lambda r:r['rate_limit_info'].update(status='rejected')),(1,lambda r:r.update(estimated_tokens=-1)),(1,lambda r:r.update(estimated_tokens_delta=True)),(2,lambda r:r.update(request_id='x'*513)),(2,lambda r:r.pop('uuid'))]
  for index,change in changes:
   with self.subTest(index=index):rows=f.frames();change(rows[index]);self.fail(rows)
 def test_result_false_types_subagents_usage_and_output_mismatch(self):
  changes=[lambda r:r.update(result='PRIVATE_CANARY'),lambda r:r.update(is_error=True),lambda r:r.update(stop_reason='max_tokens'),lambda r:r.update(terminal_reason='failed'),lambda r:r.update(num_turns=True),lambda r:r.update(queued_turn_count=1),lambda r:r.update(result_index=False),lambda r:r.update(permission_denials=[{}]),lambda r:r['modelUsage'].update(other={'inputTokens':1,'outputTokens':1}),lambda r:r['modelUsage'][f.MODEL].update(inputTokens=True),lambda r:r['modelUsage'][f.MODEL].update(outputTokens=0),lambda r:r['modelUsage'][f.MODEL].update(costUSD=float('nan')),lambda r:r['subagent_stats'].update(spawned=1),lambda r:r['subagent_stats']['requested'].update(background=1),lambda r:r['subagent_stats'].update(by_type={'agent':0})]
  for change in changes:
   with self.subTest(change=changes.index(change)):
    rows=f.frames();change(rows[-1])
    if isinstance(rows[-1]['modelUsage'][f.MODEL].get('costUSD'),float) and str(rows[-1]['modelUsage'][f.MODEL]['costUSD'])=='nan':self.fail(raw=b'\n'.join(json.dumps(r).encode() for r in rows)+b'\n')
    else:self.fail(rows)
 def test_order_duplicates_unknown_trailing_and_poisoned_finish(self):
  base=f.frames();variants=[base[1:],base+[base[-1]],[base[0],base[0],*base[1:]],[base[0],base[-1],*base[1:-1]],[{**base[0],'type':'user'},*base[1:]],[base[0],{**base[1],'subtype':'unknown'},*base[2:]]]
  rows=copy.deepcopy(base);rows[3]['uuid']=rows[2]['uuid'];variants.append(rows)
  for rows in variants:
   with self.subTest(length=len(rows)):self.fail(rows)
  b=f.buffer()
  with self.assertRaises(ValueError):b.feed(b'PRIVATE_CANARY\n')
  with self.assertRaises(ValueError):b.feed(f.stream(base))
 def test_json_utf8_duplicates_nonfinite_blank_truncation_and_nesting(self):
  for raw in (b'\xff\n',b'\n',b'{"type":"system","type":"system"}\n',b'{"x":NaN}\n',b'{"x":Infinity}\n',f.stream(f.frames())[:-1],b'{"x":'+b'['*65+b'0'+b']'*65+b'}\n'):
   with self.subTest(prefix=raw[:20]):self.fail(raw=raw)
 def test_frame_stdout_count_and_final_text_caps(self):
  self.fail(raw=b'x'*262145+b'\n');self.fail(raw=b'x'*1048577)
  b=f.buffer();text='日'*10922+'xx';self.assertEqual(len(text.encode()),32768);b.feed(f.stream(f.frames(text)));self.assertEqual(b.finish(stdout_eof=True,stderr_eof=True,exit_code=0)['capture']['text'],text)
  rows=f.frames('x'*32769);self.fail(rows)
  rows=f.frames('')
  self.fail(rows)
  rows=f.frames();ticks=[{**rows[1],'uuid':f.uid(i+100)} for i in range(2048)];self.fail([rows[0],*ticks,*rows[2:]])
  rows=f.frames();rows[2]['message']['content']=[{'type':'text','text':'x'} for _ in range(2049)];rows[3]['message']['content']=[{'type':'text','text':'y'}];rows[-1]['result']='x'*2049+'y';self.fail(rows)
 def test_finish_eof_and_exit_types_are_strict(self):
  for changes in ({'stdout_eof':False},{'stderr_eof':False},{'stdout_eof':1},{'exit_code':False},{'exit_code':-15},{'exit_code':1}):
   with self.subTest(changes=changes):self.fail(f.frames(),**changes)
 def test_ending_validator_closed_binding_tamper_and_defensive_copy(self):
  m=self.module();b=f.buffer();b.feed(f.stream(f.frames()));pair=b.finish(stdout_eof=True,stderr_eof=True,exit_code=0);capture=pair['capture'];ending=pair['cessation']
  kw={'request_sha256':'1'*64,'profile_sha256':'2'*64,'attempt_ref':f.ATTEMPT,'model_id':f.MODEL,'output_sha256':capture['output_sha256'],'utf8_bytes':capture['utf8_bytes'],'chunks':2}
  value=m.validate_claude_ending(ending,**kw);value['completion']['exit_code']=5;self.assertEqual(ending['completion']['exit_code'],0)
  changes=[lambda e:e.update(extra=1),lambda e:e.update(model_id='wrong'),lambda e:e.update(request_sha256='9'*64),lambda e:e.update(prompt_sha256='9'*64),lambda e:e.update(stdout_sha256='bad'),lambda e:e['protocol'].update(assistant_model='wrong'),lambda e:e['completion'].update(exit_code=False),lambda e:e['completion'].update(subagents=1),lambda e:e.update(chunks=True)]
  for change in changes:
   with self.subTest(index=changes.index(change)),self.assertRaises(ValueError):e=copy.deepcopy(ending);change(e);m.validate_claude_ending(e,**kw)
 def test_native_returned_claude_dispatch_and_profile_laundering_refusal(self):
  native=importlib.import_module('pal.native_call_v5');p=f.profile();request={'fixture':'whole request'};returned=f.returned(request,p,'JSON data');evidence=returned.validate(request_sha256=f.digest(f.canonical(request)),profile=p);self.assertEqual(evidence['model_id'],f.MODEL);self.assertEqual(evidence['evidence_kind'],'fixture')
  wrong=native.NativeProfile(model_id='swe-2-high',qualification_sha256='4'*64,evidence_kind='fixture')
  with self.assertRaises(ValueError):returned.validate(request_sha256=f.digest(f.canonical(request)),profile=wrong)
if __name__=='__main__':unittest.main()
