import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
from pal.native import supervised_text, NativeClaude, AccessProof, ProviderUnavailable


class NativeTests(unittest.TestCase):
    def test_bounded_text_and_failure_and_timeout(self):
        output = supervised_text([sys.executable,'-c','import sys; print(sys.stdin.read())'], 'sanitized synthetic prompt', timeout=3, max_output=1000)
        self.assertIn('synthetic', output)
        with self.assertRaises(ProviderUnavailable):
            supervised_text([sys.executable,'-c','import sys;sys.stdout.write("x"*10000)'], 'test', timeout=3, max_output=500)
        with self.assertRaises(ProviderUnavailable):
            supervised_text([sys.executable,'-c','import time;time.sleep(20)'], 'test', timeout=0.2, max_output=500)
        with self.assertRaises(ProviderUnavailable):
            supervised_text([sys.executable,'-c','import sys;sys.exit(3)'], 'test', timeout=3, max_output=500)

    def test_expired_or_unverified_route_cannot_run(self):
        provider = NativeClaude(AccessProof(verified_at=0, no_extra_charge=True))
        with self.assertRaises(ProviderUnavailable):
            provider.complete('No call allowed')
        with self.assertRaises(ProviderUnavailable):
            NativeClaude(AccessProof(verified_at=time.time(), no_extra_charge=False)).complete('No call allowed')

    def test_parent_sigkill_stops_provider_group(self):
        with tempfile.TemporaryDirectory() as temp:
            pidfile=Path(temp)/'pid.txt'
            helper = "import os,sys,time; from pathlib import Path; Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(30)"
            parent_code="""\nimport sys\nfrom pal.native import supervised_text\nsupervised_text([sys.executable,'-c',sys.argv[2],sys.argv[1]],'test',timeout=25,max_output=500)\n"""
            parent=subprocess.Popen([sys.executable,'-c',parent_code,str(pidfile),helper],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                deadline=time.monotonic()+5
                while not pidfile.exists() and time.monotonic()<deadline:
                    time.sleep(.02)  # bounded observation polling, not concurrency correctness proof
                self.assertTrue(pidfile.exists())
                native_pid=int(pidfile.read_text())
                os.kill(parent.pid,signal.SIGKILL)
                parent.communicate(timeout=5)
                deadline=time.monotonic()+5
                alive=True
                while time.monotonic()<deadline:
                    try:
                        os.kill(native_pid,0)
                    except ProcessLookupError:
                        alive=False
                        break
                    time.sleep(.02)
                self.assertFalse(alive,'orphan native process survived parent death')
            finally:
                if parent.poll() is None:
                    parent.kill()
                parent.communicate(timeout=5)

    def test_native_cli_contract_has_no_tools_mcp_hooks_fallback_or_persistence(self):
        provider=NativeClaude(AccessProof(time.time(),True))
        command=provider.command()
        self.assertIn('--safe-mode',command)
        self.assertEqual(command[command.index('--tools')+1],'')
        self.assertIn('--strict-mcp-config',command)
        self.assertIn('--no-session-persistence',command)
        self.assertNotIn('--fallback-model',command)

    def test_env_keeps_os_identity_but_never_inherits_api_tokens(self):
        with patch.dict(os.environ, {'USER':'synthetic-user','LOGNAME':'synthetic-user','ANTHROPIC_API_KEY':'synthetic-forbidden','CLAUDE_CODE_OAUTH_TOKEN':'synthetic-forbidden'}):
            output=supervised_text([sys.executable,'-c',"import os;print(os.environ.get('USER')=='synthetic-user',os.environ.get('LOGNAME')=='synthetic-user','ANTHROPIC_API_KEY' in os.environ,'CLAUDE_CODE_OAUTH_TOKEN' in os.environ)"],'test',timeout=3,max_output=500)
        self.assertEqual(output,'True True False False')
