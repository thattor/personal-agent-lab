import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pal.store import Store, _SCHEMA, _SELECTION_SCHEMA, _QUESTION_SCHEMA


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
        self.assertEqual(self.snapshot()[0], Store.SCHEMA_VERSION)
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
        self.assertEqual(self.snapshot()[0], Store.SCHEMA_VERSION)

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
                    self.assertEqual(self.snapshot()[0], Store.SCHEMA_VERSION)
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

    def test_v2_receipts_defaults_bytes_and_fresh_schema_equivalence(self):
        old_path = Path(self.temp.name) / 'v2.db'
        with sqlite3.connect(old_path) as db:
            db.executescript(_SCHEMA + _SELECTION_SCHEMA)
            db.execute('PRAGMA user_version=2')
            db.execute("INSERT INTO goals(id,state,revision,acceptance_id) VALUES ('g','completed',1,'a')")
            db.execute("INSERT INTO acceptances VALUES ('a','g','{}')")
            db.execute("INSERT INTO revisions VALUES ('g',1,'a','Draft','[]','{}')")
            db.execute("INSERT INTO attempts(id,goal_id,revision,acceptance_id,epoch,status,manifest) VALUES ('t','g',1,'a',1,'pass','[]')")
            db.execute("INSERT INTO artifacts VALUES ('b',?,'hash',5)", (b'Draft',))
            db.execute("INSERT INTO receipts VALUES ('r','t','b','hash',5,1,1)")
        def fail(point):
            if point == 'schema.before_commit': raise RuntimeError('stop migration')
        with self.assertRaises(RuntimeError):
            Store(old_path, fault=fail)
        with sqlite3.connect(old_path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 2)
            self.assertNotIn('role', [r[1] for r in db.execute('PRAGMA table_info(receipts)')])
        upgraded = Store(old_path)
        fresh_path = Path(self.temp.name) / 'fresh.db'
        Store(fresh_path)
        self.assertEqual(upgraded.artifact('b'), b'Draft')
        data = upgraded.inspect()
        self.assertEqual(data['receipts'][0]['role'], 'draft')
        self.assertEqual(data['revisions'][0]['template_preview_allowed'], 0)
        def schema(path):
            with sqlite3.connect(path) as db:
                return db.execute("SELECT name,sql FROM sqlite_master ORDER BY name").fetchall()
        self.assertEqual(schema(old_path), schema(fresh_path))

    def test_v3_upgrade_adds_primary_without_changing_existing_rows(self):
        old_path = Path(self.temp.name) / 'v3.db'
        with sqlite3.connect(old_path) as db:
            db.executescript(_SCHEMA + _SELECTION_SCHEMA + _QUESTION_SCHEMA)
            db.execute("ALTER TABLE receipts ADD COLUMN role TEXT NOT NULL DEFAULT 'draft' CHECK(role IN ('draft','preview'))")
            db.execute('ALTER TABLE revisions ADD COLUMN template_preview_allowed INTEGER NOT NULL DEFAULT 0 CHECK(template_preview_allowed IN (0,1))')
            db.execute('PRAGMA user_version=3')
            db.execute("INSERT INTO records(id,role,content) VALUES ('retained','user','original')")
        def fail(point):
            if point == 'schema.before_commit': raise RuntimeError('injected')
        with self.assertRaises(RuntimeError): Store(old_path,fault=fail)
        with sqlite3.connect(old_path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='primary_turns'").fetchone())
        upgraded = Store(old_path)
        self.assertEqual(upgraded.inspect()['records'][0]['content'],'original')
        self.assertEqual(upgraded.inspect()['primary_turns'],[])
        admitted = upgraded.prepare_primary('first','new input')
        upgraded.recover()
        self.assertEqual(upgraded.operation('first')['result']['primary_status'],'interrupted')
        self.assertEqual(upgraded.operation('first')['result']['record_id'],admitted['record_id'])
