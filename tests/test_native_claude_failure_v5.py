"""Prospective private observations; fake CLI children, never official Claude."""
import copy
import errno
import json
import os
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_native_claude_provider_v5 as existing
import native_claude_fixtures_v5 as f
from pal.native_call_v5 import NativeNeverEntered

KEYS = {'version', 'request_sha256', 'profile_sha256', 'attempt_ref', 'phase',
        'primary_error', 'cleanup_status', 'cleanup_error', 'observed_stdout_eof',
        'observed_stderr_eof', 'observed_exit_code', 'ending_write_completed',
        'capture_write_completed'}
PHASES = {'durable_admission', 'buffer', 'entering_hook', 'spawn', 'capture_streams',
          'pump', 'close_streams', 'finish', 'validate', 'owned_wait', 'save_ending',
          'save_capture', 'release'}
CANARY = 'PRIVATE_FAILURE_CANARY_日本語'

class ClaudeFailureTests(unittest.TestCase):
    # Reuse setup methods, without inheriting or discovering the old TestCase.
    setup_provider = existing.ClaudeProviderTests.setup_provider
    request = existing.ClaudeProviderTests.request
    hook = existing.ClaudeProviderTests.hook
    invoke = existing.ClaudeProviderTests.invoke
    track_children = existing.ClaudeProviderTests.track_children
    reaped = existing.ClaudeProviderTests.reaped

    def call_dir(self):
        return self.lane / f.digest(self.request()['call_id'].encode())

    def failure(self, *, phase=None, cleanup='succeeded'):
        path = self.call_dir() / 'failure.json'
        self.assertTrue(path.is_file(), 'activated failure must retain prospective observation')
        raw = path.read_bytes()
        self.assertLessEqual(len(raw), 4096)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        row = json.loads(raw)
        self.assertEqual(raw, f.canonical(row))
        self.assertEqual(set(row), KEYS)
        self.assertEqual(row['version'], 'NATIVE-CLAUDE-FAILURE/1')
        self.assertEqual(row['request_sha256'], f.digest((self.call_dir()/'request.json').read_bytes()))
        self.assertEqual(row['profile_sha256'], self.profile.profile_sha256)
        self.assertEqual(row['attempt_ref'], json.loads(self.enter.read_text()))
        self.assertIn(row['phase'], PHASES)
        if phase: self.assertEqual(row['phase'], phase)
        self.assertEqual(row['cleanup_status'], cleanup)
        for key in ('primary_error', 'cleanup_error'):
            value = row[key]
            if value is None:
                self.assertEqual(key, 'cleanup_error'); self.assertNotEqual(cleanup, 'failed')
                continue
            self.assertEqual(set(value), {'kind', 'errno', 'sites'})
            self.assertIs(type(value['kind']), str)
            self.assertTrue(value['errno'] is None or type(value['errno']) is int)
            self.assertIs(type(value['sites']), list); self.assertLessEqual(len(value['sites']), 8)
            for site in value['sites']:
                self.assertEqual(set(site), {'file', 'line'})
                self.assertIn(site['file'], self.module._SOURCE_FILES)
                self.assertIs(type(site['line']), int); self.assertGreater(site['line'], 0)
        for key in ('ending_write_completed', 'capture_write_completed'):
            self.assertIs(type(row[key]), bool)
        for key in ('observed_stdout_eof', 'observed_stderr_eof'):
            self.assertTrue(row[key] is None or type(row[key]) is bool)
        self.assertTrue(row['observed_exit_code'] is None or type(row['observed_exit_code']) is int)
        self.assertNotIn(CANARY, raw.decode())
        self.assertNotIn(str(self.lane), raw.decode())
        self.assertTrue((self.lane/'active.json').is_file())
        return row

    def generic_failure(self, run):
        with self.assertRaises(RuntimeError) as caught: run()
        self.assertEqual(str(caught.exception), 'Claude native text unavailable')
        self.assertTrue(caught.exception.__suppress_context__)

    def test_feed_and_finish_failure_record_after_one_owned_cleanup(self):
        for where in ('feed', 'finish'):
            with self.subTest(where=where):
                self.setup_provider()
                original = self.module._cleanup
                with self.track_children(), patch.object(self.module, '_cleanup', wraps=original) as cleanup, \
                     patch.object(self.module.NativeClaudeBuffer, where, side_effect=ValueError(CANARY)):
                    self.generic_failure(self.invoke)
                self.reaped(); self.assertEqual(sum(c.args[0] in self.children for c in cleanup.call_args_list), 1)
                row = self.failure(phase='pump' if where=='feed' else 'finish')
                self.assertEqual(row['primary_error']['kind'], 'ValueError')
                self.assertFalse(row['ending_write_completed']); self.assertFalse(row['capture_write_completed'])

    def test_primary_and_cleanup_errors_are_separate_with_exact_errno_kind(self):
        self.setup_provider(); original = self.module._cleanup
        def cleanup(child):
            original(child)
            if not self.enter.exists(): return
            raise PermissionError(errno.EPERM, CANARY)
        class Derived(ValueError): pass
        with self.track_children(), patch.object(self.module, '_cleanup', side_effect=cleanup) as cleaned, \
             patch.object(self.module.NativeClaudeBuffer, 'finish', side_effect=Derived(CANARY)):
            self.generic_failure(self.invoke)
        self.reaped(); self.assertEqual(sum(c.args[0] in self.children for c in cleaned.call_args_list), 1)
        row = self.failure(phase='finish', cleanup='failed')
        self.assertEqual(row['primary_error']['kind'], 'OtherError')
        self.assertIsNone(row['primary_error']['errno'])
        self.assertEqual(row['cleanup_error']['kind'], 'PermissionError')
        self.assertEqual(row['cleanup_error']['errno'], errno.EPERM)

    def test_interrupt_identity_child_and_no_child_cleanup_boundaries(self):
        for kind in (KeyboardInterrupt, SystemExit):
            for child_exists in (False, True):
                with self.subTest(kind=kind.__name__, child=child_exists):
                    self.setup_provider(); error=kind(CANARY); original=self.module._cleanup
                    def hook(attempt):
                        self.hook(attempt)
                        if not child_exists: raise error
                    with patch.object(self.module.shutil, 'which', return_value=str(self.exe)), \
                         patch.object(self.module, '_cleanup', wraps=original) as cleanup, \
                         patch.object(self.module.NativeClaudeBuffer, 'feed', side_effect=error), \
                         self.track_children(), self.assertRaises(kind) as caught:
                        self.provider.invoke(self.request(), on_enter=hook)
                    self.assertIs(caught.exception, error)
                    self.assertEqual(sum(c.args[0] in self.children for c in cleanup.call_args_list), int(child_exists))
                    if child_exists: self.reaped()
                    row=self.failure(phase='pump' if child_exists else 'entering_hook',
                                     cleanup='succeeded' if child_exists else 'not_attempted')
                    self.assertEqual(row['primary_error']['kind'],kind.__name__)

    def test_diagnostic_write_exception_or_interrupt_never_replaces_selected_outcome(self):
        for primary in (ValueError(CANARY), KeyboardInterrupt(CANARY), SystemExit(CANARY)):
            for diagnostic in (OSError(errno.ENOSPC, CANARY), KeyboardInterrupt(CANARY)):
                with self.subTest(primary=type(primary).__name__, diagnostic=type(diagnostic).__name__):
                    self.setup_provider(); original=self.module._write; cleanup_original=self.module._cleanup
                    attempts=[]
                    def write(path, value):
                        if path.name=='failure.json':
                            attempts.append(path); raise diagnostic
                        return original(path,value)
                    with self.track_children(), patch.object(self.module, '_write', side_effect=write), \
                         patch.object(self.module, '_cleanup', wraps=cleanup_original) as cleanup, \
                         patch.object(self.module.NativeClaudeBuffer,'feed',side_effect=primary):
                        if isinstance(primary, Exception): self.generic_failure(self.invoke)
                        else:
                            with self.assertRaises(type(primary)) as caught: self.invoke()
                            self.assertIs(caught.exception,primary)
                    self.assertEqual(len(attempts),1); self.assertEqual(sum(c.args[0] in self.children for c in cleanup.call_args_list),1)
                    self.assertTrue((self.lane/'active.json').exists())
                    self.assertFalse((self.call_dir()/'failure.json').exists())

    def test_observations_masking_and_post_wait_write_flags_are_truthful(self):
        for mode in ('pump_close', 'finish', 'save_capture', 'release'):
            with self.subTest(mode=mode):
                self.setup_provider(); original_write=self.module._write; original_fsync=self.module.os.fsync
                pumping=[False]; masked=[False]; original_pump=self.module._pump
                def pump(*args,**kwargs):
                    if not self.enter.exists(): return original_pump(*args,**kwargs)
                    pumping[0]=True; raise ValueError(CANARY)
                def sync(fd):
                    if pumping[0] and not masked[0]: masked[0]=True; raise OSError(errno.EIO,CANARY)
                    return original_fsync(fd)
                def write(path,value):
                    if mode=='save_capture' and path.name=='capture.json': raise OSError(errno.EIO,CANARY)
                    return original_write(path,value)
                from contextlib import ExitStack
                with ExitStack() as stack:
                    stack.enter_context(patch.object(self.module,'_write',side_effect=write))
                    if mode=='pump_close':
                        stack.enter_context(patch.object(self.module,'_pump',side_effect=pump))
                        stack.enter_context(patch.object(self.module.os,'fsync',side_effect=sync))
                    if mode=='finish': stack.enter_context(patch.object(self.module.NativeClaudeBuffer,'finish',side_effect=ValueError(CANARY)))
                    if mode=='release': stack.enter_context(patch.object(self.provider,'_release',side_effect=OSError(errno.EIO,CANARY)))
                    self.generic_failure(self.invoke)
                row=self.failure(phase={'pump_close':'close_streams','finish':'finish','save_capture':'save_capture','release':'release'}[mode])
                for key in ('observed_stdout_eof','observed_stderr_eof','observed_exit_code'):
                    if mode=='pump_close': self.assertIsNone(row[key])
                    else: self.assertEqual(row[key],0 if key=='observed_exit_code' else True)
                self.assertEqual(row['ending_write_completed'],mode in ('save_capture','release'))
                self.assertEqual(row['capture_write_completed'],mode=='release')
                if mode in ('save_capture','release'):
                    self.assertTrue((self.call_dir()/'ending.json').exists())

    def test_success_and_pre_activation_refusal_add_no_failure_record(self):
        self.setup_provider(); value=self.invoke(); value.validate(request_sha256=f.digest(f.canonical(self.request())),profile=self.profile)
        self.assertFalse(list(self.lane.rglob('failure.json'))); self.assertFalse((self.lane/'active.json').exists())
        with self.assertRaises(NativeNeverEntered) as caught: self.invoke()
        self.assertEqual(caught.exception.evidence_ref,f.refusal(self.request(),self.profile).evidence_ref)
        self.assertFalse(list(self.lane.rglob('failure.json'))); self.assertEqual(self.starts.read_text(),'start\n')

    def test_private_bounded_closed_record_and_exclusive_existing_retention(self):
        for existing_file in (False, True):
            with self.subTest(existing=existing_file):
                self.setup_provider('bad_protocol')
                self.exe.write_text(self.exe.read_text().replace("'text': 'fixture'", "'text': "+repr(CANARY)))
                pin=f.pin(existing.ROOT,self.exe); self.profile=f.profile(f.digest(f.canonical(pin)))
                self.provider=self.module.NativeClaudeText(executable=self.exe,attempt_root=self.lane,profile=self.profile)
                request=self.request(); request['messages'][1]['text']=CANARY
                original_env=self.module._environment
                def environment(): return {**original_env(),'LC_FIXTURE_CANARY':CANARY}
                def hook(attempt):
                    self.hook(attempt)
                    if existing_file:
                        path=self.call_dir()/'failure.json'; path.write_bytes(b'original private fixture');path.chmod(0o600)
                with patch.object(self.module,'_environment',side_effect=environment),patch.object(self.module.shutil,'which',return_value=str(self.exe)):
                    self.generic_failure(lambda:self.provider.invoke(request,on_enter=hook))
                if existing_file:self.assertEqual((self.call_dir()/'failure.json').read_bytes(),b'original private fixture')
                else:
                    row=self.failure(phase='finish'); self.assertEqual(row['primary_error']['kind'],'RuntimeError')
                    self.assertTrue(row['primary_error']['sites'])
                    self.assertNotIn('fixture output',(self.call_dir()/'failure.json').read_text())
                self.assertTrue((self.lane/'active.json').exists())
                frames=[json.loads(line) for line in (self.call_dir()/'stdout.bin').read_bytes().splitlines()]
                self.assertIn(CANARY,json.dumps(frames,ensure_ascii=False))
        # Only exact fixed-source traceback frames count; last8, in original order.
        self.setup_provider()
        ns={'error':ValueError(CANARY)}
        code='def recurse(n):\n if n: return recurse(n-1)\n raise error\n'
        exec(compile(code,str(self.provider._root/'tools/native_claude_text_v5.py'),'exec'),ns)
        def hook(attempt): self.hook(attempt); ns['recurse'](12)
        with patch.object(self.module.shutil,'which',return_value=str(self.exe)):
            self.generic_failure(lambda:self.provider.invoke(self.request(),on_enter=hook))
        row=self.failure(phase='entering_hook',cleanup='not_attempted')
        self.assertEqual(row['primary_error']['sites'],[{'file':'tools/native_claude_text_v5.py','line':2}]*7+[{'file':'tools/native_claude_text_v5.py','line':3}])


        # A narrow serialization fault forces the otherwise bounded closed record
        # past its byte ceiling; it must be omitted, never truncated or written.
        self.setup_provider(); original_bytes=self.module._bytes
        def oversized(value):
            if type(value) is dict and value.get('version')=='NATIVE-CLAUDE-FAILURE/1':
                return original_bytes(value)+b' '*4097
            return original_bytes(value)
        with patch.object(self.module,'_bytes',side_effect=oversized), \
             patch.object(self.module,'_write',wraps=self.module._write) as write, \
             patch.object(self.module.NativeClaudeBuffer,'finish',side_effect=ValueError(CANARY)):
            self.generic_failure(self.invoke)
        self.assertEqual([c for c in write.call_args_list if c.args[0].name=='failure.json'],[])
        self.assertFalse((self.call_dir()/'failure.json').exists())
        self.assertTrue((self.lane/'active.json').exists())

    def test_synthetic_old_unknown_inventory_unchanged_and_never_reentered(self):
        self.setup_provider(); old=self.lane.parent/'old-unknown';old.mkdir(mode=0o700)
        for name in ('active.json','request.json','stdout.bin','result.json'):
            path=old/name;path.write_bytes(('synthetic UNKNOWN '+name).encode());path.chmod(0o600)
        before={p.name:p.read_bytes() for p in old.iterdir()}
        def hook(attempt): self.hook(attempt); raise RuntimeError(CANARY)
        with patch.object(self.module.shutil,'which',return_value=str(self.exe)):
            self.generic_failure(lambda:self.provider.invoke(self.request(),on_enter=hook))
        row=self.failure(phase='entering_hook',cleanup='not_attempted')
        self.assertIsNone(row['observed_exit_code']);self.assertFalse(row['ending_write_completed'])
        lane_before={str(p.relative_to(self.lane)):p.read_bytes() for p in self.lane.rglob('*') if p.is_file()}
        with self.assertRaises(NativeNeverEntered):self.invoke({**self.request(),'call_id':'second'})
        self.assertEqual(lane_before,{str(p.relative_to(self.lane)):p.read_bytes() for p in self.lane.rglob('*') if p.is_file()})
        self.assertEqual(before,{p.name:p.read_bytes() for p in old.iterdir()})
        self.assertFalse(self.starts.exists())

if __name__=='__main__': unittest.main()
