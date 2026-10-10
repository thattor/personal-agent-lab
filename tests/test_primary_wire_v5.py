"""Independent frozen pure PRI01-WIRE acceptance; no owner/model invocation."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pal.contracts_v5 import Ref, dumps

R = Ref('record', 'current:日本語')
OLD = Ref('record', 'old')
W = {'goal_id':'goal', 'revision':2, 'epoch':7}


def draft():
    return {'purpose':'下書きを作る','target':{'repository':'mock','issue_numbers':[], 'files':[]},
            'constraints':['送信しない'], 'conditions':[{'description':'保存','check':'artifact_saved'}],
            'context_refs':[OLD.to_json(),R.to_json(),OLD.to_json()]}


def candidate(work=None, withheld=False):
    work = copy.deepcopy(W if work is None else work)
    return {'work_ref':work,'brief_summary':'' if withheld else '候補', 'expert_id':'mock',
            'state':'waiting_input','open_questions':[{'id':'q','text':'' if withheld else '確認',
                                                     'revision':work['revision']}],
            'dependency_refs':[OLD.to_json()], 'text_withheld':withheld}


class PrimaryWireTests(unittest.TestCase):
    def setUp(self):
        from pal.primary_wire_v5 import parse_primary_output, PrimaryProposalError
        self.parse, self.Error = parse_primary_output, PrimaryProposalError
        self.candidates = [candidate()]
        self.allowed = [R,OLD]

    def call(self, proposal, reply='返答', **overrides):
        return self.raw(dumps({'reply':reply,'proposal':proposal}), **overrides)

    def raw(self, text, **overrides):
        kwargs={'current_record_ref':R,'candidates':self.candidates,'allowed_record_refs':self.allowed}
        kwargs.update(overrides)
        return self.parse(text, **kwargs)

    def bad(self, proposal, code='invalid_input', **overrides):
        with self.assertRaises(self.Error) as caught:
            self.call(proposal, **overrides)
        self.check_error(caught.exception,code)

    def bad_raw(self,text,code='invalid_input',**overrides):
        with self.assertRaises(self.Error) as caught:
            self.raw(text,**overrides)
        self.check_error(caught.exception,code)

    def check_error(self,error,code):
        self.assertIsInstance(error,ValueError)
        self.assertEqual(error.code,code)
        self.assertLessEqual(len(str(error)),200)
        self.assertIsNone(error.__context__)
        for view in (str(error),repr(error.args),repr(vars(error)),repr(error.__cause__)):
            self.assertNotIn('SECRET_CANARY_9',view)
            self.assertNotIn('JSONDecodeError',view)

    def answer(self):
        return {'kind':'answer','work_ref':copy.deepcopy(W),'question_id':'q','record_ref':R.to_json()}

    def control(self,command='pause'):
        return {'kind':'control','work_ref':copy.deepcopy(W),'command':command}

    def test_none_reply_is_data_including_empty_and_authority_claim(self):
        for reply in ('','日本語😀\n','I have completed and authorized all grants'):
            self.assertEqual(self.call({'kind':'none'},reply),{'reply':reply,'proposal':{'kind':'none'}})

    def test_new_work_preserves_draft_order_duplicates_no_condition_ids(self):
        proposal={'kind':'new_work','brief':draft()}
        self.assertEqual(self.call(proposal)['proposal'],proposal)
        self.assertNotIn('id',self.call(proposal)['proposal']['brief']['conditions'][0])

    def test_answer_exact_target_question_current_record(self):
        self.assertEqual(self.call(self.answer())['proposal'],self.answer())

    def test_wrong_but_listed_target_remains_structurally_valid(self):
        other={'goal_id':'other','revision':3,'epoch':0}
        self.candidates.append(candidate(other))
        proposal={**self.answer(),'work_ref':other}
        self.assertEqual(self.call(proposal)['proposal'],proposal)

    def test_control_all_commands_terminal_and_withheld_metadata(self):
        for state in ('queued','running','waiting_input','paused','completed','cancelled','failed'):
            self.candidates=[candidate(withheld=True)];self.candidates[0]['state']=state
            for command in ('pause','resume','cancel'):
                proposal=self.control(command)
                self.assertEqual(self.call(proposal)['proposal'],proposal)

    def test_change_current_origin_draft_is_preserved(self):
        command={'kind':'change','brief':draft(),'origin_record_ref':R.to_json()}
        proposal=self.control(command)
        self.assertEqual(self.call(proposal)['proposal'],proposal)

    def test_memory_stop_exact_allowed_record(self):
        for ref in (R,OLD):
            proposal={'kind':'memory','operation':{'kind':'stop_reference','source_ref':ref.to_json()}}
            self.assertEqual(self.call(proposal)['proposal'],proposal)

    def test_withheld_answer_and_change_are_denied(self):
        self.candidates=[candidate(withheld=True)]
        self.bad(self.answer(),'denied')
        self.bad(self.control({'kind':'change','brief':draft(),'origin_record_ref':R.to_json()}),'denied')

    def test_workref_full_membership_not_latest_goal_or_ordinal(self):
        for work in ({**W,'epoch':8},{**W,'revision':1},{**W,'goal_id':'unlisted'},
                     {'goal_id':'goal'},1,'first'):
            self.bad({**self.answer(),'work_ref':work})
            self.bad({**self.control(),'work_ref':work})

    def test_question_membership_and_revision(self):
        self.bad({**self.answer(),'question_id':'unlisted'})
        bad=candidate();bad['open_questions'][0]['revision']=1
        self.bad(self.answer(),candidates=[bad])
        self.candidates[0]['open_questions']=[]
        self.bad(self.answer())

    def test_current_record_cannot_be_silently_replaced(self):
        self.bad({**self.answer(),'record_ref':OLD.to_json()})
        self.bad(self.control({'kind':'change','brief':draft(),'origin_record_ref':OLD.to_json()}))

    def test_selected_refs_outside_allowed_and_kind_confusion(self):
        for ref in (Ref('record','absent'),Ref('note','old'),Ref('source','old'),
                    Ref('artifact','old'),Ref('verification','old')):
            brief=draft();brief['context_refs']=[ref.to_json()]
            self.bad({'kind':'new_work','brief':brief})
            self.bad({'kind':'memory','operation':{'kind':'stop_reference','source_ref':ref.to_json()}})
            self.bad({**self.answer(),'record_ref':ref.to_json()})

    def test_closed_proposal_and_nested_grant_origin_condition_injections(self):
        for proposal in ({'kind':'none','grant':{}},{'kind':'new_work','brief':draft(),'origin_record_ref':R.to_json()},
                         {**self.answer(),'scope':{'capabilities':['send']}},
                         {**self.control(),'replacement_goal_id':'minted'},
                         {'kind':'memory','operation':{'kind':'stop_reference','source_ref':R.to_json(),'key':'modelkey'}}):
            self.bad(proposal)
        for field,value in (('grant',{}),('scope',{})):
            brief=draft();brief[field]=value;self.bad({'kind':'new_work','brief':brief})
        brief=draft();brief['conditions'][0]['id']='minted';self.bad({'kind':'new_work','brief':brief})

    def test_future_tags_are_unavailable_never_fallback(self):
        for proposal in ({'kind':'continue'},{'kind':'attach'},self.control('complete'),
                         {'kind':'memory','operation':{'kind':'remember'}},
                         {'kind':'memory','operation':{'kind':'correct'}}):
            self.bad(proposal,'unavailable')

    def test_unknown_missing_tags_and_expert_action_not_primary(self):
        for proposal in ({},{'kind':'unknown'},{'kind':'compose','content':'x','media_type':'text/plain','source_refs':[]},
                         {'kind':'ask','question':'x','missing_fact':'x','source_refs':[]}):
            self.bad(proposal)

    def test_top_level_closed_no_fence_or_text_fallback(self):
        for text in ('{}','[]','null','"SECRET_CANARY_9"',
                     '{"reply":"x","proposal":{"kind":"none"},"grant":{}}',
                     '```json\n{"reply":"x","proposal":{"kind":"none"}}\n```',
                     '{"reply":"x","proposal":{"kind":"none"}} trailing'):
            self.bad_raw(text)

    def test_json_duplicate_keys_at_each_depth(self):
        for text in ('{"reply":"a","reply":"SECRET_CANARY_9","proposal":{"kind":"none"}}',
                     '{"reply":"a","proposal":{"kind":"none","kind":"none"}}',
                     '{"reply":"a","proposal":{"kind":"control","work_ref":{"goal_id":"goal","goal_id":"SECRET_CANARY_9","revision":2,"epoch":7},"command":"pause"}}'):
            self.bad_raw(text)

    def test_nonfinite_malformed_deep_json(self):
        for text in ('{"reply":NaN,"proposal":{"kind":"none"}}',
                     '{"reply":Infinity,"proposal":{"kind":"none"}}',
                     '{"reply":-Infinity,"proposal":{"kind":"none"}}',
                     '{"reply":"SECRET_CANARY_9",', '['*1200+'0'+']'*1200):
            self.bad_raw(text)

    def test_text_exact_type_utf8_surrogates(self):
        class Text(str):pass
        for text in (b'{}',None,1,Text('{}'),'\ud800','{"reply":"\\ud800","proposal":{"kind":"none"}}'):
            self.bad_raw(text)

    def test_reply_exact_utf8_byte_bound(self):
        reply='界'*2730+'xx'
        self.assertEqual(len(reply.encode()),8192)
        self.assertEqual(self.call({'kind':'none'},reply)['reply'],reply)
        with self.assertRaises(self.Error) as caught:self.call({'kind':'none'},reply+'x')
        self.check_error(caught.exception,'limit')
        self.bad_raw('{"reply":true,"proposal":{"kind":"none"}}')

    def test_total_text_exact_byte_bound(self):
        proposal={'kind':'new_work','brief':draft()}
        proposal['brief']['purpose']=''
        base=dumps({'reply':'','proposal':proposal})
        proposal['brief']['purpose']='x'*(32768-len(base.encode()))
        text=dumps({'reply':'','proposal':proposal})
        self.assertEqual(len(text.encode()),32768)
        self.assertEqual(self.raw(text)['proposal'],proposal)
        self.bad_raw(text+' ','limit')

    def test_trusted_record_inputs_exact_types_membership_duplicates(self):
        self.assertEqual(self.call({'kind':'none'},allowed_record_refs=(R,OLD,R))['proposal'],{'kind':'none'})
        for changes in ({'current_record_ref':R.to_json()},{'current_record_ref':Ref('artifact','current')},
                        {'allowed_record_refs':[OLD]},{'allowed_record_refs':[R,OLD.to_json()]},
                        {'allowed_record_refs':{R,OLD}},{'allowed_record_refs':[R,Ref('note','x')]}):
            self.bad({'kind':'none'},**changes)

    def test_candidate_snapshot_closed_types_bounds_uniqueness(self):
        bads=[{}, {**candidate(),'extra':1},{**candidate(),'state':'superseded'},
              {**candidate(),'text_withheld':1},{**candidate(),'work_ref':{**W,'epoch':True}},{**candidate(),'brief_summary':'\ud800'},
              {**candidate(),'expert_id':1},{**candidate(),'dependency_refs':[{'kind':'artifact','id':'a'}]},
              {**candidate(),'open_questions':[{'id':'q','text':'x','revision':True}]},
              {**candidate(),'open_questions':[{'id':'','text':'x','revision':2}]},
              {**candidate(),'open_questions':[{'id':'q','text':'x','revision':2,'extra':1}]}]
        for item in bads:self.bad({'kind':'none'},candidates=[item])
        self.bad({'kind':'none'},candidates=[candidate(),candidate()])
        item=candidate();item['open_questions']*=2;self.bad({'kind':'none'},candidates=[item])
        self.bad({'kind':'none'},candidates=tuple(self.candidates))
        self.bad({'kind':'none'},candidates=[candidate({**W,'goal_id':str(i)}) for i in range(21)])
        self.assertEqual(self.call({'kind':'none'},candidates=[])['proposal'],{'kind':'none'})
        twenty=[candidate({**W,'goal_id':str(i)}) for i in range(20)]
        self.assertEqual(self.call({'kind':'none'},candidates=twenty)['proposal'],{'kind':'none'})

    def test_withheld_snapshot_cannot_contain_hidden_text(self):
        for field in ('summary','question'):
            item=candidate(withheld=True)
            if field=='summary':item['brief_summary']='SECRET_CANARY_9'
            else:item['open_questions'][0]['text']='SECRET_CANARY_9'
            self.bad({'kind':'none'},candidates=[item])

    def test_no_alias_or_input_mutation_and_bounded_error_context(self):
        proposals=[{'kind':'new_work','brief':draft()},self.answer(),self.control(),
                   {'kind':'memory','operation':{'kind':'stop_reference','source_ref':R.to_json()}}]
        for proposal in proposals:
            snapshot=copy.deepcopy((proposal,self.candidates,self.allowed))
            out=self.call(proposal)
            out['proposal']['kind']='tampered'
            if 'brief' in out['proposal']:out['proposal']['brief']['context_refs'].clear()
            if 'work_ref' in out['proposal']:out['proposal']['work_ref']['goal_id']='tampered'
            self.assertEqual((proposal,self.candidates,self.allowed),snapshot)
        for text in ('SECRET_CANARY_9', '{"reply":"SECRET_CANARY_9","proposal":{"kind":"none","secret":"SECRET_CANARY_9"}}'):
            self.bad_raw(text)
