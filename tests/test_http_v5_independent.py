"""Independent UI01 frozen HTTP acceptance; actual owners, injected mocks only."""
import http.client
import json
from pathlib import Path
import sqlite3
import threading
import unittest
from urllib.parse import urlencode


def wire(value):
    return json.dumps(value, ensure_ascii=False).encode('utf-8')


class HTTPIndependentTests(unittest.TestCase):
    def start(self, primary=None, expert=None):
        from pal.http_v5 import LocalMockApp, create_server
        self.app = LocalMockApp(primary_invoke=primary, expert_invoke=expert)
        self.addCleanup(lambda: self.app.close(timeout=3))
        self.server = create_server(self.app, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.authority = '127.0.0.1:' + str(self.server.server_port)
        return self.app

    def stop_server(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(3)
        self.assertFalse(self.thread.is_alive())

    def request(self, method, path, data=None, *, raw=None, headers=None):
        body = wire(data) if raw is None and data is not None else raw
        hs = {'Host': self.authority}
        if body is not None:
            hs.update({'Content-Type': 'application/json', 'Content-Length': str(len(body))})
        hs.update(headers or {})
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        try:
            c.request(method, path, body=body, headers=hs)
            r = c.getresponse(); payload = r.read()
            return r.status, payload
        finally:
            c.close()

    def ok(self, method, path, data=None):
        status, raw = self.request(method, path, data)
        self.assertIn(status, (200, 201, 202), raw)
        result = json.loads(raw)
        self.assertIs(result.get('ok'), True, result)
        return result['value']

    def submit(self, key='one', text='fixture input'):
        return self.ok('POST', '/api/turns', {'client_key': key, 'text': text})

    def works(self):
        return self.ok('GET', '/api/works')['works']

    @staticmethod
    def proposal(request, kind=None):
        snapshot = json.loads(request['messages'][1]['text'])
        if kind == 'new':
            proposal = {'kind': 'new_work', 'brief': {'purpose': 'fixture draft',
                'target': {'repository': 'demo', 'issue_numbers': [], 'files': []},
                'constraints': ['no sending'], 'conditions': [
                    {'description': 'draft saved', 'check': 'artifact_saved'}], 'context_refs': []}}
        else:
            proposal = {'kind': 'none'}
        return json.dumps({'reply': '明示的なテストです', 'proposal': proposal}), snapshot

    def test_fresh_mock_status_and_no_poll_inference(self):
        calls = []
        self.start(lambda req: calls.append(req) or self.proposal(req)[0])
        status, raw = self.request('GET', '/api/status')
        self.assertEqual(status, 200)
        data = json.loads(raw)
        self.assertEqual(data['mode'], 'mock'); self.assertIs(data['native_available'], False)
        self.assertEqual(data['session_id'], self.app.session_id)
        self.assertNotIn('/private/', raw.decode()); self.assertNotIn('pid', data)
        self.assertEqual(self.works(), [])
        self.ok('GET', '/api/inspection'); self.assertTrue(self.app.wait_idle(timeout=1))
        self.assertEqual(calls, [])

    def test_submit_replay_conflict_and_polling_do_not_duplicate(self):
        entered, release = threading.Event(), threading.Event(); calls = []
        def primary(req):
            calls.append(req); entered.set()
            if not release.wait(3): raise AssertionError('fixture release missing')
            return self.proposal(req)[0]
        self.start(primary); self.addCleanup(release.set)
        first = self.submit(); self.assertTrue(entered.wait(2))
        self.assertEqual(self.submit(), first)
        status, raw = self.request('POST', '/api/turns', {'client_key': 'one', 'text': 'changed'})
        result = json.loads(raw); self.assertFalse(result['ok']); self.assertEqual(result['error']['code'], 'conflict')
        query = '/api/turns?' + urlencode({'turn_id': first['turn_id']})
        for _ in range(3): self.assertEqual(self.ok('GET', query)['status'], 'pending')
        self.assertEqual(len(calls), 1)
        release.set(); self.assertTrue(self.app.wait_idle(timeout=3))
        self.assertEqual(self.ok('GET', query)['status'], 'committed')
        self.submit(); self.assertTrue(self.app.wait_idle(timeout=1)); self.assertEqual(len(calls), 1)

    def test_question_answer_same_work_and_saved_readback(self):
        inputs = []; answer_binding = []
        def primary(req):
            initial, snap = self.proposal(req, 'new')
            if not snap['candidates']['works']: return initial
            work = snap['candidates']['works'][0]; q = work['open_questions'][0]
            answer_binding.append((work['work_ref']['goal_id'], q['id'], snap['record_ref']))
            return json.dumps({'reply': '回答を保存するテストです', 'proposal': {
                'kind': 'answer', 'work_ref': work['work_ref'], 'question_id': q['id'],
                'record_ref': snap['record_ref']}})
        def expert(context, **diagnostics):
            inputs.append(context)
            if len(inputs) == 1:
                return {'kind': 'ask', 'question': '日時は？', 'missing_fact': 'date',
                        'source_refs': [v['ref'] for v in context['context']]}
            return {'kind': 'compose', 'media_type': 'text/plain', 'content': 'SAVED_DRAFT_日時は午後2時',
                    'source_refs': [v['ref'] for v in context['context']]}
        self.start(primary, expert); self.submit(); self.assertTrue(self.app.wait_idle(timeout=3))
        waiting = self.works(); self.assertEqual(len(waiting), 1)
        self.assertEqual(waiting[0]['state'], 'waiting_input'); self.assertEqual(len(waiting[0]['open_questions']), 1)
        self.submit('answer', '午後2時'); self.assertTrue(self.app.wait_idle(timeout=3))
        completed = self.works(); self.assertEqual(completed[0]['state'], 'completed')
        self.assertEqual(completed[0]['work_ref']['goal_id'], waiting[0]['work_ref']['goal_id'])
        self.assertEqual(completed[0]['open_questions'], [])
        self.assertEqual(len(inputs), 2)
        link = inputs[1]['pending_inputs'][0]
        self.assertEqual(link['question_id'], answer_binding[0][1])
        self.assertEqual(link['answer_record_ref'], answer_binding[0][2])
        inspection = self.ok('GET', '/api/inspection')
        self.assertIn('SAVED_DRAFT_日時は午後2時', json.dumps(inspection, ensure_ascii=False))

    def blocking_case(self, action):
        entered, release = threading.Event(), threading.Event(); calls = []
        def expert(context, **diagnostics):
            calls.append(context); entered.set()
            if not release.wait(4): raise AssertionError('fixture release missing')
            return {'kind': 'compose', 'media_type': 'text/plain', 'content': 'LATE_DRAFT_MUST_NOT_SAVE',
                    'source_refs': [v['ref'] for v in context['context']]}
        self.start(lambda req: self.proposal(req, 'new')[0], expert); self.addCleanup(release.set)
        self.submit(); self.assertTrue(entered.wait(2))
        work = self.works()[0]
        if action == 'source-stop':
            self.ok('POST', '/api/source-stop', {'key': 'stop', 'source_ref': calls[0]['context'][0]['ref']})
        else:
            self.ok('POST', '/api/controls', {'key': 'control', 'work_ref': work['work_ref'], 'command': action})
        self.assertFalse(release.is_set()); self.assertFalse(self.app.wait_idle(timeout=.01))
        release.set(); self.assertTrue(self.app.wait_idle(timeout=3))
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.works()[0]['state'], {'pause': 'paused', 'cancel': 'cancelled', 'source-stop': 'queued'}[action])
        if action == 'source-stop':
            current = self.works()[0]
            self.assertGreater(current['work_ref']['epoch'], work['work_ref']['epoch'])
            self.assertIs(current['text_withheld'], True)
        self.assertNotIn('LATE_DRAFT_MUST_NOT_SAVE', json.dumps(self.ok('GET', '/api/inspection')))

    def test_blocked_expert_pause_responsive_and_late_fenced(self): self.blocking_case('pause')
    def test_blocked_expert_cancel_responsive_and_late_fenced(self): self.blocking_case('cancel')
    def test_blocked_expert_source_stop_responsive_and_late_fenced(self): self.blocking_case('source-stop')

    def test_transport_rejections_have_no_effects(self):
        calls = []; self.start(lambda req: calls.append(req) or self.proposal(req)[0])
        cases = [
            (b'{"client_key":"x","client_key":"y","text":"x"}', {}),
            (b'{"client_key":"x","text":NaN}', {}),
            (b'{"client_key":"x","text":"\xff"}', {}),
            (wire({'client_key':'x','text':'x','session_id':'foreign'}), {}),
            (wire({'client_key':'x','text':'x'*32769}), {}),
            (wire({'client_key':'x'*513,'text':'x'}), {}),
            (b' '*65537, {}),
            (wire({'client_key':'x','text':'x'}), {'Origin':'https://other.invalid'}),
            (wire({'client_key':'x','text':'x'}), {'Host':'other.invalid'}),
            (wire({'client_key':'x','text':'x'}), {'Content-Type':'text/plain'}),
            (wire({'client_key':'x','text':'x'}), {'Transfer-Encoding':'chunked'}),
        ]
        for raw, headers in cases:
            with self.subTest(size=len(raw), headers=headers):
                status, body = self.request('POST', '/api/turns', raw=raw, headers=headers)
                self.assertTrue(400 <= status < 500, (status, body))
        self.assertTrue(self.app.wait_idle(timeout=1)); self.assertEqual(calls, []); self.assertEqual(self.works(), [])
        self.assertEqual(self.ok('GET', '/api/inspection')['items'], [])

    def test_routes_traversal_and_boolean_port_refused(self):
        self.start()
        for method, path in [('GET','/../pal/http_v5.py'),('GET','/%2e%2e/STATE.md'),
                             ('GET','/api/source-stop'),('OPTIONS','/api/turns'),('PUT','/api/turns')]:
            with self.subTest(method=method,path=path):
                status, body = self.request(method,path)
                self.assertTrue(400 <= status < 500, (status,body))
        from pal.http_v5 import create_server
        with self.assertRaises((ValueError,TypeError)): create_server(self.app, port=True)

    def test_context_manager_and_missing_length(self):
        from pal.http_v5 import LocalMockApp
        with LocalMockApp() as app:
            self.assertTrue(app.wait_idle(timeout=1))
            self.assertTrue(app.session_id)
        self.assertIs(app.close(timeout=1), True)
        self.start()
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        try:
            c.putrequest('POST', '/api/turns', skip_host=True)
            c.putheader('Host', self.authority)
            c.putheader('Content-Type', 'application/json')
            c.endheaders()
            response = c.getresponse()
            self.assertTrue(400 <= response.status < 500)
            response.read()
        finally:
            c.close()

    def test_shutdown_holds_active_fixture_then_cleans(self):
        entered, release = threading.Event(), threading.Event()
        def primary(req):
            entered.set()
            if not release.wait(3): raise AssertionError('fixture release missing')
            return self.proposal(req)[0]
        self.start(primary); self.addCleanup(release.set)
        self.submit(); self.assertTrue(entered.wait(2))
        path = Path(self.app.database_path)
        self.assertTrue(path.is_file())
        with self.assertRaises(AttributeError):
            self.app.database_path = str(path) + '.other'
        self.assertIs(self.app.close(timeout=.01), False)
        self.assertTrue(path.is_file())
        from pal.mock_host_v5 import MockHostSession
        with self.assertRaises(RuntimeError):
            accidental = MockHostSession.open(path)
            self.addCleanup(accidental.close)
        self.assertFalse(self.app.wait_idle(timeout=.01))
        release.set(); self.assertTrue(self.app.wait_idle(timeout=3))
        self.assertIs(self.app.close(timeout=3), True)
        self.assertFalse(path.exists())


    def test_capacity_sixteen_includes_active_and_rejects_before_persistence(self):
        entered, release = threading.Event(), threading.Event(); calls = []
        def primary(req):
            calls.append(req); entered.set()
            if not release.wait(10): raise AssertionError('fixture release missing')
            return self.proposal(req)[0]
        self.start(primary); self.addCleanup(release.set)
        first = self.submit('queue-0'); self.assertTrue(entered.wait(2))
        for i in range(1, 16):
            self.assertEqual(self.submit('queue-' + str(i))['status'], 'pending')
        self.assertEqual(len(calls), 1)
        path = Path(self.app.database_path)
        def snapshot():
            with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as conn:
                return tuple(conn.iterdump())
        before = snapshot()
        status, body = self.request('POST', '/api/turns',
                                    {'client_key': 'queue-16', 'text': 'overflow-must-not-persist'})
        self.assertEqual(status, 503, body)
        result = json.loads(body); self.assertIs(result['ok'], False)
        self.assertEqual(snapshot(), before)
        self.assertEqual(len(calls), 1)
        release.set(); self.assertTrue(self.app.wait_idle(timeout=5))
        self.assertEqual(len(calls), 16)

    def test_malformed_and_non_origin_targets_return_bounded_errors_without_effects(self):
        calls = []
        self.start(lambda req: calls.append(req) or self.proposal(req)[0])
        for target in ('http://[', 'http://foreign.invalid/api/turns', '//foreign.invalid/api/turns'):
            with self.subTest(target=target):
                status, body = self.request('POST', target, {'client_key': 'invalid-target', 'text': 'must not persist'})
                self.assertTrue(400 <= status < 500, (status, body))
                result = json.loads(body)
                self.assertIs(result.get('ok'), False)
                self.assertLessEqual(len(body), 1024)
                self.assertNotIn(b'/private/', body)
                self.assertNotIn(b'Traceback', body)
        self.assertTrue(self.app.wait_idle(timeout=1))
        self.assertEqual(calls, [])
        self.assertEqual(self.works(), [])
        self.assertEqual(self.ok('GET', '/api/inspection')['items'], [])

    def test_demo_held_close_reports_nonzero_without_private_path(self):
        import contextlib
        import importlib.util
        import io
        from unittest.mock import patch
        import pal.http_v5
        source = Path(pal.http_v5.__file__).resolve().parents[1] / 'scripts' / 'demo_http_v5.py'
        spec = importlib.util.spec_from_file_location('ui_demo_under_review', source)
        demo = importlib.util.module_from_spec(spec); spec.loader.exec_module(demo)
        class App:
            def close(self): return False
        class Server:
            server_port = 12345
            def serve_forever(self): raise KeyboardInterrupt()
            def server_close(self): pass
        out, err = io.StringIO(), io.StringIO()
        with patch.object(demo, 'LocalMockApp', return_value=App()), \
             patch.object(demo, 'create_server', return_value=Server()), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = demo.main()
        self.assertIs(type(status), int)
        self.assertNotEqual(status, 0)
        self.assertTrue(err.getvalue().strip())
        self.assertNotIn('/private/', err.getvalue())
        self.assertNotIn('Traceback', err.getvalue())

    def test_security_headers_on_static_status_and_refusal(self):
        self.start()
        for path in ('/', '/api/status', '/not-a-route'):
            with self.subTest(path=path):
                c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
                try:
                    c.request('GET', path, headers={'Host': self.authority})
                    response = c.getresponse(); response.read()
                    csp = response.getheader('Content-Security-Policy', '')
                    directives = {part.strip() for part in csp.split(';')}
                    self.assertIn("frame-ancestors 'none'", directives)
                    self.assertIn("base-uri 'none'", directives)
                    self.assertEqual(response.getheader('X-Content-Type-Options'), 'nosniff')
                    self.assertEqual(response.getheader('Cache-Control'), 'no-store')
                    self.assertEqual(response.getheader('Referrer-Policy'), 'no-referrer')
                finally:
                    c.close()


if __name__ == '__main__':
    unittest.main()
