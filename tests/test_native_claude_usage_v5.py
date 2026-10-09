"""Frozen twelve-key usage grammar, synthetic transport data only; no quality grade."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import native_claude_fixtures_v5 as f

USAGE_KEYS={'canonicalModel','provider','costBasis','inputTokens','outputTokens',
 'cacheReadInputTokens','cacheCreationInputTokens','thinkingTokens','contextWindow',
 'maxOutputTokens','webSearchRequests','costUSD'}

class ClaudeUsageTests(unittest.TestCase):
 def accept(self,rows):
  buffer=f.buffer();buffer.feed(f.stream(rows));pair=buffer.finish(stdout_eof=True,stderr_eof=True,exit_code=0)
  self.assertEqual(pair['capture']['text'],rows[-1]['result'])
  self.assertEqual(pair['capture']['output_sha256'],f.digest(rows[-1]['result'].encode()))
  self.assertEqual(pair['cessation']['stdout_sha256'],f.digest(f.stream(rows)))
  return pair
 def refuse(self,rows,nonfinite=False):
  buffer=f.buffer()
  raw=b''.join(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()+b'\n' for r in rows) if nonfinite else f.stream(rows)
  with self.assertRaises(ValueError) as caught:
   buffer.feed(raw);buffer.finish(stdout_eof=True,stderr_eof=True,exit_code=0)
  self.assertNotIn('SYNTHETIC_CANARY',str(caught.exception));self.assertLess(len(str(caught.exception)),160)
  with self.assertRaises(ValueError):buffer.finish(stdout_eof=True,stderr_eof=True,exit_code=0)
 def usage(self,rows):return rows[-1]['modelUsage'][f.MODEL]
 def test_valid_closed_twelve_keys_strings_and_integer_or_float_cost(self):
  for cost in (0,1,0.0,0.125):
   with self.subTest(cost=cost):
    rows=f.frames('synthetic transport data');u=self.usage(rows);self.assertEqual(set(u),USAGE_KEYS)
    self.assertEqual((u['canonicalModel'],u['provider'],u['costBasis']),(f.MODEL,'firstParty','list'))
    u['costUSD']=cost;pair=self.accept(rows);rows[-1]['result']='changed fixture';self.assertEqual(pair['capture']['text'],'synthetic transport data')
 def test_usage_is_closed_missing_each_field_and_extra_field_refuse(self):
  for missing in sorted(USAGE_KEYS):
   with self.subTest(missing=missing):rows=f.frames();del self.usage(rows)[missing];self.refuse(rows)
  rows=f.frames();self.usage(rows)['SYNTHETIC_CANARY_extra']=0;self.refuse(rows)
  for malformed in ([],None,'SYNTHETIC_CANARY',False):
   with self.subTest(malformed=malformed):rows=f.frames();rows[-1]['modelUsage'][f.MODEL]=malformed;self.refuse(rows)
 def test_three_string_fields_have_exact_identity_and_types(self):
  for field in ('canonicalModel','provider','costBasis'):
   for bad in ('SYNTHETIC_CANARY',None,0,True,[],{}):
    with self.subTest(field=field,bad=bad):rows=f.frames();self.usage(rows)[field]=bad;self.refuse(rows)
 def test_input_and_output_tokens_are_positive_exact_integer(self):
  rows=f.frames();self.usage(rows).update(inputTokens=1,outputTokens=1);self.accept(rows)
  for field in ('inputTokens','outputTokens'):
   for bad in (True,False,0,-1,1.5,'1',None):
    with self.subTest(field=field,bad=bad):rows=f.frames();self.usage(rows)[field]=bad;self.refuse(rows)
 def test_other_numeric_fields_have_correct_integer_bounds_and_finite_cost(self):
  counters=('cacheReadInputTokens','cacheCreationInputTokens','thinkingTokens')
  positive=('contextWindow','maxOutputTokens')
  rows=f.frames();self.usage(rows).update({field:0 for field in counters});self.usage(rows).update({field:1 for field in positive});self.accept(rows)
  for field in (*counters,*positive):
   for bad in (True,False,-1,0.5,'0',None,*((0,) if field in positive else ())):
    with self.subTest(field=field,bad=bad):rows=f.frames();self.usage(rows)[field]=bad;self.refuse(rows)
  for bad in (True,False,-1,-0.5,'0',None,[],float('nan'),float('inf'),float('-inf')):
   with self.subTest(cost=bad):rows=f.frames();self.usage(rows)['costUSD']=bad;self.refuse(rows,nonfinite=isinstance(bad,float) and not -float('inf')<bad<float('inf'))
 def test_web_search_requests_is_exact_zero_without_extra_tool_authority(self):
  for bad in (True,False,1,-1,0.0,'0',None):
   with self.subTest(web_search=bad):rows=f.frames();self.usage(rows)['webSearchRequests']=bad;self.refuse(rows)
  rows=f.frames();self.usage(rows)['webSearchRequests']=0;self.accept(rows)

if __name__=='__main__':unittest.main()
