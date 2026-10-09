"""Fresh loopback mock UI, composed only from current public v5 owners."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import queue
import shutil
import sqlite3
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlsplit
import uuid

from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import ErrorCode, Grant, Limits, Result, dumps, loads
from pal.events_v5 import EventReader
from pal.host_read_v5 import HostReader
from pal.memory_v5 import MemoryStore
from pal.mock_host_v5 import MockHostSession
from pal.mock_runner_v5 import MockRunner
from pal.native_call_v5 import NativeProfile
from pal.primary_host_v5 import PrimaryHost
from pal.read_consumer_v5 import inspect_session
from pal.sanitize import sanitize
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore


def failure(code=ErrorCode.INVALID_INPUT):
    return Result.failure(code, 'Local mock request unavailable').to_json()


def _closed(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError()


def _token(value):
    if type(value) is not str or not value or len(value.encode('utf-8')) > 512:
        raise ValueError()


class LocalMockApp:
    """One disposable managed session; injected callbacks remain mock fixtures."""
    def __init__(self, primary_invoke=None, expert_invoke=None):
        for callback in (primary_invoke, expert_invoke):
            owner = getattr(callback, '__self__', callback)
            if callback is not None and (not callable(callback) or
                    type(getattr(owner, 'profile', None)) is NativeProfile):
                raise TypeError('mock fixture callable required')
        self.session_id = 'ui-' + uuid.uuid4().hex
        self._directory = Path(tempfile.mkdtemp(prefix='pal-v5-ui-'))
        self._directory.chmod(0o700)
        self._path = self._directory / 'work.sqlite'
        self._guard = MockHostSession.open(self._path)
        self._grant = Grant((), ('demo',), Limits(0, 6, 6))
        self._primary = primary_invoke or self._default_primary
        self._expert = expert_invoke or self._default_expert
        self._queue = queue.Queue(maxsize=16)
        self._lock = threading.RLock()
        self._scheduled = set()
        self._slots = 0
        self._admissions = 0
        self._closing = False
        self._closed = False
        self._running = False
        self._idle = threading.Event(); self._idle.set()
        self._stop = threading.Event()
        self._active_handlers = 0
        with self.owners() as (conn, tasks, memory, artifacts, verifier, host):
            registered = tasks.register_host()
            if not registered.ok: raise RuntimeError('mock startup unavailable')
            recovered = host.recover_turns()
            if not recovered.ok: raise RuntimeError('mock startup unavailable')
            ready = tasks.finish_startup()
            if not ready.ok: raise RuntimeError('mock startup unavailable')
        self._worker = threading.Thread(target=self._work, name='pal-v5-mock', daemon=True)
        self._worker.start()

    @contextmanager
    def owners(self):
        with self._lock:
            if self._closed: raise RuntimeError('application closed')
            self._active_handlers += 1
        conn = None
        try:
            conn = sqlite3.connect(self._path, isolation_level=None, timeout=1)
            memory = artifacts = verifier = None
            tasks = TaskStore(conn, startup_guard=self._guard, host_grant=self._grant,
                host_limits=Limits(0, 20, 20), expert_id='expert',
                source_gate=lambda c,r: memory.source_gate(c,r),
                artifact_inspect=lambda c,r: artifacts.inspect(c,r),
                artifact_lookup=lambda c,r: artifacts.lookup_saved(c,r),
                verification_inspect=lambda c,r: verifier.inspect(c,r))
            memory = MemoryStore(conn, sanitize_text=sanitize, append_event=tasks.append_event,
                                 invalidate_by_refs=tasks.invalidate_by_refs)
            artifacts = ArtifactStore(conn, authorize_save=tasks.authorize_artifact_save, source_gate=memory.source_gate)
            verifier = VerificationStore(conn, context=tasks.verification_context,
                artifact_inspect=artifacts.inspect, source_gate=memory.source_gate)
            if self._guard.phase == 'owned':
                if not tasks.register_host().ok: raise RuntimeError('mock startup unavailable')
            host = PrimaryHost(conn, guard=self._guard, memory=memory, tasks=tasks,
                request_scope=self._grant, invoke=self._primary, model_id='mock-ui-fixture')
            yield conn, tasks, memory, artifacts, verifier, host
        finally:
            if conn is not None: conn.close()
            with self._lock: self._active_handlers -= 1

    def _default_primary(self, request):
        context = loads(request['messages'][1]['text'])
        current = context['record_ref']
        text = next((r['content'] for r in context['context']['records'] if r['ref'] == current), '')
        proposal = {'kind':'none'}
        eligible = [(w,q) for w in context['candidates']['works'] if not w['text_withheld']
                    for q in w['open_questions']]
        candidates = context['candidates']
        clear = not candidates['truncated'] and not any(w['text_withheld'] for w in candidates['works'])
        if clear and len(eligible) == 1:
            work,question=eligible[0]
            proposal={'kind':'answer','work_ref':work['work_ref'],'question_id':question['id'],'record_ref':current}
        elif clear and not candidates['works'] and text == '下書きデモ':
            proposal = {'kind':'new_work', 'brief': {'purpose':'mock invitation draft',
                'target':{'repository':'demo','issue_numbers':[],'files':[]}, 'constraints':['no sending'],
                'conditions':[{'description':'saved draft','check':'artifact_saved'}], 'context_refs':[]}}
        return dumps({'reply':'テスト用mockです。「下書きデモ」で固定例を開始できます。', 'proposal':proposal})

    def _default_expert(self, context, **diagnostics):
        if not context.get('pending_inputs'):
            return {'kind':'ask','question':'開催日時を入力してください（固定mock例）。',
                    'missing_fact':'date','source_refs':[context['context'][0]['ref']]}
        return {'kind':'compose','content':'固定mock下書き\n' + '\n'.join(r['content'] for r in context['context']),
                'media_type':'text/plain','source_refs':[r['ref'] for r in context['context']]}

    @property
    def database_path(self):
        return self._path

    def _reserve_slot(self):
        with self._lock:
            if self._closing or self._slots >= 16: return False
            self._slots += 1
            self._admissions += 1
            return True

    def _release_slot(self):
        with self._lock:
            self._slots -= 1
            self._admissions -= 1

    def _enqueue_reserved(self, kind, identity):
        with self._lock:
            self._admissions -= 1
            marker = (kind, identity)
            if marker in self._scheduled:
                self._slots -= 1
                return
            self._scheduled.add(marker)
            self._queue.put_nowait(marker)
            self._idle.clear()

    def submit(self, data):
        _closed(data, ('client_key','text')); _token(data['client_key'])
        if type(data['text']) is not str or len(data['text'].encode('utf-8')) > 32768: raise ValueError()
        if not self._reserve_slot(): return failure(ErrorCode.UNAVAILABLE), 503
        retained = False
        try:
            with self.owners() as (_,tasks,memory,artifacts,verifier,host):
                result = host.submit({**data,'session_id':self.session_id})
                if result.ok and result.value.to_json()['status']=='pending':
                    retained = True
                    self._enqueue_reserved('turn', result.value.to_json()['turn_id'])
                return result.to_json(), 200
        finally:
            if not retained: self._release_slot()

    def _work(self):
        while not self._stop.is_set():
            try: kind, identity = self._queue.get(timeout=.05)
            except queue.Empty: continue
            with self._lock: self._running=True
            try:
                with self.owners() as (_,tasks,memory,artifacts,verifier,host):
                    result = host.run_turn({'turn_id':identity}) if kind=='turn' else Result.success({})
                    if result.ok and not self._stop.is_set():
                        MockRunner(tasks,memory,artifacts=artifacts,verifications=verifier).run_once(self._expert)
            except Exception:
                pass
            finally:
                self._queue.task_done()
                with self._lock:
                    self._running=False
                    self._slots -= 1
                    if self._queue.empty(): self._idle.set()

    def status(self):
        with self._lock:
            state='closed' if self._closed else 'held' if self._closing and self._running else 'closing' if self._closing else 'running' if self._running or not self._queue.empty() else 'idle'
        return {'mode':'mock','native_available':False,'session_id':self.session_id,'worker_status':state}

    def wait_idle(self, timeout=5.0):
        return self._idle.wait(timeout)

    def close(self, timeout=5.0):
        with self._lock:
            if self._closed: return True
            self._closing=True; self._stop.set()
        deadline=time.monotonic()+max(0,timeout)
        self._worker.join(max(0,deadline-time.monotonic()))
        while time.monotonic()<deadline:
            with self._lock: busy=self._active_handlers + self._admissions
            if not busy: break
            time.sleep(.01)
        with self._lock:
            if self._worker.is_alive() or self._active_handlers or self._admissions: return False
            self._closed=True
        self._guard.close(); shutil.rmtree(self._directory); self._idle.set()
        return True

    def __enter__(self): return self
    def __exit__(self,*args): self.close()


def create_server(app, port=0):
    if type(port) is not int or not 0<=port<=65535: raise ValueError('invalid loopback port')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def setup(self):
            super().setup(); self.connection.settimeout(2)
        def response(self, status, body, content_type='application/json; charset=utf-8'):
            encoded=dumps(body).encode() if content_type.startswith('application/json') else body
            self.send_response(status); self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(encoded))); self.send_header('Connection','close')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cache-Control','no-store')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers(); self.wfile.write(encoded); self.close_connection=True
        def handle_request(self, post):
            expected='127.0.0.1:'+str(self.server.server_port)
            if self.headers.get('Host')!=expected or self.headers.get('Origin') not in (None,'http://'+expected):
                return self.response(403,failure(ErrorCode.DENIED))
            try:
                if len(self.path.encode())>2048 or not self.path.startswith('/') or self.path.startswith('//'): raise ValueError()
                parsed=urlsplit(self.path)
                if parsed.scheme or parsed.netloc or parsed.fragment: raise ValueError()
                if not post and parsed.path in ('/','/app.js','/style.css') and not parsed.query:
                    file={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}[parsed.path]
                    return self.response(200,(Path(__file__).parent/'web_v5'/file[0]).read_bytes(),file[1])
                query=parse_qs(parsed.query,strict_parsing=True,keep_blank_values=True,max_num_fields=4)
                if post:
                    if parsed.query or self.headers.get('Transfer-Encoding') is not None or self.headers.get('Content-Type')!='application/json': raise ValueError()
                    lengths=self.headers.get_all('Content-Length',[])
                    if len(lengths)!=1 or not lengths[0].isascii() or not lengths[0].isdigit(): raise ValueError()
                    length=int(lengths[0])
                    if not 0<length<=65536: raise ValueError()
                    raw=self.rfile.read(length)
                    if len(raw)!=length: raise ValueError()
                    data=loads(raw.decode('utf-8','strict'))
                if post and parsed.path=='/api/turns':
                    value,status=app.submit(data)
                    return self.response(status,value)
                with app.owners() as (conn,tasks,memory,artifacts,verifier,host):
                    if not post:
                        if parsed.path=='/api/turns':
                            if set(query)!= {'turn_id'} or len(query['turn_id'])!=1: raise ValueError()
                            _token(query['turn_id'][0]); result=host.get_turn({'turn_id':query['turn_id'][0]})
                        elif query: raise ValueError()
                        elif parsed.path=='/api/status': return self.response(200,app.status())
                        elif parsed.path=='/api/works': result=tasks.list_candidates({'session_id':app.session_id,'limit':20})
                        elif parsed.path=='/api/inspection': result=inspect_session({'session_id':app.session_id},events=EventReader(conn),tasks=tasks,reader=HostReader(memory,artifacts,verifier))
                        else: return self.response(404,failure(ErrorCode.NOT_FOUND))
                    elif parsed.path=='/api/controls':
                        _closed(data,('key','work_ref','command'));_token(data['key'])
                        progress = data['command']=='resume' or type(data['command']) is dict and data['command'].get('kind')=='answer'
                        if progress and not app._reserve_slot():
                            return self.response(503,failure(ErrorCode.UNAVAILABLE))
                        retained = False
                        try:
                            result=tasks.control(data)
                            if progress and result.ok:
                                retained=True; app._enqueue_reserved('task',data['key'])
                        finally:
                            if progress and not retained: app._release_slot()
                    elif parsed.path=='/api/source-stop':
                        _closed(data,('key','source_ref'));_token(data['key']);result=memory.stop_reference(data,session_id=app.session_id)
                    else: return self.response(404,failure(ErrorCode.NOT_FOUND))
                    return self.response(200,result.to_json())
            except (ValueError,TypeError,UnicodeError): return self.response(400,failure())
            except Exception: return self.response(503,failure(ErrorCode.UNAVAILABLE))
        def do_GET(self): self.handle_request(False)
        def do_POST(self): self.handle_request(True)
        def do_OPTIONS(self): self.response(405,failure(ErrorCode.DENIED))
        def do_PUT(self): self.response(405,failure())
        def do_DELETE(self): self.response(405,failure())
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)
