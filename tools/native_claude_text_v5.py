"""Owned direct Claude print transport; import and construction never enter a model.

Qualification digests bind bytes, not a qualification verdict. An uncertain entry
retains its designated lane; local cleanup never certifies remote cancellation.
"""
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

from pal.contracts_v5 import dumps, Ref, WorkRef
from pal.native_call_v5 import NativeProfile, NativeReturned, NativeNeverEntered
from pal.native_claude_text_v5 import (
    CLAUDE_PROFILE_ID, CLAUDE_MODEL_ID, CLAUDE_CLI_VERSION,
    NativeClaudeBuffer, claude_argv,
)

_SOURCE_FILES = (
    'pal/__init__.py', 'pal/artifact_content_v5.py',
    'pal/artifact_integrity_v5.py', 'pal/artifacts_v5.py',
    'pal/contracts_v5.py', 'pal/intake_v5.py', 'pal/mock_host_v5.py',
    'pal/mock_runner_v5.py', 'pal/native_call_v5.py',
    'pal/native_claude_text_v5.py', 'pal/native_expert_runner_v5.py',
    'pal/native_text_v5.py', 'pal/primary_host_v5.py',
    'pal/primary_wire_v5.py', 'pal/sanitize.py', 'pal/tasks_v5.py',
    'tools/native_claude_text_v5.py',
)


def _fail():
    raise RuntimeError('Claude native text unavailable') from None


def _bytes(value):
    return dumps(value).encode('utf-8')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _token(value):
    return type(value) is str and 1 <= len(value.encode('utf-8')) <= 512


def _directory(path):
    st = path.lstat()
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
            or stat.S_IMODE(st.st_mode) != 0o700):
        _fail()
    return st.st_dev, st.st_ino


def _file(path, *, private=False, executable=False):
    st = path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
            or st.st_nlink != 1 or (private and stat.S_IMODE(st.st_mode) != 0o600)
            or (executable and not st.st_mode & 0o111)):
        _fail()
    return st.st_dev, st.st_ino


