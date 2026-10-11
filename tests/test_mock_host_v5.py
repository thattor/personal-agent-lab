"""Frozen HOST01 process/identity tests; trusted fixtures, not TSK recovery proof."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gc
import os
import select
import signal
import sqlite3
import subprocess
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
OPEN_REFUSAL = (RuntimeError, ValueError, OSError)


class MockHostTests(unittest.TestCase):
    def setUp(self):
        from pal.mock_host_v5 import MockHostSession
        self.Host = MockHostSession
        self.temp = tempfile.TemporaryDirectory(prefix='pal-host-fixed-')
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'work.sqlite'
        self.lock = Path(str(self.db) + '.pal-v5.lock')
        self.guards = []
        self.addCleanup(self.close_guards)

    def close_guards(self):
        for guard in reversed(self.guards):
            if guard.phase != 'closed':
                guard.close()

    def open(self, path=None):
        guard = self.Host.open(self.db if path is None else path)
        self.guards.append(guard)
        return guard

    def connection(self, path=None):
        conn = sqlite3.connect(self.db if path is None else path, isolation_level=None)
        self.addCleanup(conn.close)
        return conn

    def ready(self, guard):
        guard.mark_registered(str(uuid.uuid4()), None)
        guard.activate()

    def child_owner(self):
        code = """import sys
from pal.mock_host_v5 import MockHostSession
g = MockHostSession.open(sys.argv[1])
print('owned', flush=True)
sys.stdin.buffer.read(1)
g.close()
"""
        proc = subprocess.Popen([sys.executable, '-E', '-s', '-B', '-c', code, str(self.db)],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def cleanup():
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                stream.close()
        self.addCleanup(cleanup)
        self.assertTrue(select.select([proc.stdout], [], [], 5)[0], 'child startup timeout')
        self.assertEqual(proc.stdout.readline(), b'owned\n')
        return proc

    def test_open_creates_canonical_db_and_permanent_sidecar(self):
        g = self.open()
        self.assertEqual(Path(g.database_path), self.db.resolve())
        self.assertTrue(self.db.is_file())
        self.assertTrue(self.lock.is_file())
        for identifier in (g.session_id, g.runner_id):
            self.assertEqual(str(uuid.UUID(identifier)), identifier)
        self.assertEqual(g.phase, 'owned')
        self.assertIsNone(g.db_uuid)
        self.assertIsNone(g.orphan_lease_id)
        before = self.lock.stat().st_ino
        g.check_connection(self.connection())
        g.close()
        self.assertEqual(g.phase, 'closed')
        self.assertEqual(self.lock.stat().st_ino, before)
        other = self.open()
        self.assertNotEqual((g.session_id, g.runner_id), (other.session_id, other.runner_id))

    def test_phase_registration_retry_activation_and_readonly_properties(self):
        g = self.open()
        conn = self.connection()
        with self.assertRaises(RuntimeError): g.check_connection(conn, ready=True)
        with self.assertRaises(RuntimeError): g.activate()
        identity = str(uuid.uuid4())
        g.mark_registered(identity, 'orphan')
        self.assertEqual((g.phase, g.db_uuid, g.orphan_lease_id), ('startup', identity, 'orphan'))
        g.mark_registered(identity, 'orphan')
        with self.assertRaises(RuntimeError): g.mark_registered(str(uuid.uuid4()), 'orphan')
        with self.assertRaises(RuntimeError): g.mark_registered(identity, None)
        g.check_connection(conn)
        with self.assertRaises(RuntimeError): g.check_connection(conn, ready=True)
        g.activate()
        self.assertEqual(g.phase, 'ready')
        g.check_connection(conn, ready=True)
        for field in ('database_path', 'session_id', 'runner_id', 'phase', 'db_uuid', 'orphan_lease_id'):
            with self.subTest(field=field):
                with self.assertRaises(AttributeError): setattr(g, field, 'forged')

    def test_same_process_duplicate_alias_and_gc_keep_ownership(self):
        code = """import gc,sys
from pathlib import Path
from pal.mock_host_v5 import MockHostSession
p=Path(sys.argv[1]); g=MockHostSession.open(p)
for path in (p,p.parent/'.'/p.name):
    try: MockHostSession.open(path)
    except (RuntimeError,ValueError,OSError): pass
    else: raise AssertionError('duplicate acquired')
