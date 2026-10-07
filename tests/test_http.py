import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from pal.runtime import Runtime
from pal.server import make_server


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime=Runtime(Path(self.temp.name)/'state.db')
        self.addCleanup(self.runtime.close)
        self.server=make_server(self.runtime,0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.runtime.close()
        self.temp.cleanup()

    def request(self,path,body=None,headers=None,method=None):
        data=json.dumps(body).encode() if body is not None else None
        request=urllib.request.Request(self.base+path,data=data,method=method,headers=headers or {})
        try:
            response=urllib.request.urlopen(request,timeout=3)
        except urllib.error.HTTPError as error:
            response=error
        with response:
            return response.status,response.read(),response.headers

    def post(self,body,path='/api/message',origin=None):
        return self.request(path,body,{'Origin':origin or self.base,'Content-Type':'application/json'})

    def test_conversation_draft_and_inspect_artifact(self):
        status,body,_=self.post({'key':'hello','text':'Hello'})
        self.assertEqual(status,202)
        self.assertIsNone(json.loads(body)['goal'])
        status,body,_=self.post({'key':'draft','text':'Make a draft, do not send'})
        self.assertEqual(status,202)
        self.assertTrue(self.runtime.idle.wait(2))
        status,body,_=self.request('/api/state')
        state=json.loads(body)
        self.assertEqual(state['goals'][0]['state'],'completed')
        artifact=state['receipts'][0]['artifact_id']
        status,body,headers=self.request('/api/artifact/'+artifact)
        self.assertEqual(status,200)
        self.assertTrue(body)
        self.assertIn('text/plain',headers['Content-Type'])
        for route in ('/','/inspect','/app.js','/style.css'):
            self.assertEqual(self.request(route)[0],200)

    def test_inspect_is_read_only_and_cross_origin_cannot_mutate(self):
        before=self.runtime.store.inspect()
        self.assertEqual(self.post({'key':'bad','text':'Make a draft'},origin='https://evil.invalid')[0],403)
        self.assertEqual(self.post({'key':'bad','text':'Hello'},path='/api/state')[0],405)
        self.assertEqual(self.request('/api/state',headers={'Host':'evil.invalid'})[0],403)
        self.assertEqual(self.runtime.store.inspect(),before)
        self.assertEqual(self.request('/api/state',method='DELETE')[0],405)

    def test_duplicate_client_message_and_invalid_fields(self):
        body={'key':'same','text':'Make a draft'}
        a=self.post(body)
        b=self.post(body)
        self.assertEqual(json.loads(a[1]),json.loads(b[1]))
        self.assertEqual(len(self.runtime.store.inspect()['goals']),1)
        self.assertEqual(self.post({'key':'bad','text':'Hello','state':'completed'})[0],400)
        self.assertEqual(self.post({'key':'same','text':'Different'})[0],400)

    def test_host_bound_selection_http_and_guarded_state(self):
        self.assertTrue(self.runtime.idle.wait(2))
        goals = []
        for name in ('Cedar', 'Birch'):
            result = self.runtime.store.ingress('seed-' + name, name + ' draft', 'draft')
            goals.append(result['goal']['id'])
            self.runtime.store.control('pause-' + name, goals[-1], 'pause')
        status, body, _ = self.post({'key': 'question', 'text': 'その下書きを止めて'})
        self.assertEqual(status, 202)
        question = json.loads(body)
        self.assertEqual(question['control_status'], 'selection_required')
        state = json.loads(self.request('/api/state')[1])
        self.assertEqual(len(state['selections'][0]['choices']), 2)
        payload = {'key': 'choice', 'text': 'Select work target', 'control': {
            'action': 'select', 'selection_id': question['selection_id'],
            'source_key': question['source_key'], 'target_id': goals[0]}}
        first = self.post(payload)
        self.assertEqual(first[0], 202)
        self.assertEqual(json.loads(first[1])['control_status'], 'applied')
        self.assertEqual(json.loads(self.post(payload)[1]), json.loads(first[1]))
        self.assertEqual(self.runtime.store.get_goal(goals[1])['state'], 'paused')
        self.assertEqual(json.loads(self.request('/api/state')[1])['selections'][0]['choices'], [])
        payload['key'] = 'tamper'
        payload['control']['text'] = 'invented correction'
        self.assertEqual(self.post(payload)[0], 400)

    def test_conversational_remember_and_forget(self):
        self.post({'key':'remember','text':'Remember the fictional project is green'})
        source=self.runtime.store.inspect()['records'][0]
        self.assertEqual(len(self.runtime.store.context()['notes']),1)
        self.assertEqual(self.post({'key':'forget','text':'Forget that'})[0],202)
        self.assertNotIn(source['id'],self.runtime.store.context()['manifest'])
        retained=[r for r in self.runtime.store.inspect()['records'] if r['id']==source['id']][0]
        self.assertEqual(retained['usable'],0)
        self.assertTrue(retained['content'])

    def test_ui_csp_no_inline_model_html_and_request_bounds(self):
        status,body,headers=self.request('/')
        self.assertIn("script-src 'self'",headers['Content-Security-Policy'])
        self.assertIn(b'id="session-receipt" translate="no"',body)
        _,script,_=self.request('/app.js')
        self.assertIn(b'textContent',script)
        self.assertNotIn(b'innerHTML',script)
        self.assertEqual(self.request('/api/message',{'key':'x','text':'x'},headers={'Origin':self.base,'Content-Type':'text/plain'})[0],400)
        self.assertEqual(self.post({'key':'big','text':'x'*70000})[0],413)

    def test_artifact_status_readonly_and_forget_stale(self):
        self.assertTrue(self.runtime.idle.wait(2))
        store = self.runtime.store
        source = store.record('source','user','Friday')
        store.create_goal('g','Draft Friday',{'kind':'local_draft','max_bytes':4096},[source['id']])
        attempt = store.claim()
        receipt = store.write_draft(attempt['id'],'Friday draft')
        store.complete(attempt['id'],receipt['id'])
        route = '/api/artifact_status/' + receipt['artifact_id']
        before = store.inspect()
        status, body, _ = self.request(route)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body),{'role':'draft','reason':'','stale':False})
        self.assertEqual(self.post({'key':'bad','text':'mutate'},path=route)[0],405)
        self.assertEqual(store.inspect(),before)
        store.forget('forget-source',source['id'])
        self.assertTrue(json.loads(self.request(route)[1])['stale'])
        self.assertEqual(self.request('/api/artifact/'+receipt['artifact_id'])[1], b'Friday draft')
        self.assertEqual(self.request('/api/artifact_status/unknown')[0],404)

    def test_explicit_question_answer_http_rejects_wrong_binding(self):
        self.assertTrue(self.runtime.idle.wait(2))
        store = self.runtime.store
        goal = store.create_goal('g','Draft invitation',{'kind':'local_draft','max_bytes':4096})
        waiting = store.waiting(store.claim()['id'],'Which date?')
        payload = {'key':'answer','text':'Saturday','goal_id':goal['id'],'control':{
            'action':'input','text':'Saturday','question_id':waiting['question_id'],'epoch':waiting['epoch']+1}}
        before = store.inspect()
        self.assertEqual(self.post(payload)[0],400)
        self.assertEqual(store.inspect(),before)
        payload['control']['epoch']=waiting['epoch']
        self.assertEqual(self.post(payload)[0],202)
        self.assertTrue(self.runtime.idle.wait(2))
        self.assertEqual(store.get_goal(goal['id'])['state'],'completed')
        self.assertEqual(store.inspect()['questions'][0]['status'],'answered')

    def test_lost_ack_fate_can_be_queried_without_duplicate_effect(self):
        self.post({'key':'lost-ack','text':'Make a draft'})
        status,body,_=self.request('/api/operation/lost-ack')
        fate=json.loads(body)
        self.assertEqual(fate['status'],'accepted')
        goal_id=fate['result']['goal']['id']
        self.assertEqual(self.request('/api/operation/absent')[0],200)
        self.assertEqual(json.loads(self.request('/api/operation/absent')[1])['status'],'absent')
        self.post({'key':'lost-ack','text':'Make a draft'})
        self.assertEqual(self.runtime.store.inspect()['goals'][0]['id'],goal_id)
        self.assertEqual(len(self.runtime.store.inspect()['goals']),1)

    def test_duplicate_natural_forget_keeps_original_target_binding(self):
        self.post({'key':'remember','text':'Remember the fictional color is green'})
        first=self.post({'key':'forget','text':'Forget that'})
        state=self.runtime.store.inspect()
        second=self.post({'key':'forget','text':'Forget that'})
        self.assertEqual(first[0],202)
        self.assertEqual(json.loads(first[1]),json.loads(second[1]))
        references=[e for e in self.runtime.store.inspect()['events'] if e['kind']=='reference.stopped']
        self.assertEqual(len(references),1)
        self.assertEqual(len([r for r in self.runtime.store.inspect()['records'] if r['role']=='user']),len([r for r in state['records'] if r['role']=='user']))


