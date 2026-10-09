"""Trusted external ACP composition; importing this module never launches Native.

Fixture receipts establish consistency only. Actual qualification and entry are
host-owned; neither this bridge nor a matching profile manufactures that proof.
"""
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import pwd
import re
import selectors
import shutil
import stat
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

from pal.contracts_v5 import dumps, Ref
from pal.native_text_v5 import NativeTextBuffer
from pal.native_call_v5 import NativeProfile, NativeReturned, NativeNeverEntered

_TRANSPORT_VERSION = 'devin 3000.11.3 (9c803229faa4)'

_HEX = re.compile(r'[0-9a-f]{64}\Z')
_PIN_KEYS = {'route', 'model', 'version', 'cost_tier', 'measurement_digest',
             'selection_digest', 'runtime_hashes', 'wrapper_sha256',
             'capture_sha256', 'executable_sha256'}
_POLICY = {'mode': 'fixed', 'targets': {'implement': {'route': 'devin', 'model': 'swe-2-high'}}}


def _fail():
    raise RuntimeError('Native text unavailable') from None


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _file(path, *, private=False):
    path = Path(path)
    st = path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_nlink != 1
            or (private and stat.S_IMODE(st.st_mode) != 0o600)):
        _fail()
    return st.st_dev, st.st_ino


def _directory(path):
    path = Path(path)
    st = path.lstat()
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
            or stat.S_IMODE(st.st_mode) != 0o700):
        _fail()
    return st.st_dev, st.st_ino


def _ledger():
    path = Path(pwd.getpwuid(os.getuid()).pw_dir) / '.co-task-host' / 'capacity.db'
    _directory(path.parent)
    return path, _file(path, private=True)


def _write(path, value):
    data = _canonical(value)
    if len(data) > 262144:
        _fail()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _runtime_origin(module, runtime):
    spec = getattr(module, '__spec__', None)
    origin = getattr(module, '__file__', None)
    spec_origin = getattr(spec, 'origin', None)
    locations = []
    for paths in (getattr(spec, 'submodule_search_locations', None),
                  getattr(module, '__path__', None)):
        if paths is not None:
            paths = tuple(paths)
            if not paths:
                _fail()
            locations.extend(paths)
    if origin is None:
        # Namespace packages have no source file; every search root is authority.
        if spec_origin is not None or not locations:
            _fail()
    else:
        if spec_origin != origin:
            _fail()
        locations.append(origin)
    for location in locations:
        if (not isinstance(location, (str, os.PathLike)) or not str(location)
                or not Path(location).resolve(strict=True).is_relative_to(runtime)):
            _fail()


def _load_runtime(runtime):
    runtime = Path(runtime).resolve(strict=True)
    if (runtime / 'VERSION').read_text('utf-8').strip() != '0.4.5':
        _fail()
    for name, module in tuple(sys.modules.items()):
        if name == 'co_v4' or name.startswith('co_v4.'):
            _runtime_origin(module, runtime)
    sys.path.insert(0, str(runtime))
    try:
        modules = {name: importlib.import_module('co_v4.' + name) for name in
                   ('contracts', 'devin_host', 'adapters.devin', 'delegation', 'adapter_capacity', 'task.admission', 'task.select')}
    finally:
        sys.path.remove(str(runtime))
    for name, module in tuple(sys.modules.items()):
        if name == 'co_v4' or name.startswith('co_v4.'):
            _runtime_origin(module, runtime)
    host, cap = modules['devin_host'], modules['adapter_capacity']
    return SimpleNamespace(contracts=modules['contracts'], DevinTextHost=host.DevinTextHost,
        DevinHostConfig=host.DevinHostConfig, DevinAdapter=modules['adapters.devin'].DevinAdapter,
        DelegatedScope=modules['delegation'].DelegatedScope, CapacityLedger=cap.CapacityLedger,
        PooledAdapter=cap.PooledAdapter, gate=modules['task.admission'].gate,
        check_launch_template=host.check_launch_template, launch_environment=host.launch_environment,
        NativeCandidates=modules['task.select'].NativeCandidates)


def _metadata(executable, args, env):
    """Bound local metadata output; never a generation or task command."""
    proc = subprocess.Popen([str(executable), *args], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    data = bytearray()
    captured = 0
    try:
        with selectors.DefaultSelector() as selector:
            for stream in (proc.stdout, proc.stderr):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ)
            deadline = time.monotonic() + 30
            while selector.get_map():
                if time.monotonic() >= deadline:
                    _fail()
                for key, _ in selector.select(0.1):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        captured += len(chunk)
                        if key.fileobj is proc.stdout:
                            data.extend(chunk)
                        if captured > 1048576:
                            _fail()
            if proc.wait(timeout=max(0.01, deadline-time.monotonic())) != 0:
                _fail()
        return bytes(data)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        proc.stdout.close()
        proc.stderr.close()


