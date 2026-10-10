"""Actual current-owner loopback fixture checks; no native provider proof."""
import http.client
import json
from pathlib import Path
import sys
import threading
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pal.http_v5 import LocalMockApp,create_server

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.app=LocalMockApp();self.server=create_server(self.app)
        self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start()
        self.addCleanup(self.cleanup)
    def cleanup(self):
        self.server.shutdown();self.server.server_close();self.thread.join(3);self.assertTrue(self.app.close())
    def request(self,path,data=None,headers=None,raw=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        body=raw if raw is not None else json.dumps(data).encode() if data is not None else None
        h={'Content-Type':'application/json'} if body is not None else {}
        h.update(headers or {});c.request('POST' if body is not None else 'GET',path,body,h)
        r=c.getresponse();status=r.status;value=r.read();c.close();return status,json.loads(value)
    def value(self,path,data=None):
        status,value=self.request(path,data);self.assertEqual(status,200);self.assertTrue(value['ok'],value);return value['value']
    def test_mock_default_and_turn_replay_no_extra_effect(self):
        status,value=self.request('/api/status');self.assertEqual((status,value['mode'],value['native_available']),(200,'mock',False))
        first=self.value('/api/turns',{'client_key':'same','text':'hello'});self.assertTrue(self.app.wait_idle())
        replay=self.value('/api/turns',{'client_key':'same','text':'hello'})
        self.assertEqual(replay['turn_id'],first['turn_id']);self.assertEqual(replay['status'],'committed')
        turn=self.value('/api/turns?turn_id='+first['turn_id']);self.assertEqual(turn['status'],'committed');self.assertIn('mock',turn['reply'])
    def test_actual_question_answer_compose_readback(self):
        self.value('/api/turns',{'client_key':'draft','text':'下書きデモ'});self.assertTrue(self.app.wait_idle())
        works=self.value('/api/works')['works'];self.assertEqual(len(works),1);work=works[0]
        self.assertEqual(work['state'],'waiting_input');question=work['open_questions'][0]
        self.value('/api/turns',{'client_key':'answer','text':'10月12日 午後2時'});self.assertTrue(self.app.wait_idle())
        self.assertTrue(self.app.wait_idle());self.assertEqual(self.value('/api/works')['works'][0]['state'],'completed')
        inspection=self.value('/api/inspection');self.assertTrue(any(read['ref']['kind']=='artifact' and read['result']['ok'] for item in inspection['items'] for read in item['reads']))
    def test_invalid_transport_and_cross_origin_do_not_submit(self):
        for raw in (b'{"client_key":"a","text":"x","text":"y"}',b'{"client_key":"a","text":NaN}',b'\xff'):
            self.assertEqual(self.request('/api/turns',raw=raw)[0],400)
        self.assertEqual(self.request('/api/turns',{'client_key':'a','text':'x'},headers={'Origin':'http://evil.invalid'})[0],403)
        self.assertEqual(self.request('/api/status',headers={'Host':'evil.invalid'})[0],403)
        self.assertEqual(self.request('/../../private')[0],404)
    def test_control_responsive_while_expert_blocked_and_close_holds(self):
        entered=threading.Event();unblock=threading.Event()
        def expert(context,**kw):
            entered.set();unblock.wait(5)
            return {'kind':'compose','content':'late','media_type':'text/plain',
                    'source_refs':[r['ref'] for r in context['context']]}
        self.app._expert=expert
        self.value('/api/turns',{'client_key':'blocked','text':'下書きデモ'})
        self.assertTrue(entered.wait(3))
        work=self.value('/api/works')['works'][0]
        result=self.value('/api/controls',{'key':'cancel-blocked','work_ref':work['work_ref'],'command':'cancel'})
        self.assertEqual(result['state'],'cancelled')
        self.assertFalse(self.app.close(timeout=.01));self.assertEqual(self.app.status()['worker_status'],'held')
        unblock.set();self.assertTrue(self.app.wait_idle(3));self.assertTrue(self.app.close())

    def test_ui_uses_text_nodes_without_dynamic_html(self):
        source=(Path(__file__).resolve().parents[1]/'pal/web_v5/app.js').read_text()
        self.assertIn('textContent',source);self.assertNotIn('innerHTML',source);self.assertNotIn('eval(',source)

if __name__=='__main__':unittest.main()
