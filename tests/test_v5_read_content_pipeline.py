"""Synthetic preparation pipeline; no provider, saved artifact or Goal proof."""

import base64
import hashlib
import json
import unittest
from unittest.mock import Mock

from pal.artifact_content_v5 import prepare_content
from pal.artifact_integrity_v5 import check_bytes
from pal.bounded_payload_v5 import PayloadBuffer, PayloadLimitError
from pal.github_file_payload_v5 import FilePayloadError, decode_file
from pal.github_read_request_v5 import ReadRequestError, prepare_read


def file_response(body, *, size=None):
    encoded = base64.b64encode(body).decode("ascii")
    wrapped = "\r\n".join(encoded[n:n + 8] for n in range(0, len(encoded), 8))
    return json.dumps({
        "type": "file", "encoding": "base64", "content": wrapped,
        "size": len(body) if size is None else size, "sha": "b" * 40,
    }).encode("utf-8")


def preview(arguments, transport, *, max_bytes=1048576):
    request = prepare_read("github.file.read", arguments, max_bytes=max_bytes)
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


if __name__ == "__main__":
    unittest.main()