del g; gc.collect()
try: MockHostSession.open(p)
except (RuntimeError,ValueError,OSError): pass
else: raise AssertionError('GC released ownership')
print('retained')
"""
        result = subprocess.run([sys.executable, '-E', '-s', '-B', '-c', code, str(self.db)],
            cwd=ROOT, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stdout, b'retained\n')
        self.open()

    def test_real_two_process_contention_and_normal_close_acquire(self):
        proc = self.child_owner()
        with self.assertRaises(OPEN_REFUSAL): self.Host.open(self.db)
        proc.stdin.write(b'x'); proc.stdin.flush()
        self.assertEqual(proc.wait(timeout=5), 0)
        self.open().check_connection(self.connection())

    def test_sigstop_owner_retains_lock_then_process_death_allows_acquire(self):
        proc = self.child_owner()
        os.kill(proc.pid, signal.SIGSTOP)
        pid, status = os.waitpid(proc.pid, os.WUNTRACED)
        self.assertEqual(pid, proc.pid)
        self.assertTrue(os.WIFSTOPPED(status))
        with self.assertRaises(OPEN_REFUSAL): self.Host.open(self.db)
        proc.kill()
        proc.wait(timeout=5)
        self.open().check_connection(self.connection())

    def test_forked_guard_use_refuses_and_inherited_fd_keeps_lock(self):
        g = self.open()
        read_fd, write_fd = os.pipe()
        child = os.fork()
        if child == 0:
            os.close(read_fd)
            try:
                checks = []
                for call in (lambda: g.check_connection(sqlite3.connect(self.db)), g.close):
                    try: call()
                    except RuntimeError: checks.append(True)
                    else: checks.append(False)
                os.write(write_fd, b'ok' if all(checks) else b'bad')
                os.kill(os.getpid(), signal.SIGSTOP)
            finally:
                os._exit(0)
        os.close(write_fd)
        try:
            self.assertTrue(select.select([read_fd], [], [], 5)[0])
            self.assertEqual(os.read(read_fd, 3), b'ok')
            os.waitpid(child, os.WUNTRACED)
            with self.assertRaises(OPEN_REFUSAL): self.Host.open(self.db)
        finally:
            os.close(read_fd)
            os.kill(child, signal.SIGKILL)
            os.waitpid(child, 0)
        g.close()
        self.open()

    def test_dead_parent_inherited_fork_fd_retains_lock(self):
        code = """import os,signal,sys
from pal.mock_host_v5 import MockHostSession
g=MockHostSession.open(sys.argv[1])
pid=os.fork()
if pid==0:
    os.kill(os.getpid(),signal.SIGSTOP)
    os._exit(0)
os.waitpid(pid,os.WUNTRACED)
print(pid,flush=True)
os._exit(0)
"""
        proc = subprocess.Popen([sys.executable, '-E', '-s', '-B', '-c', code, str(self.db)],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        child = None
        try:
            self.assertTrue(select.select([proc.stdout], [], [], 5)[0])
            child = int(proc.stdout.readline())
            self.assertEqual(proc.wait(timeout=5), 0)
            with self.assertRaises(OPEN_REFUSAL): self.Host.open(self.db)
        finally:
            if child is not None: os.kill(child, signal.SIGKILL)
            if proc.poll() is None: proc.kill()
            proc.wait(timeout=5)
            proc.stdout.close(); proc.stderr.close()
        # Orphan death is asynchronous; acquisition after confirmed exit belongs
        # to the direct child-death case, avoiding timing sleeps/retry here.

    def test_nested_operations_and_activity_prevent_close_without_deadlock(self):
        g = self.open()
        with g.operation():
            with g.operation():
                with self.assertRaises(RuntimeError): g.close()
        with self.assertRaises(RuntimeError):
            with g.activity(): pass
        self.ready(g)
        with g.activity():
            with g.operation(ready=True):
                with g.operation():
                    with self.assertRaises(RuntimeError): g.close()
        g.close()

    def test_baseexception_permits_cleanup_and_context_exit_close(self):
        class Abort(BaseException): pass
        g = self.open()
        self.ready(g)
        with self.assertRaises(Abort):
            with g.activity():
                with g.operation(): raise Abort()
        with g:
            g.check_connection(self.connection(), ready=True)
        self.assertEqual(g.phase, 'closed')

    def test_closed_fake_wrong_and_blank_connections_fail(self):
        g = self.open()
        with self.assertRaises(RuntimeError): g.check_connection(self.connection(':memory:'))
        with self.assertRaises(RuntimeError): g.check_connection(self.connection(self.db.parent / 'other.sqlite'))
        fake = object.__new__(self.Host)
        with self.assertRaises(RuntimeError): fake.check_connection(self.connection())
        g.close()
        for action in (lambda: g.check_connection(self.connection()),
                       lambda: g.mark_registered(str(uuid.uuid4()), None), g.activate):
            with self.assertRaises(RuntimeError): action()
        with self.assertRaises(RuntimeError):
            with g.operation(): pass
        with self.assertRaises(RuntimeError):
            with g.activity(): pass

    def test_memory_blank_uri_inputs_are_refused(self):
        for path in ('', ':memory:', 'file:work?mode=memory&cache=shared'):
            with self.subTest(path=path):
                with self.assertRaises(OPEN_REFUSAL): self.Host.open(path)

    def test_sidecar_symlink_hardlink_and_db_hardlink_are_refused(self):
        target = self.db.parent / 'target'
        target.write_bytes(b'')
        self.lock.symlink_to(target)
        with self.assertRaises(OPEN_REFUSAL): self.Host.open(self.db)
        self.lock.unlink()
        os.link(target, self.lock)
        with self.assertRaises(OPEN_REFUSAL): self.Host.open(self.db)
        self.lock.unlink()
        self.db.write_bytes(b'')
        os.link(self.db, self.db.parent / 'alias.sqlite')
        with self.assertRaises(OPEN_REFUSAL): self.Host.open(self.db)

    def test_db_and_sidecar_replacement_invalidate_guard(self):
        g = self.open()
        conn = self.connection()
        for path in (self.db, self.lock):
            backup = Path(str(path) + '.original')
            path.rename(backup)
            path.write_bytes(b'')
            try:
                with self.assertRaises(RuntimeError): g.check_connection(conn)
                with self.assertRaises(RuntimeError):
                    with g.operation(): pass
            finally:
                path.unlink()
                backup.rename(path)
            g.check_connection(conn)
