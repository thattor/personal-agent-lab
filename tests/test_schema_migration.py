import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pal.store import Store, _SCHEMA


class SchemaMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.db'
        # Authored historical-schema fixture, never a production database.
        with sqlite3.connect(self.path) as db:
            db.executescript(_SCHEMA)
            db.execute('PRAGMA user_version=1')
            db.execute("INSERT INTO records(id,role,content) VALUES('source','user','Cedar')")

    def snapshot(self):
        with sqlite3.connect(self.path) as db:
            return (db.execute('PRAGMA user_version').fetchone()[0],
                    db.execute('SELECT * FROM records').fetchall(),
                    db.execute("SELECT name,sql FROM sqlite_master ORDER BY name").fetchall())

    def test_additive_upgrade_preserves_rows_and_reopens(self):
        before = self.snapshot()[1]
        Store(self.path)
        self.assertEqual(self.snapshot()[0], 2)
        self.assertEqual(self.snapshot()[1], before)
        with sqlite3.connect(self.path) as db:
            columns = [r[1] for r in db.execute('PRAGMA table_info(control_selections)')]
            self.assertEqual(columns, ['selection_id', 'source_record_id', 'source_key',
                                       'action', 'proposal', 'consumed_by'])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        after = self.snapshot()
        Store(self.path)
        self.assertEqual(self.snapshot(), after)

    def test_fault_rolls_back_schema_and_version_together(self):
        before = self.snapshot()
        def fault(point):
            if point == 'schema.before_commit':
                raise RuntimeError('injected migration failure')
        with self.assertRaisesRegex(RuntimeError, 'injected'):
            Store(self.path, fault=fault)
        self.assertEqual(self.snapshot(), before)
        Store(self.path)
        self.assertEqual(self.snapshot()[0], 2)

    def test_process_kill_before_and_after_commit_is_recoverable(self):
        before = self.snapshot()
        child = '''import os, signal, sys
from pal.store import Store
def fault(point):
    if point == sys.argv[2]:
        os.kill(os.getpid(), signal.SIGKILL)
Store(sys.argv[1], fault=fault)
'''
        for point in ('schema.before_commit', 'schema.after_commit'):
            with self.subTest(point=point):
                result = subprocess.run([sys.executable, '-c', child, str(self.path), point],
                                        capture_output=True, timeout=15)
                self.assertEqual(result.returncode, -9, result.stderr)
                if point.endswith('before_commit'):
                    self.assertEqual(self.snapshot(), before)
                else:
                    self.assertEqual(self.snapshot()[0], 2)
                # Reopening safely finishes or observes the committed upgrade.
                if point.endswith('after_commit'):
                    Store(self.path)
                    self.assertEqual(self.snapshot()[1], before[1])

    def test_future_schema_refuses_without_mutation(self):
        with sqlite3.connect(self.path) as db:
            db.execute('PRAGMA user_version=900')
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'unsupported canonical schema'):
            Store(self.path)
        self.assertEqual(self.snapshot(), before)
