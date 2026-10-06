"""Official tool-free Claude route, explicit fresh no-extra-charge proof required."""
import json
import math
import hashlib
import stat
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from .sanitize import sanitize


class ProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class AccessProof:
    verified_at: float
    no_extra_charge: bool
    route: str = 'official_claude_pro'

    _loaded_wall: float = field(default_factory=lambda: time.time(), init=False, repr=False)
    _loaded_mono: float = field(default_factory=lambda: time.monotonic(), init=False, repr=False)

    def check(self):
        try:
            numeric = type(self.verified_at) in (int,float) and math.isfinite(self.verified_at)
            if not numeric or self.no_extra_charge is not True or self.route != 'official_claude_pro':
                raise ProviderUnavailable('proof_malformed')
            age = time.time() - self.verified_at
            elapsed = time.monotonic() - self._loaded_mono
            remaining = 900 - (self._loaded_wall - self.verified_at)
            if not 0 <= age <= 900 or not 0 <= elapsed < remaining:
                raise ProviderUnavailable('proof_expired')
        except (TypeError,ValueError,OverflowError):
            raise ProviderUnavailable('proof_malformed') from None

    @classmethod
    def load(cls, path):
        def pairs(items):
            value={}
            for key,item in items:
                if key in value:
                    raise ValueError('duplicate proof key')
                value[key]=item
            return value
        def constant(_):
            raise ValueError('nonfinite proof value')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('proof must be a regular file')
            raw=stream.read(4097)
        if len(raw)>4096:
            raise ValueError('proof size bound')
        value=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=constant)
        if not isinstance(value,dict) or set(value)!={'verified_at','no_extra_charge','route'}:
            raise ValueError('invalid proof schema')
        proof=cls(**value)
        proof.check()
        return proof

    def consume(self, directory):
        self.check()
        canonical=json.dumps({'verified_at':float(self.verified_at).hex(),'no_extra_charge':True,'route':self.route},sort_keys=True,separators=(',',':'),allow_nan=False)
        name=hashlib.sha256(canonical.encode()).hexdigest()
        directory=Path(directory)
        directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        dirfd=os.open(str(directory),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            info=os.fstat(dirfd)
            if info.st_uid!=os.getuid() or info.st_mode & 0o022:
                raise ValueError('unsafe proof marker directory')
            try:
                fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=dirfd)
            except FileExistsError:
                raise ProviderUnavailable('proof_consumed') from None
            with os.fdopen(fd,'wb') as stream:
                stream.write(b'consumed\n'); stream.flush(); os.fsync(stream.fileno())
            os.fsync(dirfd)
        finally:
            os.close(dirfd)


