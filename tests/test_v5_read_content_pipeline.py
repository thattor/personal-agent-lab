"""Synthetic preparation pipeline; no provider, saved artifact or Goal proof."""

import base64
import hashlib
import json
import unittest
from unittest.mock import Mock

from pal.artifact_content_v5 import prepare_content
from pal.artifact_integrity_v5 import check_bytes
from pal.bounded_payload_v5 import PayloadBuffer, PayloadLimitError
from pal.contracts_v5 import ContractError, Ref, Result, WorkRef, dumps, loads, parse_model_action
from pal.github_file_payload_v5 import FilePayloadError, decode_file
from pal.github_read_request_v5 import ReadRequestError, prepare_read


def file_response(body, *, size=None):
    encoded = base64.b64encode(body).decode("ascii")
    wrapped = "\r\n".join(encoded[n:n + 8] for n in range(0, len(encoded), 8))
    return json.dumps({
        "type": "file", "encoding": "base64", "content": wrapped,
        "size": len(body) if size is None else size, "sha": "b" * 40,
    }).encode("utf-8")


def preview(arguments, transport, *, capability="github.file.read", max_bytes=1048576):
    request = prepare_read(capability, arguments, max_bytes=max_bytes)
    buffer = PayloadBuffer(max_bytes=request.max_bytes)
    for chunk in transport(request):
        buffer.append(chunk)
    decoded = decode_file(buffer.getvalue(), max_bytes=request.max_bytes)
    return request, decoded, prepare_content(decoded.content, "text/markdown")


class ReadContentPipelineTests(unittest.TestCase):
    def setUp(self):
        self.arguments = {
            "repository": "thattor/personal-agent-lab",
            "path": "資料/進捗.md", "ref": "a" * 40,
        }

    def test_chunked_response_preserves_text_and_checks_expected_bytes(self):
        body = "## 状況\r\n確認中 e\u0301\r\n".encode("utf-8")
        raw = file_response(body)
        transport = Mock(return_value=[raw[n:n + 3] for n in range(0, len(raw), 3)])
        request, decoded, content = preview(self.arguments, transport)
        transport.assert_called_once_with(request)
        self.assertTrue(request.argv[-1].endswith("?ref=" + self.arguments["ref"]))
        self.assertEqual(decoded.blob_sha, "b" * 40)
        self.assertEqual(decoded.data, body)
        self.assertEqual(content.data, body)
        self.assertEqual(content.byte_count, len(body))
        expected_hash = hashlib.sha256(body).hexdigest()
        self.assertEqual(content.sha256, expected_hash)
        outcome = check_bytes(content.data, expected_hash, len(body))
        self.assertEqual((outcome.status, outcome.reason), ("met", "integrity_match"))

    def test_empty_file_is_valid_content(self):
        _, decoded, content = preview(self.arguments, lambda request: [file_response(b"")])
        self.assertEqual(decoded.content, "")
        outcome = check_bytes(content.data, hashlib.sha256(b"").hexdigest(), 0)
        self.assertEqual((outcome.status, outcome.reason), ("met", "integrity_match"))

    def test_same_length_tampering_does_not_match_expected_body(self):
        expected = b"original"
        _, _, content = preview(self.arguments, lambda request: [file_response(b"tampered")])
        outcome = check_bytes(content.data, hashlib.sha256(expected).hexdigest(), len(expected))
        self.assertEqual((outcome.status, outcome.reason), ("unmet", "sha256_mismatch"))

    def test_wrong_provider_size_stops_before_content_preparation(self):
        with self.assertRaises(FilePayloadError) as cm:
            preview(self.arguments, lambda request: [file_response(b"text", size=3)])
        self.assertEqual(cm.exception.code, "invalid_input")

    def test_cumulative_transport_overflow_cannot_enter_decode(self):
        raw = file_response(b"text")
        with self.assertRaises(PayloadLimitError) as cm:
            preview(self.arguments, lambda request: [raw[:-1], raw[-1:]], max_bytes=len(raw) - 1)
        self.assertEqual(cm.exception.code, "limit")

    def test_denied_repository_never_reaches_transport(self):
        transport = Mock(side_effect=AssertionError("transport must not run"))
        arguments = dict(self.arguments, repository="someone/other")
        with self.assertRaises(ReadRequestError) as cm:
            preview(arguments, transport)
        self.assertEqual(cm.exception.code, "denied")
        transport.assert_not_called()


