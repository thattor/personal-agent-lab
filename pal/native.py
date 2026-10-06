"""Official tool-free Claude route, explicit fresh no-extra-charge proof required."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from .sanitize import sanitize


class ProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class AccessProof:
    verified_at: float
    no_extra_charge: bool
    route: str = 'official_claude_pro'

    def check(self):
        age = time.time() - self.verified_at
        if self.route != 'official_claude_pro' or not self.no_extra_charge or not 0 <= age <= 900:
            raise ProviderUnavailable('fresh official route/cost verification required')


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

    def __init__(self, proof):
        self.proof = proof
        self._lock = threading.Lock()
        self._calls = {}
        self._stopped = False

    def command(self):
        executable = shutil.which('claude')
        if not executable:
            raise ProviderUnavailable('official Claude CLI not installed')
        return [executable,'-p','--model','opus','--safe-mode','--permission-mode','default','--system-prompt','You are the text-only PAL assistant. Return only the requested conversational reply or draft. You have no tools and cannot execute actions. Do not emit tool invocations, plan files, execution claims, or control instructions. Canonical task state and completion are owned by the host.','--tools','','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--disable-slash-commands','--no-session-persistence','--output-format','text']

    def register(self, process, control_fd):
        with self._lock:
            if self._stopped:
                os.write(control_fd,b'x')
                raise ProviderUnavailable('native provider stopped')
            self._calls[process] = control_fd

    def unregister(self, process):
        with self._lock:
            self._calls.pop(process,None)

    def complete(self, prompt):
        self.proof.check()
        with self._lock:
            if self._stopped:
                raise ProviderUnavailable('native provider stopped')
        # Verify existing native auth via official command. Do not log account fields.
        result = subprocess.run([self.command()[0],'auth','status'],capture_output=True,text=True,timeout=10,env=native_environment())
        try:
            status = json.loads(result.stdout)
        except ValueError:
            raise ProviderUnavailable('official auth status unavailable') from None
        if result.returncode != 0 or not status.get('loggedIn') or status.get('authMethod') != 'claude.ai' or status.get('subscriptionType') not in ('pro','max'):
            raise ProviderUnavailable('existing official subscription authentication required')
        self.proof.check()
        return supervised_text(self.command(),prompt,timeout=120,max_output=65536,owner=self)

    def stop(self):
        with self._lock:
            self._stopped = True
            for control_fd in self._calls.values():
                try:
                    os.write(control_fd,b'x')
                except OSError:
                    pass
            self._calls.clear()
