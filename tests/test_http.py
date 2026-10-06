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