class ProviderStartupTests(unittest.TestCase):
    def test_default_is_mock_and_live_options_do_not_create_store(self):
        from types import SimpleNamespace
        from pal.server import build_provider
        args=SimpleNamespace(provider='mock',access_proof=None,native_call_limit=None,mock_task_delay=0)
        self.assertEqual(build_provider(args).identity,'mock')
        for field,value in (('access_proof','missing.json'),('native_call_limit',2)):
            bad=SimpleNamespace(**vars(args)); setattr(bad,field,value)
            with self.assertRaises(ValueError): build_provider(bad)

    def test_live_startup_requires_valid_proof_before_runtime(self):
        from types import SimpleNamespace
        from pal.server import build_provider
        import time
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'proof.json'
            args=SimpleNamespace(provider='official_claude_pro',access_proof=str(path),native_call_limit=4,mock_task_delay=0)
            for value in ({'verified_at':0,'no_extra_charge':True},{'verified_at':time.time(),'no_extra_charge':False},{'verified_at':time.time(),'no_extra_charge':True,'token':'forbidden'}):
                path.write_text(json.dumps(value))
                with self.assertRaises((ValueError,RuntimeError)): build_provider(args,marker_dir=Path(temp)/'markers')
            path.write_text(json.dumps({'verified_at':time.time(),'no_extra_charge':True,'route':'official_claude_pro'}))
            provider=build_provider(args,marker_dir=Path(temp)/'markers')
            self.assertEqual(provider.status()['calls_remaining'],4)
            self.assertNotEqual(provider.identity,'mock')
            provider.stop()