def native_environment():
    # USER/LOGNAME are non-secret OS identity required by macOS keychain lookup.
    # Do not inherit API keys, tokens, config overrides, or third-party routes.
    environment = {'HOME':os.environ['HOME'], 'PATH':os.environ.get('PATH','/usr/bin:/bin'), 'TERM':'dumb', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC':'1'}
    for key in ('USER','LOGNAME'):
        if key in os.environ:
            environment[key] = os.environ[key]
    return environment


def supervised_text(command, prompt, timeout=120, max_output=65536, owner=None, diagnostics=None):
    prompt = sanitize(prompt)
    if len(prompt) > 131072:
        raise ProviderUnavailable('provider prompt bound exceeded')
    try:
        request = prompt.encode('utf-8',errors='strict')
    except UnicodeError:
        raise ProviderUnavailable('provider prompt encoding invalid') from None
    if len(request) > 131072:
        raise ProviderUnavailable('provider prompt byte bound exceeded')
    # CLI handles its own already-existing first-party auth. No credential values inherited.
    environment = native_environment()
    control_read, control_write = os.pipe()
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix='pal-native-') as scratch:
            environment['TMPDIR'] = scratch
            process = subprocess.Popen([sys.executable,str(Path(__file__).with_name('native_supervisor.py')),str(control_read),str(timeout),str(max_output),json.dumps(command)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,pass_fds=(control_read,),cwd=scratch,env=environment)
            os.close(control_read)
            control_read = None
            if owner is not None:
                owner.register(process,control_write)
            try:
                stdout, stderr = process.communicate(input=request,timeout=timeout+8)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.communicate(timeout=6)
                raise ProviderUnavailable('native provider deadline exceeded') from None
            if process.returncode != 0:
                if diagnostics is not None:
                    diagnostics.append(sanitize(stderr.decode('utf-8',errors='replace'))[:2000])
                raise ProviderUnavailable('native provider failed, stopped, or exceeded bound')
            if len(stdout) > max_output:
                raise ProviderUnavailable('native output bound exceeded')
            try:
                text = stdout.decode('utf-8',errors='strict').strip()
            except UnicodeError:
                raise ProviderUnavailable('native output encoding invalid') from None
            if not text:
                raise ProviderUnavailable('native provider returned empty output')
            return sanitize(text)
    finally:
        if owner is not None and process is not None:
            owner.unregister(process)
        if control_read is not None:
            os.close(control_read)
        try:
            os.close(control_write)
        except OSError:
            pass
        if process is not None and process.poll() is None:
            process.terminate()
            process.communicate(timeout=6)


class NativeClaude:
    identity = 'official_claude_opus_tool_free'

    def __init__(self, proof, max_calls=16):
        if type(max_calls) is not int or not 1<=max_calls<=32:
            raise ValueError("native call limit must be 1..32")
        self.proof = proof
        self._remaining = max_calls
        self._last_error = ""
        self._lock = threading.Lock()
        self._calls = {}
        self._stopped = False

    def command(self):
        executable = shutil.which('claude')
        if not executable:
            raise ProviderUnavailable('official Claude CLI not installed')
        return [executable,'-p','--model','opus','--safe-mode','--permission-mode','default','--system-prompt','You are the text-only PAL assistant. Return only the requested conversational reply or draft. You have no tools and cannot execute actions. Do not emit tool invocations, plan files, execution claims, or control instructions. Canonical task state and completion are owned by the host. PAL host persists accepted sanitized conversation and supplies usable remembered context in each request. You have no independent memory store. Do not claim that PAL loses memory between conversations or promise unlimited retention; describe memory only from the supplied host context. Do not claim a state change not established by host input. Keep a concise, natural tone. When helping clarify a personal project, ask for the important goal or value judgment only the user can supply, then offer to organize their answer; do not offload avoidable writing or planning chores to them. For this kind of clarification, ask the important question directly; never first tell them to write it down, make a list, or compose a one-line goal. Example: What matters most for this project? Tell me and I can organize the priorities from your answer. Do not ask about routine choices or facts already available in context. Offer conversational organization, not claims of executing work or starting a task. For thank-you drafts, express overall gratitude first, then include one or two concrete contributions only when supported by the supplied context. If details are absent, keep the thanks general; never invent achievements, obstacles, or contributions. Preserve the requested language, names, sentence count, and other draft constraints.','--tools','','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--disable-slash-commands','--no-session-persistence','--output-format','text']

    def register(self, process, control_fd):
        with self._lock:
            if self._stopped:
                os.write(control_fd,b'x')
                raise ProviderUnavailable('native provider stopped')
            self._calls[process] = control_fd

    def unregister(self, process):
        with self._lock:
            self._calls.pop(process,None)

    def status(self):
        with self._lock:
            reason='stopped' if self._stopped else ''
            if not reason:
                try:
                    self.proof.check()
                except ProviderUnavailable as error:
                    reason=str(error)
            if not reason and self._remaining==0:
                reason='budget_exhausted'
            return {'mode':'official_claude_pro','calls_remaining':self._remaining,
                    'expires_at':self.proof.verified_at+900 if type(self.proof.verified_at) in (int,float) and math.isfinite(self.proof.verified_at) else None,
                    'authorized_now':not reason,'unavailable_reason':reason,'last_error':self._last_error}

    def _auth_command(self):
        return [self.command()[0],'auth','status']

    def complete(self, prompt):
        with self._lock:
            self.proof.check()
            if self._stopped:
                raise ProviderUnavailable('stopped')
            if self._remaining==0:
                raise ProviderUnavailable('budget_exhausted')
            self._remaining-=1
        phase='auth_unavailable'
        try:
            raw=supervised_text(self._auth_command(),'',timeout=10,max_output=8192,owner=self)
            try:
                status=json.loads(raw)
            except ValueError:
                raise ProviderUnavailable('auth_unavailable') from None
            if not isinstance(status,dict) or not status.get('loggedIn') or status.get('authMethod')!='claude.ai' or status.get('subscriptionType') not in ('pro','max'):
                raise ProviderUnavailable('auth_unavailable')
            self.proof.check()
            phase='generation_unavailable'
            return supervised_text(self.command(),prompt,timeout=120,max_output=65536,owner=self)
        except Exception:
            with self._lock:
                self._last_error=phase
            raise

    def stop(self):
        with self._lock:
            self._stopped = True
            for control_fd in self._calls.values():
                try:
                    os.write(control_fd,b'x')
                except OSError:
                    pass
            self._calls.clear()