class ActionReadContentPipelineTests(unittest.TestCase):
    """Wire-to-helper composition only; no grant, ledger or saved Ref is implied."""

    def setUp(self):
        self.source = Ref("record", "synthetic-request")
        self.action = {
            "kind": "operate", "capability": "github.file.read",
            "arguments": {
                "repository": "thattor/personal-agent-lab",
                "path": "資料/進捗.md", "ref": "a" * 40,
            },
            "source_refs": [self.source.to_json()],
        }

    def run_preview(self, raw, transport):
        action = parse_model_action(raw, allowed_refs=[self.source])
        return preview(action.arguments.to_json(), transport, capability=action.capability)

    def test_model_action_bytes_and_result_round_trip_across_helpers(self):
        body = "## 進捗\r\n共通契約を接続 e\u0301\r\n".encode("utf-8")
        transport = Mock(return_value=[file_response(body)])
        request, decoded, content = self.run_preview(dumps(self.action), transport)
        transport.assert_called_once_with(request)
        self.assertEqual(decoded.data, body)
        self.assertEqual(content.data, body)
        self.assertEqual(check_bytes(content.data, content.sha256, len(body)).status, "met")
        work = WorkRef("synthetic-goal", 2, 3)
        result = Result.success({
            "work_ref": work.to_json(), "content": content.data.decode("utf-8"),
            "sha256": content.sha256, "byte_count": content.byte_count,
        })
        restored = Result.from_json(loads(dumps(result)))
        self.assertEqual(restored, result)
        self.assertEqual(WorkRef.from_json(restored.value.to_json()["work_ref"]), work)

    def test_unprovided_source_stops_before_preparation_and_transport(self):
        self.action["source_refs"] = [{"kind": "source", "id": self.source.id}]
        transport = Mock(side_effect=AssertionError("transport must not run"))
        with self.assertRaises(ContractError) as cm:
            self.run_preview(dumps(self.action), transport)
        self.assertEqual(cm.exception.code, "invalid_input")
        transport.assert_not_called()

    def test_duplicate_arguments_stop_before_preparation_and_transport(self):
        raw = dumps(self.action).replace('"path":', '"path":"other","path":', 1)
        transport = Mock(side_effect=AssertionError("transport must not run"))
        with self.assertRaises(ContractError):
            self.run_preview(raw, transport)
        transport.assert_not_called()

    def test_structurally_valid_wrong_repository_is_denied_by_read_helper(self):
        self.action["arguments"]["repository"] = "someone/other"
        transport = Mock(side_effect=AssertionError("transport must not run"))
        with self.assertRaises(ReadRequestError) as cm:
            self.run_preview(dumps(self.action), transport)
        result = Result.failure(cm.exception.code, "Read preparation rejected", [self.source])
        self.assertEqual(Result.from_json(loads(dumps(result))), result)
        self.assertEqual(result.error.code, "denied")
        transport.assert_not_called()

    def test_unsupported_capability_is_rejected_by_read_helper(self):
        self.action["capability"] = "github.file.write"
        transport = Mock(side_effect=AssertionError("transport must not run"))
        with self.assertRaises(ReadRequestError) as cm:
            self.run_preview(dumps(self.action), transport)
        self.assertEqual(cm.exception.code, "invalid_input")
        transport.assert_not_called()


if __name__ == "__main__":
    unittest.main()
