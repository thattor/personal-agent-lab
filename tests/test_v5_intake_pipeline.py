"""Synthetic wire -> isolated intake -> pure preview; no execution authority."""

import base64
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pal.artifact_content_v5 import prepare_content
from pal.artifact_integrity_v5 import check_bytes
from pal.contracts_v5 import (
    Brief, Grant, Ref, Result, dumps, loads, parse_model_draft_brief,
)
from pal.github_file_payload_v5 import decode_file
from pal.github_read_request_v5 import prepare_read
from pal.intake_v5 import IntakeStore


class IntakePipelineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "synthetic.sqlite"
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.addCleanup(lambda: self.conn.close())
        self.source = Ref("record", "synthetic-request")
        self.conn.execute("CREATE TABLE synthetic_sources (id TEXT PRIMARY KEY, enabled INTEGER)")
        self.conn.execute("INSERT INTO synthetic_sources VALUES (?, 1)", (self.source.id,))
        self.gate_calls = 0
        self.grant = Grant.from_json({
            "capabilities": ["github.file.read"],
            "repositories": ["thattor/personal-agent-lab"],
            "limits": {"max_operations": 1, "max_steps": 2, "max_model_calls": 0},
        })
        self.proposal = {
            "purpose": "資料を確認してローカルに下書きする",
            "target": {
                "repository": "thattor/personal-agent-lab", "issue_numbers": [],
                "files": [{"path": "資料/進捗.md", "ref": "a" * 40}],
            },
            "constraints": ["送信しない", " e\u0301\r\n"],
            "conditions": [{"description": "原文を保持", "check": "source_fetched"}],
            "context_refs": [self.source.to_json()],
        }
        draft = parse_model_draft_brief(dumps(self.proposal), allowed_refs=[self.source])
        self.request = {
            "key": "C03.create:synthetic-request", "session_id": "synthetic-session",
            "origin_record_ref": self.source.to_json(), "brief": draft.to_json(),
        }

    def source_gate(self, conn, refs):
        self.gate_calls += 1
        self.assertIs(conn, self.conn)
        self.assertTrue(conn.in_transaction)
        for ref in refs:
            row = conn.execute("SELECT enabled FROM synthetic_sources WHERE id = ?", (ref.id,)).fetchone()
            if row is None:
                return "not_found"
            if not row[0]:
                return "denied"
        return "available"

    def store(self):
        return IntakeStore(self.conn, host_grant=self.grant,
                           expert_id="synthetic-expert", source_gate=self.source_gate)

    def test_model_brief_durable_read_and_mock_bytes_remain_queued(self):
        created = self.store().create(self.request, request_scope=self.grant)
        self.assertTrue(created.ok, created.to_json())
        identity = created.to_json()["value"]["work_ref"]
        self.conn.close()
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        store = self.store()
        restored = store.get_work({"goal_id": identity["goal_id"], "revision": 1})
        self.assertEqual(Result.from_json(loads(dumps(restored))), restored)
        view = restored.to_json()["value"]
        brief = Brief.from_json(view["brief"])
        self.assertEqual(brief.constraints, tuple(self.proposal["constraints"]))
        self.assertTrue(brief.conditions[0].id)
        self.assertEqual(view["grant"]["limits"]["max_model_calls"], 0)
        file = brief.target.files[0]
        request = prepare_read("github.file.read", {
            "repository": brief.target.repository, "path": file.path, "ref": file.ref,
        })
        self.assertEqual(request.capability, "github.file.read")
        body = "## 確認中\r\n e\u0301\r\n".encode("utf-8")
        response = json.dumps({
            "type": "file", "encoding": "base64", "size": len(body), "sha": "b" * 40,
            "content": base64.b64encode(body).decode("ascii"),
        }).encode("utf-8")
        decoded = decode_file(response)
        content = prepare_content(decoded.content, "text/markdown")
        self.assertEqual(content.data, body)
        self.assertEqual(check_bytes(body, content.sha256, len(body)).status, "met")
        after = store.get_work({"goal_id": identity["goal_id"]}).to_json()["value"]
        self.assertEqual(after, view)
        self.assertEqual(after["state"], "queued")
        self.assertEqual(after["current_artifact_refs"], [])

    def test_reference_stop_rejects_new_intake_but_replays_old_receipt(self):
        store = self.store()
        accepted = store.create(self.request, request_scope=self.grant)
        self.assertTrue(accepted.ok)
        self.conn.execute("UPDATE synthetic_sources SET enabled = 0")
        calls = self.gate_calls
        replay = store.create(self.request, request_scope=self.grant)
        self.assertEqual(replay, accepted)
        self.assertEqual(self.gate_calls, calls)
        rejected = store.create(dict(self.request, key="C03.create:later"), request_scope=self.grant)
        self.assertEqual(rejected.error.code, "denied")
        self.assertEqual(self.gate_calls, calls + 1)
        self.assertEqual(store.get_work({
            "goal_id": accepted.to_json()["value"]["work_ref"]["goal_id"],
        }).to_json()["value"]["state"], "queued")

    def test_changed_raw_scope_conflicts_even_when_effective_grant_matches(self):
        store = self.store()
        accepted = store.create(self.request, request_scope=self.grant)
        self.assertTrue(accepted.ok)
        changed = self.grant.to_json()
        changed["capabilities"].append("ungranted.synthetic.capability")
        rejected = store.create(self.request, request_scope=Grant.from_json(changed))
        self.assertEqual(rejected.error.code, "conflict")
        self.assertEqual(store.create(self.request, request_scope=self.grant), accepted)

    def test_replay_returns_original_receipt_under_changed_host_configuration(self):
        accepted = self.store().create(self.request, request_scope=self.grant)
        self.assertTrue(accepted.ok)
        self.conn.close()
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.execute("UPDATE synthetic_sources SET enabled = 0")
        changed_host = self.grant.to_json()
        changed_host["capabilities"] = []
        changed_host["repositories"] = []

        def must_not_run(*args):
            raise AssertionError("an equal replay cannot allocate IDs or invoke the gate")

        store = IntakeStore(
            self.conn, host_grant=Grant.from_json(changed_host), expert_id="later-expert",
            source_gate=must_not_run, id_factory=must_not_run,
        )
        self.assertEqual(store.create(self.request, request_scope=self.grant), accepted)


if __name__ == "__main__":
    unittest.main()
