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
        with self.assertRaises(ProviderUnavailable):
            NativeClaude(AccessProof(verified_at=0, no_extra_charge=True)).complete('No call allowed')
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


class BoundedNativeTests(unittest.TestCase):
    def test_malformed_proof_never_authorizes(self):
        for value in (True, None, 'now', float('inf'), float('nan')):
            with self.subTest(value=value), self.assertRaises(ProviderUnavailable):
                AccessProof(value, True).check()
        with self.assertRaises(ProviderUnavailable):
            AccessProof(time.time(), 'true').check()

    def test_concurrent_call_budget_counts_failures_and_never_runs_over_limit(self):
        from concurrent.futures import ThreadPoolExecutor
        provider=NativeClaude(AccessProof(time.time(),True),max_calls=2)
        auth=json.dumps({'loggedIn':True,'authMethod':'claude.ai','subscriptionType':'pro'})
        def supervised(command,*args,**kwargs):
            if command[-2:]==['auth','status']:
                return auth
            raise ProviderUnavailable('synthetic failure')
        def run(_):
            try:
                return provider.complete('synthetic')
            except ProviderUnavailable:
                return 'denied'
        with patch('pal.native.supervised_text',side_effect=supervised) as model:
            with ThreadPoolExecutor(max_workers=8) as pool:
                self.assertEqual(list(pool.map(run,range(8))),['denied']*8)
            self.assertEqual(model.call_count,4)
            self.assertEqual(sum(call.args[0][-2:]==['auth','status'] for call in model.call_args_list),2)
        status=provider.status()
        self.assertEqual(status['calls_remaining'],0)
        self.assertFalse(status['authorized_now'])

    def test_expiry_blocks_auth_subprocess_and_status_is_read_only(self):
        provider=NativeClaude(AccessProof(time.time(),True),max_calls=2)
        with patch('pal.native.time.time',return_value=time.time()+901), patch('pal.native.supervised_text') as auth:
            self.assertFalse(provider.status()['authorized_now'])
            with self.assertRaises(ProviderUnavailable):
                provider.complete('synthetic')
            auth.assert_not_called()
        self.assertEqual(provider.status()['calls_remaining'],2)

    def test_clock_rewind_cannot_extend_proof_and_status_never_calls_provider(self):
        with patch('pal.native.time.time',return_value=10000), patch('pal.native.time.monotonic',return_value=500):
            provider=NativeClaude(AccessProof(10000,True))
        with patch('pal.native.time.time',return_value=10001), patch('pal.native.time.monotonic',return_value=1401), patch('pal.native.supervised_text') as call:
            for _ in range(1000):
                self.assertEqual(provider.status()['unavailable_reason'],'proof_expired')
            with self.assertRaises(ProviderUnavailable): provider.complete('denied')
            call.assert_not_called()

    def test_expiry_during_auth_consumes_slot_without_generation(self):
        proof=AccessProof(time.time(),True)
        provider=NativeClaude(proof,max_calls=2)
        def auth(*args,**kwargs):
            object.__setattr__(proof,'verified_at',0)
            return json.dumps({'loggedIn':True,'authMethod':'claude.ai','subscriptionType':'pro'})
        with patch('pal.native.supervised_text',side_effect=auth) as call:
            with self.assertRaises(ProviderUnavailable): provider.complete('denied')
            self.assertEqual(call.call_count,1)
        self.assertEqual(provider.status()['calls_remaining'],1)

    def test_proof_consumption_is_canonical_and_rejects_unsafe_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path=root/'proof.json'; markers=root/'markers'
            timestamp=int(time.time())
            value={'verified_at':timestamp,'no_extra_charge':True,'route':'official_claude_pro'}
            path.write_text(json.dumps(value))
            AccessProof.load(path).consume(markers)
            value['verified_at']=float(timestamp)
            path.write_text(json.dumps(value))
            with self.assertRaises(ProviderUnavailable): AccessProof.load(path).consume(markers)
            for raw in ('{"verified_at":0,"verified_at":1,"no_extra_charge":true,"route":"official_claude_pro"}', '{"verified_at":NaN,"no_extra_charge":true,"route":"official_claude_pro"}'):
                path.write_text(raw)
                with self.assertRaises(ValueError): AccessProof.load(path)
            link=root/'link'; link.symlink_to(path)
            with self.assertRaises(OSError): AccessProof.load(link)
            directory_link=root/'directory-link'; directory_link.symlink_to(markers)
            with self.assertRaises(OSError): AccessProof(time.time(),True).consume(directory_link)

    def test_shutdown_during_auth_kills_owned_child_and_consumes_slot(self):
        import threading
        with tempfile.TemporaryDirectory() as temp:
            pidfile=Path(temp)/'pid'
            helper='import os,sys,time;from pathlib import Path;Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(20)'
            provider=NativeClaude(AccessProof(time.time(),True),max_calls=2)
            outcomes=[]
            def run():
                try: provider.complete('synthetic')
                except ProviderUnavailable: outcomes.append('stopped')
            with patch.object(provider,'_auth_command',return_value=[sys.executable,'-c',helper,str(pidfile)]):
                thread=threading.Thread(target=run); thread.start()
                try:
                    deadline=time.monotonic()+5
                    while not pidfile.exists() and time.monotonic()<deadline: time.sleep(.02)
                    self.assertTrue(pidfile.exists())
                    pid=int(pidfile.read_text())
                    provider.stop(); thread.join(10)
                    self.assertFalse(thread.is_alive())
                    self.assertEqual(outcomes,['stopped'])
                    with self.assertRaises(ProcessLookupError): os.kill(pid,0)
                    self.assertEqual(provider.status()['calls_remaining'],1)
                finally:
                    provider.stop(); thread.join(12)

    def test_wall_jump_and_sleep_expire_without_monotonic_progress(self):
        with patch('pal.native.time.time',return_value=10000), patch('pal.native.time.monotonic',return_value=500):
            proof=AccessProof(10000,True)
        for wall in (9999,10901):
            with patch('pal.native.time.time',return_value=wall), patch('pal.native.time.monotonic',return_value=500), self.assertRaises(ProviderUnavailable): proof.check()

    def test_expiry_budget_and_auth_failures_are_visible_without_mock_fallback(self):
        from pal.runtime import Runtime
        for reason in ('expired','exhausted','auth'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                provider=NativeClaude(AccessProof(time.time(),True),max_calls=2)
                if reason=='exhausted':
                    with patch('pal.native.supervised_text',side_effect=ProviderUnavailable('synthetic')):
                        for _ in range(2):
                            with self.assertRaises(ProviderUnavailable): provider.complete('consume')
                with patch('pal.native.time.time',return_value=time.time()+(901 if reason=='expired' else 0)), patch('pal.native.supervised_text',return_value='{"loggedIn":false}') as call:
                    runtime=Runtime(Path(temp)/'state.db',provider=provider)
                    try:
                        response=runtime.submit('chat','Hello')['response'].result(timeout=2)
                        self.assertIn('反映できません',response['content'])
                        draft=runtime.submit('draft','Make a draft')
                        draft['response'].result(timeout=2)
                        self.assertEqual(runtime.store.operation('draft')['result']['primary_status'],'rejected')
                        self.assertEqual(runtime.store.inspect()['goals'],[])
                        self.assertEqual(runtime.store.inspect()['receipts'],[])
                        self.assertNotEqual(runtime.provider.identity,'mock')
                        self.assertEqual(call.call_count,2 if reason=='auth' else 0)
                    finally: runtime.close()


class ExtendedNativeSessionTests(unittest.TestCase):
    def fresh_provider(self, seconds=8100, calls=2):
        with patch('pal.native.time.time',return_value=10000), patch('pal.native.time.monotonic',return_value=500):
            return NativeClaude(AccessProof(10000,True),max_calls=calls,session_seconds=seconds)

    def test_duration_is_strict_and_bounded_at_both_api_boundaries(self):
        for value in (True,False,None,'900',900.0,0,-1,8101,float('inf')):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): self.fresh_provider(value)
                with self.assertRaises(ValueError): AccessProof(time.time(),True).check(value)
        for value in (1,900,8100):
            with patch('pal.native.time.time',return_value=10000), patch('pal.native.time.monotonic',return_value=500):
                provider=self.fresh_provider(value)
                self.assertTrue(provider.status()['authorized_now'])
                self.assertEqual(provider.status()['expires_at'],10000+value)

    def test_complete_after_fifteen_minutes_keeps_the_same_budget(self):
        provider=self.fresh_provider(calls=1)
        auth=json.dumps({'loggedIn':True,'authMethod':'claude.ai','subscriptionType':'pro'})
        with patch('pal.native.time.time',return_value=11801), patch('pal.native.time.monotonic',return_value=2301), patch('pal.native.supervised_text',side_effect=[auth,'bounded output']) as calls:
            self.assertTrue(provider.status()['authorized_now'])
            self.assertEqual(provider.complete('synthetic'),'bounded output')
            self.assertEqual([c.kwargs['timeout'] for c in calls.call_args_list],[10,120])
            self.assertEqual(provider.status()['calls_remaining'],0)
            self.assertEqual(provider.status()['unavailable_reason'],'budget_exhausted')
            with self.assertRaisesRegex(ProviderUnavailable,'budget_exhausted'): provider.complete('no extra call')
            self.assertEqual(calls.call_count,2)
            with self.assertRaisesRegex(ProviderUnavailable,'proof_expired'): provider.proof.check()

    def test_extension_does_not_admit_a_stale_startup_proof(self):
        with patch('pal.native.time.time',return_value=10901), patch('pal.native.time.monotonic',return_value=500):
            proof=AccessProof(10000,True)
            proof.check(8100)
            with self.assertRaisesRegex(ProviderUnavailable,'proof_expired'):
                NativeClaude(proof,session_seconds=8100)

    def test_extended_expiry_and_clock_fences_reject_before_auth(self):
        provider=self.fresh_provider()
        for wall,mono in ((18101,500),(10001,8601),(9999,500),(10000,499),(18100,8600)):
            with self.subTest(wall=wall,mono=mono), patch('pal.native.time.time',return_value=wall), patch('pal.native.time.monotonic',return_value=mono), patch('pal.native.supervised_text') as calls:
                self.assertEqual(provider.status()['unavailable_reason'],'proof_expired')
                with self.assertRaisesRegex(ProviderUnavailable,'proof_expired'): provider.complete('denied')
                self.assertEqual(provider.status()['calls_remaining'],2)
                calls.assert_not_called()
        with patch('pal.native.time.time',return_value=18100), patch('pal.native.time.monotonic',return_value=8599):
            self.assertTrue(provider.status()['authorized_now'])

    def test_extended_expiry_during_auth_burns_only_the_reserved_slot(self):
        provider=self.fresh_provider()
        with patch('pal.native.time.time',return_value=18099) as wall, patch('pal.native.time.monotonic',return_value=8599) as mono:
            def auth(*args,**kwargs):
                wall.return_value=18101; mono.return_value=8601
                return json.dumps({'loggedIn':True,'authMethod':'claude.ai','subscriptionType':'pro'})
            with patch('pal.native.supervised_text',side_effect=auth) as calls:
                with self.assertRaisesRegex(ProviderUnavailable,'proof_expired'): provider.complete('denied')
                self.assertEqual(calls.call_count,1)
                self.assertEqual(provider.status()['calls_remaining'],1)
