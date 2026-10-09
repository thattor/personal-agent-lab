"""Independent UI02 contract cases: real owners and loopback, typed fixtures only."""
import http.client
import importlib
import json
from pathlib import Path
import shutil
import sqlite3
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from pal.contracts_v5 import Grant, Limits, Result, ErrorCode
import native_http_fixtures_v5 as f


class NativeHTTPTests(unittest.TestCase):
    def module(self):
        return importlib.import_module('pal.native_http_v5')

    def config(self, provider=None, **changes):
        return dict(provider=provider or f.Provider(), request_scope=Grant((), ('demo',), Limits(0, 6, 6)),
                    host_limits=Limits(0, 20, 20), **changes)

    def start(self, provider=None, **changes):
        from pal.http_v5 import create_server
        app = self.module().LocalNativeApp(**self.config(provider, **changes))
        self.addCleanup(self.dispose, app)
        server = create_server(app, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        def stop():
            server.shutdown(); server.server_close(); thread.join(3)
            self.assertFalse(thread.is_alive())
        self.addCleanup(stop)
        self.app, self.server = app, server
        self.authority = '127.0.0.1:' + str(server.server_port)
        return app

    def dispose(self, app):
        path = Path(app.database_path)
        if app.close(timeout=3):
            shutil.rmtree(path.parent)

    def request(self, method, path, data=None, headers=None):
        raw = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
        hs = {'Host': self.authority}
        if raw is not None: hs.update({'Content-Type': 'application/json', 'Content-Length': str(len(raw))})
        hs.update(headers or {})
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        try:
            conn.request(method, path, body=raw, headers=hs)
            response = conn.getresponse(); body = response.read()
            return response.status, json.loads(body)
        finally: conn.close()

    def ok(self, method, path, data=None):
        status, result = self.request(method, path, data)
        self.assertEqual(status, 200, result); self.assertIs(result['ok'], True, result)
        return result['value']

    def submit(self, key='first', text='synthetic input'):
        return self.ok('POST', '/api/turns', {'client_key': key, 'text': text})

    def works(self):
        return self.ok('GET', '/api/works')['works']

    def status(self):
        code, value = self.request('GET', '/api/status'); self.assertEqual(code, 200)
        self.assertEqual(set(value), {'mode', 'native_available', 'qualification', 'profile_id',
                                     'model_id', 'session_id', 'worker_status'})
        self.assertEqual((value['mode'], value['native_available'], value['qualification']),
                         ('native_fixture', False, 'NOT_RUN'))
        self.assertNotIn('/private/', json.dumps(value)); self.assertNotIn('sha256', json.dumps(value))
        return value

    def idle(self):
        self.assertIs(self.app.wait_idle(timeout=4), True)

    def test_config_types_marker_profile_and_mutation_refuse_without_entry(self):
        cls = self.module().LocalNativeApp
        invalid = []
        for marker in (False, 1, None):
            provider = f.Provider(); provider.fixture_only = marker; invalid.append(self.config(provider))
        provider = f.Provider(); provider.profile = object(); invalid.append(self.config(provider))
        class CallableProvider(f.Provider):
            def __call__(self): raise AssertionError('callable provider entered')
        invalid.append(self.config(CallableProvider()))
        for name in ('preflight', 'invoke'):
            provider = f.Provider(); setattr(provider, name, None); invalid.append(self.config(provider))
        invalid.extend([{**self.config(), 'request_scope': value} for value in
                        (None, Grant(('read',), ('demo',), Limits(0, 6, 6)), Grant((), ('demo',), Limits(1, 6, 6)),
                         Grant((), ('demo',), Limits(0, 21, 6)), Grant((), ('demo',), Limits(0, 6, 21)))])
        invalid.extend([{**self.config(), 'host_limits': value} for value in
                        (None, Limits(1, 20, 20), Limits(0, 21, 20), Limits(0, 20, 21))])
        invalid.extend([self.config(session_id=value) for value in ('', 'x'*513, '\ud800', 1)])
        for config in invalid:
            with self.subTest(config_types={k:type(v).__name__ for k,v in config.items()}):
                with self.assertRaises((ValueError, TypeError)): cls(**config)
                self.assertEqual(config['provider'].requests, []); self.assertEqual(config['provider'].preflights, 0)
        zero = self.config(); zero['request_scope'] = Grant((), ('demo',), Limits(0, 0, 0)); zero['host_limits'] = Limits(0, 0, 0)
        app = cls(**zero); self.addCleanup(self.dispose, app)
        self.assertEqual(zero['provider'].requests, []); self.assertEqual(zero['provider'].preflights, 0)
        from tools.native_claude_text_v5 import NativeClaudeText
        from tools.native_devin_text_v5 import NativeDevinText
        for wrapper in (NativeClaudeText, NativeDevinText):
            official = object.__new__(wrapper); official._profile = f.claude.profile()
            with patch.object(wrapper, 'preflight') as preflight, patch.object(wrapper, 'invoke') as invoke:
                with self.assertRaises((ValueError, TypeError)): cls(**self.config(official))
                preflight.assert_not_called(); invoke.assert_not_called()
        for change in ('marker', 'profile'):
            provider = f.Provider(); self.start(provider)
            if change == 'marker': provider.fixture_only = False
            else: provider.profile = f.claude.profile('8'*64)
            self.request('POST', '/api/turns', {'client_key': 'mutated', 'text': 'fixture'})
            self.idle(); self.assertEqual(provider.requests, []); self.assertEqual(provider.preflights, 0)
            self.assertEqual(self.status()['worker_status'], 'held')
            self.assertEqual(self.works(), []); self.ok('GET', '/api/inspection')
            for path, body in (('/api/controls', {'key':'after-mutation','work_ref':{'goal_id':'absent','revision':1,'epoch':0},'command':'pause'}),
                               ('/api/source-stop', {'key':'after-mutation','source_ref':{'kind':'record','id':'absent'}})):
                code, result = self.request('POST', path, body)
                self.assertEqual(code, 200); self.assertFalse(result['ok'])
                self.assertNotEqual(result['error']['code'], 'unavailable')

    def test_startup_public_order_zero_entry_and_closed_status(self):
        from pal.tasks_v5 import TaskStore
        from pal.primary_host_v5 import NativePrimaryHost
        order = []
        def wrap(name, fn):
            def call(owner, *args, **kwargs):
                order.append(name); return fn(owner, *args, **kwargs)
            return call
        provider = f.Provider()
        with patch.object(TaskStore, 'register_host', wrap('register', TaskStore.register_host)), \
             patch.object(NativePrimaryHost, 'recover_turns', wrap('recover', NativePrimaryHost.recover_turns)), \
             patch.object(TaskStore, 'finish_startup', wrap('ready', TaskStore.finish_startup)):
            self.start(provider, session_id='native-http-fixture')
        self.assertLess(order.index('register'), order.index('recover')); self.assertLess(order.index('recover'), order.index('ready'))
        self.assertEqual(self.status()['session_id'], 'native-http-fixture')
        for _ in range(2): self.works(); self.ok('GET', '/api/inspection')
        self.assertEqual(provider.requests, []); self.assertEqual(provider.preflights, 0)
        with self.app.owners() as (_, tasks, memory, artifacts, verifier, host):
            self.assertIs(type(host), NativePrimaryHost); self.assertEqual(tasks.startup_guard.phase, 'ready')

    def test_submit_replay_conflict_and_polling_do_not_duplicate_native_calls(self):
        entered, release = threading.Event(), threading.Event()
        def behavior(request):
            entered.set(); self.assertTrue(release.wait(5)); return f.primary(request)
        provider = f.Provider(behavior); self.start(provider); self.addCleanup(release.set)
        first = self.submit(); self.assertTrue(entered.wait(2)); self.assertEqual(self.submit(), first)
        code, result = self.request('POST', '/api/turns', {'client_key':'first','text':'different'})
        self.assertEqual(result['error']['code'], 'conflict')
        url = '/api/turns?' + urlencode({'turn_id':first['turn_id']})
        for _ in range(3): self.assertEqual(self.ok('GET', url)['status'], 'pending'); self.status()
        self.assertEqual(len(provider.requests), 1); release.set(); self.idle()
        self.assertEqual(self.ok('GET', url)['status'], 'committed'); self.submit(); self.idle()
        self.assertEqual(len(provider.requests), 1)

    def test_committed_primary_then_expert_same_provider_and_finite_allowance(self):
        provider = f.Provider(lambda req: f.primary(req, new=True) if req['role']=='primary' else f.compose(req))
        self.start(provider); self.submit(); self.idle()
        self.assertEqual([r['role'] for r in provider.requests], ['primary','expert'])
        work = self.works()[0]; self.assertEqual(work['state'], 'completed')
        self.assertEqual(len(work['current_artifact_refs']), 1)
        self.assertNotEqual(provider.requests[0]['call_id'], provider.requests[1]['call_id'])
        self.assertEqual(provider.requests[1]['work_ref']['goal_id'], work['work_ref']['goal_id'])
        self.assertIn('SYNTHETIC_SAVED_BODY', json.dumps(self.ok('GET', '/api/inspection')))
        provider = f.Provider(lambda req: f.primary(req, new=True))
        cfg = self.config(provider); cfg['host_limits'] = Limits(0, 20, 1)
        app = self.module().LocalNativeApp(**cfg); self.addCleanup(self.dispose, app)
        result, code = app.submit({'client_key':'limited','text':'fixture'}); self.assertEqual(code, 200)
        self.assertTrue(app.wait_idle(timeout=4)); self.assertEqual(len(provider.requests), 1)

    def test_noncommitted_and_unrecognized_primary_never_schedule_expert(self):
        from pal.primary_host_v5 import NativePrimaryHost
        from pal.native_expert_runner_v5 import NativeExpertRunner
        for status in ('failed','interrupted','pending','held','unexpected'):
            provider=f.Provider(); self.start(provider)
            with self.subTest(status=status), patch.object(NativePrimaryHost,'run_turn',return_value=Result.success({'status':status})), \
                 patch.object(NativeExpertRunner,'execute_next') as execute:
                self.submit(); self.idle(); execute.assert_not_called(); self.assertEqual(provider.requests, [])
                if status in ('held','unexpected'): self.assertEqual(self.status()['worker_status'], 'held')
        provider=f.Provider(); self.start(provider)
        with patch.object(NativePrimaryHost,'run_turn',return_value=Result.failure(ErrorCode.UNAVAILABLE,'fixture')), \
             patch.object(NativeExpertRunner,'execute_next') as execute:
            self.submit(); self.idle(); execute.assert_not_called(); self.assertEqual(self.status()['worker_status'], 'held')

    def test_primary_and_expert_unknown_latch_hold_queued_turn_and_retain_database(self):
        for role in ('primary','expert'):
            entered, release=threading.Event(),threading.Event()
            def behavior(request):
                if request['role']==role:
                    entered.set(); self.assertTrue(release.wait(5)); raise RuntimeError('SYNTHETIC_UNKNOWN')
                return f.primary(request,new=True)
            provider=f.Provider(behavior); app=self.start(provider); self.addCleanup(release.set)
            self.submit(); self.assertTrue(entered.wait(2)); queued=self.submit('queued')
            count=len(provider.requests); release.set(); self.idle()
            self.assertEqual(self.status()['worker_status'],'held'); self.assertEqual(len(provider.requests),count)
            url='/api/turns?'+urlencode({'turn_id':queued['turn_id']})
            self.assertEqual(self.ok('GET',url)['status'],'pending'); self.ok('GET','/api/inspection')
            self.assertEqual(len(provider.requests),count)
            path=Path(app.database_path); self.assertTrue(app.close(timeout=3)); self.assertTrue(path.is_file())

    def test_controls_and_source_stop_remain_responsive_during_native_callback(self):
        for command in ('pause','cancel','source-stop'):
            entered,release=threading.Event(),threading.Event()
            def behavior(request):
                if request['role']=='primary': return f.primary(request,new=True)
                entered.set(); self.assertTrue(release.wait(5)); return f.compose(request,'LATE_FORBIDDEN_BODY')
            provider=f.Provider(behavior);self.start(provider);self.addCleanup(release.set)
            self.submit();self.assertTrue(entered.wait(2));work=self.works()[0]
            if command=='source-stop':
                self.ok('POST','/api/source-stop',{'key':'stop','source_ref':provider.requests[-1]['source_refs'][0]})
            else:self.ok('POST','/api/controls',{'key':'control','work_ref':work['work_ref'],'command':command})
            self.assertFalse(release.is_set());self.assertFalse(self.app.wait_idle(timeout=.01))
            release.set();self.idle();current=self.works()[0]
            self.assertEqual(current['state'],{'pause':'paused','cancel':'cancelled','source-stop':'queued'}[command])
            if command=='source-stop':self.assertGreater(current['work_ref']['epoch'],work['work_ref']['epoch']);self.assertTrue(current['text_withheld'])
            self.assertEqual(len(provider.requests),2)
            self.assertNotIn('LATE_FORBIDDEN_BODY',json.dumps(self.ok('GET','/api/inspection')))

    def test_late_return_is_fenced_and_explicit_resume_is_one_new_expert_slice(self):
        entered,release=threading.Event(),threading.Event();expert_count=0
        def behavior(request):
            nonlocal expert_count
            if request['role']=='primary':return f.primary(request,new=True)
            expert_count+=1
            if expert_count==1:
                entered.set();self.assertTrue(release.wait(5));return f.compose(request,'OLD_FENCED')
            return f.compose(request,'RESUMED_SAVED')
        provider=f.Provider(behavior);self.start(provider);self.addCleanup(release.set)
        self.submit();self.assertTrue(entered.wait(2));work=self.works()[0]
        self.ok('POST','/api/controls',{'key':'pause','work_ref':work['work_ref'],'command':'pause'})
        release.set();self.idle();paused=self.works()[0]
        self.assertEqual(paused['state'],'paused');self.assertNotIn('OLD_FENCED',json.dumps(self.ok('GET','/api/inspection')))
        command={'key':'resume','work_ref':paused['work_ref'],'command':'resume'}
        self.ok('POST','/api/controls',command);self.idle();self.ok('POST','/api/controls',command);self.idle()
        self.assertEqual(expert_count,2);self.assertEqual(self.works()[0]['state'],'completed')
        self.assertIn('RESUMED_SAVED',json.dumps(self.ok('GET','/api/inspection')))

    def test_ask_answer_artifact_fresh_verification_and_user_view_are_connected(self):
        expert_inputs=[];bindings=[]
        def behavior(request):
            ctx=f.context(request)
            if request['role']=='primary':
                if not ctx['candidates']['works']:return f.primary(request,new=True)
                work=ctx['candidates']['works'][0];question=work['open_questions'][0]
                bindings.append((question['id'],ctx['record_ref']))
                return {'reply':'answer fixture','proposal':{'kind':'answer','work_ref':work['work_ref'],
                        'question_id':question['id'],'record_ref':ctx['record_ref']}}
            expert_inputs.append(ctx)
            if len(expert_inputs)==1:return {'kind':'ask','question':'SYNTHETIC_QUESTION','missing_fact':'date','source_refs':request['source_refs']}
            return f.compose(request,'ANSWER_BOUND_SAVED_BODY')
        provider=f.Provider(behavior);self.start(provider);self.submit();self.idle()
        waiting=self.works()[0];self.assertEqual(waiting['state'],'waiting_input')
        self.assertEqual(len(waiting['open_questions']),1);self.submit('answer','synthetic date');self.idle()
        done=self.works()[0];self.assertEqual(done['state'],'completed');self.assertEqual(done['work_ref']['goal_id'],waiting['work_ref']['goal_id'])
        link=expert_inputs[1]['pending_inputs'][0];self.assertEqual((link['question_id'],link['answer_record_ref']),bindings[0])
        from pal.host_read_v5 import HostReader
        reads=[];original=HostReader.read
        def read(owner, request, *, purpose):
            reads.append((request['ref']['kind'],purpose));return original(owner,request,purpose=purpose)
        with patch.object(HostReader,'read',read):inspection=self.ok('GET','/api/inspection')
        self.assertIn('ANSWER_BOUND_SAVED_BODY',json.dumps(inspection));self.assertIn(('artifact','user_view'),reads)
        self.assertIn(('verification','user_view'),reads);self.assertTrue(all(p=='user_view' for _,p in reads))
        self.assertEqual([r['role'] for r in provider.requests],['primary','expert','primary','expert'])

    def test_queue_sixteen_poll_pathless_status_and_bounded_retaining_close(self):
        entered,release=threading.Event(),threading.Event()
        def behavior(request):entered.set();self.assertTrue(release.wait(10));return f.primary(request)
        provider=f.Provider(behavior);app=self.start(provider);self.addCleanup(release.set)
        code, refused = self.request('POST', '/api/turns', {'client_key':'invalid','text':'fixture','profile':'foreign'})
        self.assertTrue(400 <= code < 500); self.assertFalse(refused['ok']); self.assertEqual(provider.requests, [])
        self.submit('queue-0');self.assertTrue(entered.wait(2))
        for i in range(1,16):self.submit('queue-'+str(i))
        path=Path(app.database_path)
        def snapshot():
            with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as conn:return tuple(conn.iterdump())
        before=snapshot();code,result=self.request('POST','/api/turns',{'client_key':'overflow','text':'not persisted'})
        self.assertEqual(code,503);self.assertFalse(result['ok']);self.assertEqual(snapshot(),before)
        preflight=provider.preflights
        for _ in range(2):self.status();self.works();self.ok('GET','/api/inspection')
        self.assertEqual(provider.preflights,preflight);self.assertEqual(len(provider.requests),1)
        self.assertIs(app.close(timeout=.01),False);self.assertTrue(path.is_file())
        from pal.mock_host_v5 import MockHostSession
        with self.assertRaises(RuntimeError):MockHostSession.open(path)
        release.set();self.assertTrue(app.wait_idle(timeout=4));self.assertIs(app.close(timeout=3),True)
        self.assertTrue(path.is_file());self.assertEqual(app.status()['worker_status'],'closed')


if __name__ == '__main__':
    unittest.main()
