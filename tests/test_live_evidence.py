import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from scripts.live_evidence import EvidenceJournal, RunWatchdog, verify_journal
from scripts.live_gate import GatedProvider
from pal.native import NativeClaude, AccessProof, ProviderUnavailable


class LiveEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'events.jsonl'

    def test_threaded_append_is_chained_and_secret_patterns_are_sanitized(self):
        with EvidenceJournal(self.path,'scripted') as journal:
            workers = [threading.Thread(target=journal.append,args=({'event':'fixture','number':i},)) for i in range(20)]
            for worker in workers: worker.start()
            for worker in workers: worker.join(2); self.assertFalse(worker.is_alive())
            journal.append({'event':'fixture','prompt':'Bearer synthetic-credential-abcdefghijklmnop'})
        records = verify_journal(self.path)
        self.assertEqual([r['sequence'] for r in records],list(range(1,22)))
        self.assertTrue(all(r['scope']=='scripted' for r in records))
        self.assertIn('[REDACTED]',records[-1]['prompt'])
        self.assertNotIn('synthetic-credential',self.path.read_text())

    def test_existing_or_symlink_journal_cannot_be_overwritten(self):
        with EvidenceJournal(self.path,'scripted') as journal: journal.append({'event':'fixture'})
        before = self.path.read_bytes()
        with self.assertRaises(FileExistsError): EvidenceJournal(self.path,'scripted')
        self.assertEqual(before,self.path.read_bytes())
        link = self.path.with_name('link.jsonl'); link.symlink_to(self.path)
        with self.assertRaises(OSError): EvidenceJournal(link,'scripted')
        with self.assertRaises(OSError): verify_journal(link)

    def test_tamper_truncation_duplicate_keys_and_unsupported_scope_are_rejected(self):
        with self.assertRaises(ValueError): EvidenceJournal(self.path,'human')
        with EvidenceJournal(self.path,'scripted') as journal: journal.append({'event':'fixture','value':1})
        original = self.path.read_bytes()
        for changed in (original.replace(b'"value":1',b'"value":2'), original[:-1],
                        original.replace(b'"value":1',b'"value":1,"value":1')):
            with self.subTest(changed=changed):
                self.path.write_bytes(changed)
                with self.assertRaises(ValueError): verify_journal(self.path)

    def test_invalid_payload_never_writes_partial_evidence(self):
        with EvidenceJournal(self.path,'scripted') as journal:
            for event in ({'event':'fixture','scope':'human'}, {'event':'fixture','value':float('nan')},
                          {'event':'fixture','value':'\ud800'}, {'event':'fixture','value':'x'*300000}):
                before = self.path.read_bytes()
                with self.assertRaises((ValueError,UnicodeError)): journal.append(event)
                self.assertEqual(before,self.path.read_bytes())
            journal.append({'event':'fixture'})
        self.assertEqual(len(verify_journal(self.path)),1)

    def test_watchdog_closes_owner_once_and_cancellation_does_not_stop_it(self):
        fired = threading.Event(); reasons = []
        class Owner:
            def close_run(self, reason): reasons.append(reason); fired.set()
        watchdog = RunWatchdog(Owner(),time.monotonic()-.01)
        watchdog.start(); self.assertTrue(fired.wait(2)); watchdog.close()
        self.assertEqual(reasons,['wall_deadline'])
        reasons.clear(); fired.clear()
        watchdog = RunWatchdog(Owner(),time.monotonic()+900)
        watchdog.start(); watchdog.close()
        self.assertEqual(reasons,[])

    def test_sigkill_keeps_fsynced_chain_and_kills_owned_native_fixture(self):
        pidfile = self.path.with_name('child.pid')
        helper = 'import os,sys,time;from pathlib import Path;Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(30)'
        parent_code = '''
import sys,time
from pathlib import Path
from pal.native import NativeClaude,AccessProof
from scripts.live_gate import GatedProvider
from scripts.live_evidence import EvidenceJournal
class Fixture(NativeClaude):
 identity='native_supervisor_fixture_only'
 def _auth_command(self):
  return [sys.executable,'-c','import json;print(json.dumps({"loggedIn":True,"authMethod":"claude.ai","subscriptionType":"pro"}))']
 def command(self):return [sys.executable,'-c',sys.argv[3],sys.argv[2]]
with EvidenceJournal(Path(sys.argv[1]),'scripted') as journal:
 gate=GatedProvider(Fixture(AccessProof(time.time(),True)),journal.append,time.monotonic()+25)
 gate.grant('fixture','request','DRAFT')
 gate.complete('DRAFT\\nsynthetic process fixture')
'''
        parent = subprocess.Popen([sys.executable,'-c',parent_code,str(self.path),str(pidfile),helper],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic()+5
            while not pidfile.exists() and time.monotonic()<deadline: time.sleep(.02)
            self.assertTrue(pidfile.exists())
            child = int(pidfile.read_text())
            os.kill(parent.pid,signal.SIGKILL); parent.communicate(timeout=5)
            self.assertEqual(parent.returncode,-signal.SIGKILL)
            records = verify_journal(self.path)
            self.assertEqual(records[-1]['event'],'call.started')
            self.assertEqual(records[-1]['scope'],'scripted')
            deadline = time.monotonic()+5; alive = True
            while time.monotonic()<deadline:
                try: os.kill(child,0)
                except ProcessLookupError: alive=False; break
                time.sleep(.02)
            self.assertFalse(alive,'owned fixture survived harness death')
        finally:
            if parent.poll() is None: parent.kill()
            parent.communicate(timeout=5)

    def test_watchdog_stops_inflight_native_fixture_and_retains_failure_chain(self):
        pidfile = self.path.with_name('native.pid')
        helper = 'import os,sys,time;from pathlib import Path;Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(30)'
        class Fixture(NativeClaude):
            identity = 'native_supervisor_fixture_only'
            def _auth_command(self):
                return [sys.executable,'-c','import json;print(json.dumps({"loggedIn":True,"authMethod":"claude.ai","subscriptionType":"pro"}))']
            def command(self): return [sys.executable,'-c',helper,str(pidfile)]
        errors = []
        with EvidenceJournal(self.path,'scripted') as journal:
            gate = GatedProvider(Fixture(AccessProof(time.time(),True)),journal.append,time.monotonic()+10)
            gate.grant('fixture','request','DRAFT')
            def call():
                try: gate.complete('DRAFT\nsynthetic process fixture')
                except ProviderUnavailable as error: errors.append(error)
            worker = threading.Thread(target=call); worker.start()
            watchdog = None
            try:
                deadline = time.monotonic()+5
                while not pidfile.exists() and time.monotonic()<deadline: time.sleep(.02)
                self.assertTrue(pidfile.exists())
                # Arm after real child startup, so the test proves in-flight kill.
                watchdog = RunWatchdog(gate,time.monotonic()+.05); watchdog.start()
                self.assertTrue(watchdog.expired.wait(2))
                worker.join(5); self.assertFalse(worker.is_alive())
                self.assertEqual(len(errors),1)
                with self.assertRaises(ProcessLookupError): os.kill(int(pidfile.read_text()),0)
            finally:
                gate.close_run('fixture_teardown')
                if watchdog: watchdog.close()
                worker.join(5)
        records = verify_journal(self.path)
        self.assertTrue(any(r['event']=='run.closed' and r['reason']=='wall_deadline' for r in records))
        self.assertTrue(any(r['event']=='call.failed' for r in records))
