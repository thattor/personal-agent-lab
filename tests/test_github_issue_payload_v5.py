"""Tests for pal.github_issue_payload_v5 (PAL v5 EXE-02 leaf decoder).

All fixtures are synthetic, built with json.dumps or hand-written bytes;
nothing is copied from real repository responses.
"""

import dataclasses
import json
import unittest

from pal.github_issue_payload_v5 import (
    DecodedIssue,
    IssuePayloadError,
    canonical_issue,
    decode_issue,
)

MARKER = "SECRET-MARKER-9Z"
UPDATED = "2026-10-10T01:02:03Z"


def issue_payload(**over):
    obj = {
        "number": 42,
        "title": "hello",
        "state": "open",
        "body": "text",
        "updated_at": UPDATED,
        "id": 7,
        "url": "https://api.example.invalid/x?token=" + MARKER,
        "html_url": "https://example.invalid/" + MARKER,
        "user": {"login": "u", "token": MARKER},
        "labels": [{"name": "bug"}],
    }
    obj.update(over)
    return json.dumps(obj).encode("utf-8")


def raw_object(obj):
    return json.dumps(obj).encode("utf-8")


class DecodeIssueTests(unittest.TestCase):
    maxDiff = None

    def assert_error(self, raw, code=None, **kwargs):
        with self.assertRaises(IssuePayloadError) as cm:
            decode_issue(raw, **kwargs)
        err = cm.exception
        self.assertIs(type(err), IssuePayloadError)
        if code is not None:
            self.assertEqual(err.code, code)
        self.assertIn(err.code, ("invalid_input", "limit"))
        self.assertEqual(str(err), err.message)
        self.assertEqual(err.args, (err.message,))
        self.assertTrue(err.message.isascii())
        self.assertLessEqual(len(err.message), 80)
        self.assertIsNone(err.__cause__)
        self.assertIsNone(err.__context__)
        for rendered in (str(err), repr(err), str(err.args)):
            self.assertNotIn(MARKER, rendered)
        return err

    # --- Valid inputs ----------------------------------------------------

    def test_valid_issue_full_fields(self):
        result = decode_issue(issue_payload())
        self.assertIs(type(result), DecodedIssue)
        self.assertEqual(result.number, 42)
        self.assertEqual(result.title, "hello")
        self.assertEqual(result.state, "open")
        self.assertEqual(result.body, "text")
        self.assertEqual(result.updated_at, UPDATED)

    def test_valid_issue_null_body(self):
        result = decode_issue(issue_payload(body=None))
        self.assertIsNone(result.body)

    def test_valid_issue_unicode_and_empty_title(self):
        result = decode_issue(issue_payload(title="", body="本文 \U0001f600"))
        self.assertEqual(result.title, "")
        self.assertEqual(result.body, "本文 \U0001f600")

    def test_valid_issue_closed_state(self):
        result = decode_issue(issue_payload(state="closed"))
        self.assertEqual(result.state, "closed")

    def test_extra_members_ignored_not_retained(self):
        result = decode_issue(issue_payload())
        canonical = canonical_issue(result)
        self.assertNotIn(MARKER.encode(), canonical)
        for key in (b"url", b"html_url", b"user", b"labels", b"id"):
            self.assertNotIn(key, canonical)

    def test_canonical_sorted_keys_and_null(self):
        result = decode_issue(issue_payload(body=None, title="t"))
        canonical = canonical_issue(result)
        parsed = json.loads(canonical)
        self.assertEqual(
            parsed,
            {
                "number": 42,
                "title": "t",
                "state": "open",
                "body": None,
                "updated_at": UPDATED,
            },
        )
        self.assertIsNone(parsed["body"])
        expected = json.dumps(
            parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(canonical, expected)
        self.assertLess(len(canonical), 4096)

    def test_canonical_no_pull_request_leak(self):
        result = decode_issue(issue_payload())
        self.assertNotIn(b"pull_request", canonical_issue(result))

    def test_immutability(self):
        result = decode_issue(issue_payload())
        for field in ("number", "title", "state", "body", "updated_at"):
            with self.assertRaises(dataclasses.FrozenInstanceError):
                setattr(result, field, None)

    # --- pull_request rejection ------------------------------------------

    def test_pull_request_member_rejected(self):
        for value in ({"url": "x"}, None, True, {}, "anything"):
            self.assert_error(
                issue_payload(pull_request=value), "invalid_input"
            )

    # --- Structural rejections -------------------------------------------

    def test_duplicate_keys_rejected(self):
        raw = (
            b'{"number":42,"number":43,"title":"t","state":"open",'
            b'"body":null,"updated_at":"' + UPDATED.encode() + b'"}'
        )
        err = self.assert_error(raw, "invalid_input")
        self.assertIn("duplicate", err.message)

    def test_nested_duplicate_keys_rejected(self):
        raw = (
            b'{"number":42,"title":"t","state":"open","body":null,'
            b'"updated_at":"' + UPDATED.encode()
            + b'","user":{"a":1,"a":2}}'
        )
        self.assert_error(raw, "invalid_input")

    def test_nonfinite_rejected(self):
        for bad in (b"NaN", b"Infinity", b"-Infinity"):
            raw = b'{"number":' + bad + b',"title":"t","state":"open","body":null,"updated_at":"' + UPDATED.encode() + b'"}'
            err = self.assert_error(raw, "invalid_input")
            self.assertIn("non-finite", err.message)
        raw = raw_object(
            {
                "number": 1e999,
                "title": "t",
                "state": "open",
                "body": None,
                "updated_at": UPDATED,
            }
        )
        self.assert_error(raw, "invalid_input")

    def test_invalid_json_rejected(self):
        for raw in (
            b"",
            b"not json",
            b"{",
            b'{"number":42,}',
            b"\xef\xbb\xbf" + issue_payload(),
            b"\xff\xfe\x00",
        ):
            self.assert_error(raw, "invalid_input")

    def test_non_object_rejected(self):
        for raw in (b"[]", b"[1,2]", b'"str"', b"42", b"null", b"true"):
            self.assert_error(raw, "invalid_input")

    def test_max_bytes_validation(self):
        for bad in (0, -1, True, False, 1.5, "10", None):
            self.assert_error(issue_payload(), "invalid_input", max_bytes=bad)
        self.assert_error(
            issue_payload(), "limit", max_bytes=1048577
        )
        self.assert_error(
            issue_payload(), "limit", max_bytes=len(issue_payload()) - 1
        )

    def test_payload_type_and_limit(self):
        for bad in ("{}", None, 42, ["x"], {"a": 1}):
            self.assert_error(bad, "invalid_input")
        self.assert_error(issue_payload(), "limit", max_bytes=10)
        self.assert_error(b"x" * 1048577, "limit")

    # --- Field validation -------------------------------------------------

    def test_number_validation(self):
        for bad in (True, False, 0, -1, "42", 42.0, None, 2**63, 10**30):
            self.assert_error(issue_payload(number=bad), "invalid_input")
        result = decode_issue(issue_payload(number=2**63 - 1))
        self.assertEqual(result.number, 2**63 - 1)

    def test_title_validation(self):
        for bad in (None, 42, True, ["x"], {"a": 1}):
            self.assert_error(issue_payload(title=bad), "invalid_input")
        self.assert_error(issue_payload(title="x" * 5000), "invalid_input")
        self.assert_error(issue_payload(title="\ud800"), "invalid_input")
        result = decode_issue(issue_payload(title="x" * 1024))
        self.assertEqual(len(result.title), 1024)

    def test_state_validation(self):
        for bad in (None, 1, True, "OPEN", "merged", "draft", "", ["open"]):
            self.assert_error(issue_payload(state=bad), "invalid_input")

    def test_body_validation(self):
        obj = {
            "number": 42,
            "title": "t",
            "state": "open",
            "updated_at": UPDATED,
        }
        self.assert_error(raw_object(obj), "invalid_input")
        for bad in (42, True, ["x"], {"a": 1}):
            self.assert_error(issue_payload(body=bad), "invalid_input")
        self.assert_error(
            issue_payload(body="x" * 300000), "invalid_input"
        )

    def test_updated_at_validation(self):
        for bad in (
            None,
            42,
            True,
            "",
            "2026-10-10",
            "2026-10-10 01:02:03",
            "2026-13-10T01:02:03Z",
            "2026-10-32T01:02:03Z",
            "2026-10-10T25:02:03Z",
            "2026-10-10T01:60:03Z",
            "2026-10-10T01:02:60Z",
            "2026-10-10T01:02:03+09:00",
            "x2026-10-10T01:02:03Z",
            "2026-10-10T01:02:03Zx",
        ):
            self.assert_error(issue_payload(updated_at=bad), "invalid_input")

    def test_missing_fields_rejected(self):
        for drop in ("number", "title", "state", "body", "updated_at"):
            obj = json.loads(issue_payload())
            obj.pop(drop)
            self.assert_error(raw_object(obj), "invalid_input")

    def test_no_raw_input_echo(self):
        err = self.assert_error(
            issue_payload(title=MARKER, state="bogus"), "invalid_input"
        )
        self.assertNotIn("bogus", err.message)


class CanonicalIssueTests(unittest.TestCase):
    def test_canonical_type_validation(self):
        for bad in (None, 42, "x", {"a": 1}, ["x"]):
            with self.assertRaises(IssuePayloadError):
                canonical_issue(bad)

    def test_canonical_field_type_validation(self):
        with self.assertRaises(IssuePayloadError):
            canonical_issue(
                DecodedIssue(
                    number="42",
                    title="t",
                    state="open",
                    body=None,
                    updated_at=UPDATED,
                )
            )
        with self.assertRaises(IssuePayloadError):
            canonical_issue(
                DecodedIssue(
                    number=42,
                    title="t",
                    state="open",
                    body=42,
                    updated_at=UPDATED,
                )
            )


if __name__ == "__main__":
    unittest.main()