def _sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_raw(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    _sync(path.parent)


def _write(path, value):
    _write_raw(path, _bytes(value))


def _environment():
    value = {key: val for key, val in os.environ.items()
             if key in {'HOME', 'PATH', 'TMPDIR', 'USER', 'LOGNAME', 'LANG'}
             or key.startswith('LC_')}
    value['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = '1'
    return value


def _cleanup(child):
    # Only this transport waits on the child. Keep an unreaped leader's PID owned
    # until the final group signal, even if TERM already ended that leader.
    try:
        if child.returncode is None:
            try:
                os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            except ChildProcessError:
                # Another owner reaped it; no PGID-only signal is safe now.
                _fail()
            try:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                time.sleep(0.05)
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                time.sleep(0.05)
            finally:
                # Darwin may deny signaling an exited-only group. Ownership was
                # established above; even that error must not leak its zombie.
                child.wait(timeout=2)
    finally:
        for stream in (child.stdin, child.stdout, child.stderr):
            if stream is not None:
                stream.close()


def _observe_exit(child, deadline):
    # WNOWAIT preserves PID ownership until protocol acceptance or error cleanup.
    while True:
        status = os.waitid(os.P_PID, child.pid,
                           os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if status is not None:
            if status.si_pid != child.pid:
                _fail()
            if status.si_code == os.CLD_EXITED:
                return status.si_status
            if status.si_code in (os.CLD_KILLED, os.CLD_DUMPED):
                return -status.si_status
            _fail()
        if time.monotonic() >= deadline:
            _fail()
        time.sleep(0.01)


def _pump(child, raw, *, seconds, stdout_cap, stderr_cap, feed=None,
          stdout_file=None, stderr_file=None, combined_cap=None):
    deadline = time.monotonic() + seconds
    output, errors = bytearray(), bytearray()
    sent = 0
    eof = {'stdout': False, 'stderr': False}
    with selectors.DefaultSelector() as selector:
        for stream, name in ((child.stdout, 'stdout'), (child.stderr, 'stderr')):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        if raw:
            os.set_blocking(child.stdin.fileno(), False)
            selector.register(child.stdin, selectors.EVENT_WRITE, 'stdin')
        else:
            child.stdin.close()
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _fail()
            for key, _ in selector.select(min(remaining, 0.1)):
                stream, name = key.fileobj, key.data
                if name == 'stdin':
                    try:
                        size = os.write(stream.fileno(), raw[sent:sent + 8192])
                    except BlockingIOError:
                        continue
                    if size <= 0:
                        _fail()
                    sent += size
                    if sent == len(raw):
                        selector.unregister(stream)
                        stream.close()
                    continue
                try:
                    part = os.read(stream.fileno(), 8192)
                except BlockingIOError:
                    continue
                if not part:
                    eof[name] = True
                    selector.unregister(stream)
                    stream.close()
                    continue
                target = output if name == 'stdout' else errors
                cap = stdout_cap if name == 'stdout' else stderr_cap
                if len(target) + len(part) > cap:
                    _fail()
                target.extend(part)
                if combined_cap is not None and len(output) + len(errors) > combined_cap:
                    _fail()
                handle = stdout_file if name == 'stdout' else stderr_file
                if handle is not None:
                    handle.write(part)
                if name == 'stdout' and feed is not None:
                    feed(part)
        remaining = deadline - time.monotonic()
        if sent != len(raw) or remaining <= 0:
            _fail()
        code = _observe_exit(child, deadline)
    return bytes(output), bytes(errors), eof, code


def _metadata(executable, args, cwd, env):
    child = subprocess.Popen([str(executable), *args], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             cwd=cwd, env=env, start_new_session=True)
    try:
        out, err, eof, code = _pump(child, b'', seconds=15,
                                  stdout_cap=65536, stderr_cap=65536, combined_cap=65536)
        if code != 0 or len(out) + len(err) > 65536 or not all(eof.values()):
            _fail()
        if child.wait(timeout=2) != code:
            _fail()
        return out
    finally:
        _cleanup(child)


def _request(value, raw):
    if type(value) is not dict or not 1 <= len(raw) <= 65536:
        _fail()
    primary = {'call_id', 'reservation_id', 'role', 'messages', 'source_refs', 'output_kind'}
    role = value.get('role')
    if (type(role) is not str or role not in {'primary', 'expert'}
            or set(value) != (primary if role == 'primary' else primary | {'work_ref'})
            or value['output_kind'] != ('primary_proposal' if role == 'primary' else 'expert_action')
            or not _token(value['call_id']) or not _token(value['reservation_id'])):
        _fail()
    if role == 'expert':
        if type(value['work_ref']) is not dict:
            _fail()
        WorkRef.from_json(value['work_ref'])
    messages = value['messages']
    if type(messages) is not list or not 1 <= len(messages) <= 64:
        _fail()
    for message in messages:
        if (type(message) is not dict or set(message) != {'role', 'text'}
                or type(message['role']) is not str
                or message['role'] not in {'system', 'user', 'assistant'}
                or type(message['text']) is not str):
            _fail()
        message['text'].encode('utf-8')
    refs = value['source_refs']
    if type(refs) is not list or len(refs) > 64:
        _fail()
    for ref in refs:
        if type(ref) is not dict or Ref.from_json(ref).to_json()['kind'] != 'record':
            _fail()


class NativeClaudeText:
    def __init__(self, *, attempt_root, executable, profile):
        if (type(profile) is not NativeProfile or profile.id != CLAUDE_PROFILE_ID
                or profile.model_id != CLAUDE_MODEL_ID):
            raise ValueError('invalid Claude profile')
        try:
            lane = Path(attempt_root).absolute()
            identity = _directory(lane)
            resolved_lane = lane.resolve(strict=True)
            supplied = Path(executable).resolve(strict=True)
            _file(supplied, executable=True)
        except Exception:
            _fail()
        self._profile = profile
        self._lane = lane
        self._identity = identity
        self._resolved_lane = resolved_lane
        self._executable = supplied
        self._root = Path(__file__).absolute().parents[1]

    @property
    def profile(self):
        return self._profile

    def _pin(self):
        found = shutil.which('claude')
        if found is None or Path(found).resolve(strict=True) != self._executable:
            _fail()
        _file(self._executable, executable=True)
        hashes = {}
        for relative in _SOURCE_FILES:
            path = self._root / relative
            _file(path)
            if path.resolve(strict=True) != path:
                _fail()
            module_name = (relative[:-3].replace('/', '.') if not relative.endswith('/__init__.py')
                           else relative[:-12].replace('/', '.'))
            module = sys.modules.get(module_name)
            if module is not None:
                origin = getattr(module, '__file__', None)
                spec_origin = getattr(getattr(module, '__spec__', None), 'origin', None)
                if origin != str(path) or spec_origin != str(path):
                    _fail()
            hashes[relative] = _sha(path.read_bytes())
        pin = {'version': 'NATIVE-CLAUDE01/1', 'profile_id': CLAUDE_PROFILE_ID,
               'cli_version': CLAUDE_CLI_VERSION, 'model_id': CLAUDE_MODEL_ID,
               'executable_sha256': _sha(self._executable.read_bytes()),
               'source_hashes': hashes}
        if _sha(_bytes(pin)) != self.profile.qualification_sha256:
            _fail()
        return pin

    def preflight(self):
        try:
            pin = self._pin()
            with tempfile.TemporaryDirectory(prefix='pal-claude-meta-') as cwd:
                os.chmod(cwd, 0o700)
                env = _environment()
                version = _metadata(self._executable, ['--version'], cwd, env)
                if version.decode('utf-8').strip() != CLAUDE_CLI_VERSION + ' (Claude Code)':
                    _fail()
                raw = _metadata(self._executable, ['auth', 'status', '--json'], cwd, env)
                def closed(pairs):
                    result = {}
                    for key, val in pairs:
                        if key in result:
                            _fail()
                        result[key] = val
                    return result
                auth = json.loads(raw.decode('utf-8'), object_pairs_hook=closed,
                                  parse_constant=lambda _: _fail())
                if (type(auth) is not dict or auth.get('loggedIn') is not True
                        or auth.get('authMethod') != 'claude.ai'
                        or auth.get('apiProvider') != 'firstParty'
                        or auth.get('subscriptionType') != 'pro'):
                    _fail()
            return copy.deepcopy(pin)
        except Exception:
            _fail()

    def _lock(self):
        if (_directory(self._lane) != self._identity
                or self._lane.resolve(strict=True) != self._resolved_lane):
            _fail()
        path = self._lane / 'owner.lock'
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            _file(path, private=True)
            st = os.fstat(fd)
            if (st.st_dev, st.st_ino) != _file(path, private=True):
                _fail()
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BaseException:
            os.close(fd)
            raise

    def _release(self, active):
        fd = self._lock()
        path = self._lane / 'active.json'
        try:
            _file(path, private=True)
            if path.read_bytes() != _bytes(active):
                _fail()
            path.unlink()
            try:
                _sync(self._lane)
            except BaseException:
                if not path.exists():
                    _write(path, active)
                raise
        finally:
            os.close(fd)

    def invoke(self, request, *, on_enter):
        # Canonical hash precedes closed-shape refusal, including invalid requests.
        try:
            raw = _bytes(request)
        except Exception:
            _fail()
        request_hash = _sha(raw)
        active_path = self._lane / 'active.json'
        activated = False
        child = None
        try:
            value = json.loads(raw)
            _request(value, raw)
            if not callable(on_enter):
                _fail()
            # Refuse an occupied lane before even the bounded metadata children.
            fd = self._lock()
            try:
                if os.path.lexists(active_path):
                    _fail()
                if os.path.lexists(self._lane / _sha(value['call_id'].encode('utf-8'))):
                    _fail()
            finally:
                os.close(fd)
            self.preflight()
            fd = self._lock()
            try:
                if os.path.lexists(active_path):
                    _fail()
                pin = self._pin()
                session = str(uuid.uuid4())
                attempt = {'run_id': 'pal-claude:' + _sha(str(self._resolved_lane).encode('utf-8')),
                           'job_id': _sha(value['call_id'].encode('utf-8')),
                           'attempt_id': session}
                call_dir = self._lane / attempt['job_id']
                call_dir.mkdir(mode=0o700)
                workspace = call_dir / 'workspace'
                workspace.mkdir(mode=0o700)
                argv = claude_argv(session_id=session, executable=str(self._executable))
                argv_hash = _sha(_bytes(claude_argv(session_id=session)))
                active = {'version': 'NATIVE-CLAUDE-ACTIVE/1',
                          'request_sha256': request_hash,
                          'profile_sha256': self.profile.profile_sha256,
                          'attempt_ref': attempt}
                _write_raw(call_dir / 'request.json', raw)
                _write(call_dir / 'pin.json', pin)
                _write(call_dir / 'attempt.json', attempt)
                _write(call_dir / 'argv.json', argv)
                try:
                    _write(active_path, active)
                finally:
                    activated = os.path.lexists(active_path)
                _write(call_dir / 'entering.json', active)
            finally:
                os.close(fd)
            buffer = NativeClaudeBuffer(request_sha256=request_hash,
                                        profile_sha256=self.profile.profile_sha256,
                                        attempt_ref=attempt, session_id=session,
                                        argv_sha256=argv_hash)
            on_enter(copy.deepcopy(attempt))
            child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, cwd=workspace,
                                     env=_environment(), start_new_session=True)
            handles = []
            try:
                for name in ('stdout.bin', 'stderr.bin'):
                    stream_fd = os.open(call_dir / name, os.O_WRONLY | os.O_CREAT |
                                        os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    handles.append(os.fdopen(stream_fd, 'wb'))
                _, _, eof, code = _pump(child, raw, seconds=300,
                                       stdout_cap=1048576, stderr_cap=4096,
                                       feed=buffer.feed, stdout_file=handles[0],
                                       stderr_file=handles[1])
            finally:
                for handle in handles:
                    handle.flush()
                    os.fsync(handle.fileno())
                    handle.close()
            pair = buffer.finish(stdout_eof=eof['stdout'], stderr_eof=eof['stderr'],
                                 exit_code=code)
            returned = NativeReturned(**pair)
            returned.validate(request_sha256=request_hash, profile=self.profile)
            if child.wait(timeout=2) != code:
                _fail()
            _write(call_dir / 'ending.json', pair['cessation'])
            _write(call_dir / 'capture.json', pair['capture'])
            self._release(active)
            return returned
        except BaseException as exc:
            if child is not None:
                try:
                    _cleanup(child)
                except BaseException:
                    pass
            if not isinstance(exc, Exception):
                raise
            if not activated:
                profile_hash = self.profile.profile_sha256
                evidence = _sha(_bytes({'reason': 'before_entry',
                                        'request_sha256': request_hash,
                                        'profile_sha256': profile_hash}))
                raise NativeNeverEntered(request_sha256=request_hash,
                                         profile_sha256=profile_hash,
                                         evidence_ref='pal-claude-refusal:' + evidence) from None
            _fail()
        finally:
            if child is not None:
                for stream in (child.stdin, child.stdout, child.stderr):
                    if stream is not None and not stream.closed:
                        stream.close()
