"""C15 EXE01 prerequisite: grant- and host-bounded operation reservations.

The tests use a temporary real TaskStore/SQLite store, not a fake authority
provider. They prove only the budget seam; no gh invocation or EXE01 ledger.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pal.contracts_v5 import Grant, Limits
from pal.tasks_v5 import TaskStore

REPO = "thattor/personal-agent-lab"
CAPABILITY = "github.issue.read"


def intake(key):
    return {
        "key": key, "session_id": "session",
        "origin_record_ref": {"kind": "record", "id": "origin"},
        "brief": {
            "purpose": "read issue",
            "target": {"repository": REPO, "issue_numbers": [22], "files": []},
            "constraints": ["read only"],
            "conditions": [{"description": "issue fetched", "check": "source_fetched"}],
            "context_refs": [],
        },
    }


class OperationBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.conn = sqlite3.connect(
            Path(self.tmp.name) / "operations.db", isolation_level=None, timeout=0
        )
        self.addCleanup(self.conn.close)
        self.host = Limits(3, 15, 15)
        self.grant = Grant((CAPABILITY,), (REPO,), Limits(2, 12, 12))
        self.t = self.store()
        self.serial = 0

    def store(self, connection=None):
        return TaskStore(
            connection or self.conn,
            host_limits=self.host,
            host_grant=self.grant,
            expert_id="expert",
            source_gate=lambda connection, refs: "available",
        )

    def ok(self, result):
        self.assertTrue(result.ok, result.to_json())
        return result.to_json()["value"]

    def fail(self, result, code):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, code)
        return result

    def snapshot(self):
        return {
            table: self.conn.execute("SELECT * FROM " + table + " ORDER BY rowid").fetchall()
            for (table,) in self.conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name LIKE 'v5_%' ORDER BY name"
            ).fetchall()
        }

    def work(self, name):
        request = intake(name)
        return self.ok(self.t.create(request, request_scope=self.grant))["work_ref"]

    def claim(self):
        return self.ok(self.t.claim({"runner_id": "runner"}))

    def reserve(self, work, key, **other):
        return self.t.reserve_budget(
            {"key": key, "work_ref": work, "kind": "operation", **other}
        )

    def test_strict_grant_and_host_counter_and_replay(self):
        work = self.work("first")
        claimed = self.claim()
        work = claimed["work_ref"]
        req = {"key": "o1", "work_ref": work, "kind": "operation"}
        a = self.ok(self.t.reserve_budget(req))
        self.assertEqual(a["remaining"], {"work": 1, "host": 2})
        self.assertEqual(
            self.conn.execute(
                "SELECT kind,role,binding FROM v5_tsk_reservation WHERE id=?",
                (a["reservation_id"],),
            ).fetchone(),
            ("operation", None, None),
        )
        state = self.snapshot()
        self.assertEqual(self.ok(self.t.reserve_budget(req)), a)
        self.assertEqual(state, self.snapshot())
        self.fail(
            self.t.reserve_budget({**req, "role": "expert"}), "invalid_input"
        )
        self.assertEqual(state, self.snapshot())
        b = self.ok(self.reserve(work, "o2"))
        self.assertEqual(b["remaining"], {"work": 0, "host": 1})
        state = self.snapshot()
        self.fail(self.reserve(work, "o3"), "limit")
        self.assertEqual(state, self.snapshot())

    def test_consume_binding_cannot_be_reused_for_second_operation(self):
        work = self.claim_after_create()
        r = self.ok(self.reserve(work, "op"))
        command = {
            "reservation_id": r["reservation_id"],
            "call_or_operation_id": "operation-one",
        }
        saved = self.ok(self.t.consume(command))
        state = self.snapshot()
        self.assertEqual(saved, command)
        self.assertEqual(self.ok(self.t.consume(command)), saved)
        self.fail(
            self.t.consume({**command, "call_or_operation_id": "operation-two"}),
            "conflict",
        )
        self.assertEqual(state, self.snapshot())

    def claim_after_create(self):
        self.work("active")
        return self.claim()["work_ref"]

    def test_operation_reservations_do_not_debit_step_or_model(self):
        work = self.claim_after_create()
        before = self.conn.execute(
            "SELECT kind,used FROM v5_tsk_host ORDER BY kind"
        ).fetchall()
        self.ok(self.reserve(work, "op"))
        after = self.conn.execute(
            "SELECT kind,used FROM v5_tsk_host ORDER BY kind"
        ).fetchall()
        self.assertEqual(after, [("model", 0), ("operation", 1), ("step", 0)])
        self.assertEqual(before, [("model", 0), ("operation", 0), ("step", 0)])
        context = self.ok(
            self.t.get_execution_context({"lease_id": self.claim()["lease_id"], "work_ref": work})
        )
        self.assertEqual(
            set(context["remaining_budget"]), {"model", "step"}
        )

    def test_reopen_retains_operation_debit(self):
        work = self.claim_after_create()
        first = self.ok(self.reserve(work, "one"))
        second_conn = sqlite3.connect(
            Path(self.tmp.name) / "operations.db", isolation_level=None, timeout=0
        )
        self.addCleanup(second_conn.close)
        reopened = self.store(second_conn)
        prior = self.snapshot()
        self.assertEqual(
            self.ok(reopened.reserve_budget(
                {"key": "one", "work_ref": work, "kind": "operation"}
            )), first
        )
        self.assertEqual(prior, self.snapshot())
        more = self.ok(reopened.reserve_budget(
            {"key": "two", "work_ref": work, "kind": "operation"}
        ))
        self.assertEqual(more["remaining"]["work"], 0)

    def test_pause_and_stale_epoch_reject_no_debit(self):
        work = self.claim_after_create()
        self.ok(self.t.control({"key": "pause", "work_ref": work, "command": "pause"}))
        before = self.snapshot()
        self.fail(self.reserve(work, "paused"), "conflict")
        self.assertEqual(before, self.snapshot())
        self.ok(self.t.release({
            "lease_id": self.claim()["lease_id"], "work_ref": work,
            "outcome": "yield", "reason": "done",
        }))
        self.ok(self.t.control({"key": "resume", "work_ref": work, "command": "resume"}))
        next_work = self.claim()["work_ref"]
        self.assertNotEqual(next_work["epoch"], work["epoch"])
        before = self.snapshot()
        self.fail(self.reserve(work, "old-epoch"), "stale")
        self.assertEqual(before, self.snapshot())

    def test_host_operation_ceiling_does_not_block_nonread_claim(self):
        self.host = Limits(0, 15, 15)
        zero_path = Path(self.tmp.name) / "zero.db"
        zero = sqlite3.connect(zero_path, isolation_level=None, timeout=0)
        self.addCleanup(zero.close)
        no_operations = self.store(zero)
        self.ok(no_operations.create(intake("zero"), request_scope=self.grant))
        claimed = self.ok(no_operations.claim({"runner_id": "runner"}))
        self.assertEqual(claimed["work_ref"]["epoch"], 1)
        result = no_operations.reserve_budget(
            {"key": "no-budget", "work_ref": claimed["work_ref"], "kind": "operation"}
        )
        self.fail(result, "limit")

    def test_corrupt_host_and_work_usage_fail_closed(self):
        work = self.claim_after_create()
        self.ok(self.reserve(work, "initial"))
        original = self.conn.execute(
            "SELECT ceiling,used FROM v5_tsk_host WHERE kind='operation'"
        ).fetchone()
        for ceiling, used in ((0, 1), (-1, 0), (3, -1), ("corrupt", 0)):
            self.conn.execute(
                "UPDATE v5_tsk_host SET ceiling=?,used=? WHERE kind='operation'",
                (ceiling, used),
            )
            before = self.snapshot()
            self.fail(self.reserve(work, "corrupt"), "unavailable")
            self.assertEqual(before, self.snapshot())
        self.conn.execute(
            "UPDATE v5_tsk_host SET ceiling=?,used=? WHERE kind='operation'",
            original,
        )
        self.conn.execute(
            "UPDATE v5_tsk_usage SET used=99 WHERE kind='operation'"
        )
        before = self.snapshot()
        self.fail(self.reserve(work, "corrupt"), "unavailable")
        self.assertEqual(before, self.snapshot())

    def test_bad_role_and_no_work_are_bounded(self):
        work = self.claim_after_create()
        before = self.snapshot()
        for bad in (
            {"key": "bad", "work_ref": work, "kind": "operation", "role": "expert"},
            {"key": "bad", "work_ref": work, "kind": "operation", "role": "primary"},
            {"key": "bad", "work_ref": work, "kind": "operation", "role": None},
            {"key": "bad", "kind": "operation", "role": "primary"},
            {"key": "bad", "kind": "operation"},
            {"key": "bad", "work_ref": work, "kind": "operation", "extra": 1},
        ):
            with self.subTest(bad=bad):
                self.fail(self.t.reserve_budget(bad), "invalid_input")
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