def _fresh_pin(api, state_dir, executable):
    executable = Path(executable)
    official = shutil.which('devin')
    if official is None or executable.resolve(strict=True) != executable or Path(official).resolve(strict=True) != executable:
        _fail()
    selection = api.NativeCandidates(state_dir).selection('implement', 'coding', policy=copy.deepcopy(_POLICY))
    if (selection['route'], selection['model']) != ('devin', 'swe-2-high'):
        _fail()
    env = api.launch_environment()
    version = _metadata(executable, ['--version'], env).decode('utf-8', 'strict').strip()
    if not re.fullmatch(r'(?:(?i:Devin(?: CLI)? )?3000\.11\.3|devin 3000\.11\.3 \([0-9a-f]{12}\))', version):
        _fail()
    if _metadata(executable, ['version'], env).decode('utf-8', 'strict').strip() != _TRANSPORT_VERSION:
        _fail()
    auth = _metadata(executable, ['auth', 'status'], env).decode('utf-8', 'strict')
    if not re.search(r'(?im)^\s*(?:authenticated|logged in)(?:\s|:|$)', auth) or re.search(r'(?i)(?:unauthenticated|not\s+(?:\w+\s+){0,3}(?:authenticated|logged in))', auth):
        _fail()
    catalog = json.loads(_metadata(executable, ['models', 'list', '--format', 'json'], env))
    matches = [v for f in catalog.get('families', []) for v in f.get('variants', [])
               if v.get('model_uid') == 'swe-2-high']
    if len(matches) != 1 or matches[0].get('cost_tier') != 'Free':
        _fail()
    runtime = Path(sys.modules[api.NativeCandidates.__module__].__file__).resolve().parents[2]
    hashes = {}
    for path in sorted((runtime / 'co_v4').rglob('*.py')):
        _file(path)
        hashes[path.relative_to(runtime).as_posix()] = _sha(path.read_bytes())
    hashes['VERSION'] = _sha((runtime / 'VERSION').read_bytes())
    capture = Path(sys.modules[NativeTextBuffer.__module__].__file__).resolve()
    return {'route': 'devin', 'model': 'swe-2-high', 'version': '3000.11.3', 'cost_tier': 'Free',
        'measurement_digest': selection['measurement_digest'],
        'selection_digest': 'sha256:' + _sha(_canonical(selection)), 'runtime_hashes': hashes,
        'wrapper_sha256': _sha(Path(__file__).read_bytes()), 'capture_sha256': _sha(capture.read_bytes()),
        'executable_sha256': _sha(Path(executable).read_bytes())}


def _pin(value):
    if type(value) is not dict or set(value) != _PIN_KEYS:
        _fail()
    if tuple(value[k] for k in ('route', 'model', 'version', 'cost_tier')) != ('devin', 'swe-2-high', '3000.11.3', 'Free'):
        _fail()
    for k in ('measurement_digest', 'selection_digest'):
        if type(value[k]) is not str or not value[k].startswith('sha256:') or not _HEX.fullmatch(value[k][7:]):
            _fail()
    hashes = value['runtime_hashes']
    if type(hashes) is not dict or not hashes:
        _fail()
    for k, v in hashes.items():
        if (type(k) is not str or not k or Path(k).is_absolute() or '..' in Path(k).parts
                or type(v) is not str or not _HEX.fullmatch(v)):
            _fail()
    for k in ('wrapper_sha256', 'capture_sha256', 'executable_sha256'):
        if type(value[k]) is not str or not _HEX.fullmatch(value[k]):
            _fail()
    return copy.deepcopy(value)


class NativeDevinText:
    def __init__(self, *, runtime, state_dir, attempt_root, executable, credential_files, profile):
        if type(profile) is not NativeProfile:
            _fail()
        self.runtime, self.state_dir, self.attempt_root, self.executable = map(Path, (runtime, state_dir, attempt_root, executable))
        self.credentials = tuple(Path(p) for p in credential_files)
        self.profile = profile
        self._api = None

    def preflight(self):
        try:
            _directory(self.attempt_root)
            _directory(self.state_dir)
            _file(self.executable)
            if not os.access(self.executable, os.X_OK) or not 1 <= len(self.credentials) <= 8:
                _fail()
            for path in self.credentials:
                _file(path)
            _ledger()
            api = _load_runtime(self.runtime)
            pin = _pin(_fresh_pin(api, self.state_dir, self.executable))
            envelope = {'version': 'NATIVE-ACP01/1', 'profile_id': 'co-devin-acp-dynamic-text/1', 'pin': pin}
            if _sha(_canonical(envelope)) != self.profile.qualification_sha256:
                _fail()
            self._api = api
            return copy.deepcopy(pin)
        except Exception:
            _fail()

    def invoke(self, request, *, on_enter):
        entered = False
        pool = ref = host = adapter = buffer = None
        last_status = None
        stopped = False
        request_hash = None
        try:
            if (type(request) is not dict or set(request) != {'call_id','reservation_id','role','messages','source_refs','output_kind'}
                    or request['role'] != 'primary' or request['output_kind'] != 'primary_proposal' or not callable(on_enter)):
                _fail()
            for key in ('call_id', 'reservation_id'):
                if type(request[key]) is not str or not 1 <= len(request[key].encode('utf-8')) <= 512:
                    _fail()
            if type(request['messages']) is not list or not 1 <= len(request['messages']) <= 64:
                _fail()
            for msg in request['messages']:
                if (type(msg) is not dict or set(msg) != {'role','text'} or msg['role'] not in ('system','user','assistant')
                        or type(msg['text']) is not str):
                    _fail()
            if type(request['source_refs']) is not list or len(request['source_refs']) > 64:
                _fail()
            for value in request['source_refs']:
                if Ref.from_json(value).to_json() != value or value['kind'] != 'record':
                    _fail()
            prompt = dumps(request)
            if len(prompt.encode('utf-8')) > 65536:
                _fail()
            request_hash = _sha(prompt.encode('utf-8'))
            pin = self.preflight()
            api, c = self._api, self._api.contracts
            call_dir = self.attempt_root / _sha(request['call_id'].encode('utf-8'))
            call_dir.mkdir(mode=0o700)
            workspace = call_dir / 'workspace'
            workspace.mkdir(mode=0o700)
            attempt = {'run_id': 'task-cwd:' + _sha(str(workspace.resolve(strict=True)).encode('utf-8')),
                       'job_id': 'primary', 'attempt_id': uuid.uuid4().hex}
            ref = c.AttemptRef(**attempt)
            journal = call_dir / 'request.json'
            _write(journal, {'request': request, 'request_sha256': request_hash, 'prompt_sha256': request_hash,
                             'profile': self.profile.to_json(), 'pin': pin, 'attempt_ref': attempt})
            ledger_path, ledger_identity = _ledger()
            conditions = c.ExecutionConditions(model='swe-2-high', adapter='devin.acp', workspace=str(workspace),
                environment_ref='sha256:' + self.profile.qualification_sha256,
                control_evidence_refs=('sha256:' + self.profile.profile_sha256,))
            job = c.Job(run_id=ref.run_id, job_id=ref.job_id, instructions=prompt,
                        acceptance_criteria=('Return only the requested JSON text without tools.',), context_json='{}', output_candidate=False)
            native_request = c.ExecuteRequest(ref=ref, job=job, conditions=conditions)
            delegation = api.DelegatedScope(human_intent_ref='sha256:' + request_hash, attempt=ref,
                                            workspace=str(workspace), capability='devin.text.only')
            config = api.DevinHostConfig(conditions=conditions, executable=self.executable, expected_version=_TRANSPORT_VERSION,
                protected_state=(journal, ledger_path), credential_files=self.credentials, delegation=delegation)
            api.check_launch_template(config)
            host = api.DevinTextHost(config, expected_response=None)
            buffer = NativeTextBuffer(request_sha256=request_hash, profile_sha256=self.profile.profile_sha256,
                                      attempt_ref=attempt, model_id='swe-2-high')
            def verify(req, phase, native):
                host.verify(req, phase, native)
                if req != native_request:
                    _fail()
                if phase == 'session':
                    buffer.begin()
            def observe(fields, *, current_update=False):
                host.observe_model(fields, current_update=current_update)
                buffer.observe(fields, current_update=current_update)
            adapter = api.DevinAdapter(verify_host=verify, transport_factory=host.transport, desired_mode='plan',
                verify_text_cessation=host.verify_text_cessation, observe_model=observe, rpc_timeout=10)
            def factory(req):
                if req != native_request:
                    _fail()
                return adapter
            if _ledger() != (ledger_path, ledger_identity):
                _fail()
            with api.gate(workspace, state_dir=self.state_dir, binding=pin):
                if _ledger() != (ledger_path, ledger_identity):
                    _fail()
                ledger = api.CapacityLedger(ledger_path)
                pool = api.PooledAdapter('devin.acp', ledger=ledger, canonical_ledger=ledger_path, factory=factory)
                if _pin(_fresh_pin(api, self.state_dir, self.executable)) != pin:
                    _fail()
                _write(call_dir / 'entering.json', {'attempt_ref': attempt, 'request_sha256': request_hash})
                on_enter(dict(attempt))
                entered = True
                deadline = time.monotonic() + 60
                reply = pool.execute(native_request)
                if (type(reply) is not c.OperationReply or reply.ref != ref
                        or type(reply.status) is not c.OperationStatus or type(reply.reason) is not str):
                    _fail()
                never = reply.never_started
                if never is not None:
                    if (type(never) is not c.NeverStarted or never.request != native_request
                            or type(never.evidence_ref) is not str or not never.evidence_ref.strip()
                            or reply.status == c.OperationStatus.ACCEPTED or reply.resume_state is not None):
                        _fail()
                _write(call_dir / 'execute.json', {'attempt_ref': attempt, 'status': reply.status.value,
                    'reason': reply.reason, 'never_started_evidence_ref': None if never is None else never.evidence_ref})
                if never is not None:
                    raise NativeNeverEntered(request_sha256=request_hash, profile_sha256=self.profile.profile_sha256,
                                             evidence_ref=never.evidence_ref)
                if type(reply.status) is not c.OperationStatus or reply.status != c.OperationStatus.ACCEPTED:
                    _fail()
                cursor = None
                while True:
                    if time.monotonic() >= deadline:
                        _fail()
                    events = pool.events(ref, after=cursor)
                    for event in events:
                        if event.ref != ref:
                            _fail()
                        cursor = event.event_id
                    status = pool.status(ref)
                    if (type(status) is not c.StatusEvent or status.ref != ref or type(status.state) is not c.State
                            or type(status.event_id) is not str or not status.event_id
                            or (status.evidence_ref is not None and type(status.evidence_ref) is not str)):
                        _fail()
                    last_status = {'attempt_ref': dict(attempt), 'event_id': status.event_id,
                                   'state': status.state.value, 'evidence_ref': status.evidence_ref}
                    if status.state == c.State.COMPLETED:
                        break
                    if status.state not in (c.State.RUNNING, c.State.PENDING):
                        _fail()
                    time.sleep(0.02)
                stopped = True
                stop = pool.stop(ref)
                if type(stop) is not c.StopReply or stop.ref != ref or type(stop.status) is not c.StopStatus:
                    _fail()
                _write(call_dir / 'stop.json', {'attempt_ref': attempt, 'status': stop.status.value, 'evidence_ref': stop.evidence_ref})
                ending = host.observation.get('cessation')
                if (type(stop) is not c.StopReply or stop.ref != ref or type(stop.status) is not c.StopStatus or stop.status != c.StopStatus.CONFIRMED
                        or type(ending) is not dict or stop.evidence_ref != ending.get('evidence_ref')):
                    _fail()
                capture = buffer.finish(ending)
                result = NativeReturned(capture=capture, cessation=ending)
                evidence = result.validate(request_sha256=request_hash, profile=self.profile)
                _write(call_dir / 'ending.json', {'capture': capture, 'evidence': evidence})
                return result
        except NativeNeverEntered:
            raise
        except BaseException as error:
            if entered and pool is not None and ref is not None and not stopped:
                stopped = True
                try:
                    stop = pool.stop(ref)
                    if type(stop) is c.StopReply and stop.ref == ref and type(stop.status) is c.StopStatus:
                        _write(call_dir / 'stop.json', {'attempt_ref': attempt, 'status': stop.status.value, 'evidence_ref': stop.evidence_ref})
                except BaseException:
                    pass
            if entered and buffer is not None:
                try:
                    _write(call_dir / 'unqualified-output.json', buffer.unqualified_snapshot())
                except BaseException:
                    pass
            if entered and adapter is not None and host is not None:
                try:
                    try:
                        diagnostic = adapter.protocol_diagnostic(ref)
                        if diagnostic is not None and type(diagnostic) is not dict:
                            _fail()
                    except Exception:
                        diagnostic = {'status': 'unavailable'}
                    # Status pumps the protocol; only retain the ordinary loop's observation.
                    observation = copy.deepcopy(host.observation)
                    if type(observation) is not dict:
                        _fail()
                    _write(call_dir / 'diagnostic.json', {'attempt_ref': dict(attempt),
                        'last_status': copy.deepcopy(last_status), 'protocol_diagnostic': copy.deepcopy(diagnostic),
                        'host_observation': observation})
                except BaseException:
                    pass
            if not isinstance(error, Exception):
                raise
            _fail()
        finally:
            if pool is not None:
                close = getattr(pool, 'close', None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass
