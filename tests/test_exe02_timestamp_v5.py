"""EXE02 timestamp boundary regressions; synthetic bytes and inert children only."""

import json
import unittest

from pal.github_issue_payload_v5 import IssuePayloadError, canonical_issue, decode_issue
from test_github_read_executor_v5 import (
    FILE_CAP, ISSUE_CAP, SHA, RecordingPopen, assert_failed, do_read,
    emit_script, file_args, file_payload, issue_payload, runner_for,
)

INVALID_DATES = (
    "2026-02-31T01:02:03Z",
    "2025-02-29T01:02:03Z",
    "1900-02-29T01:02:03Z",
    "2026-04-31T01:02:03Z",
    "2026-06-31T01:02:03Z",
    "0000-01-01T01:02:03Z",
)
NON_ASCII = (
    "２０２６-10-17T01:02:03Z",
    "٢٠٢٦-10-17T01:02:03Z",
    "2026-10-1７T01:02:03Z",
    "2026-10-17T0１:02:03Z",
    "2026-10-17T01:0２:03Z",
    "2026-10-17T01:02:0３Z",
)
VALID_DATES = (
    "0001-01-01T00:00:00Z",
    "1900-02-28T23:59:59Z",
    "2000-02-29T00:00:00Z",
    "2024-02-29T01:02:03Z",
    "2026-10-17T01:02:03Z",
    "9999-12-31T23:59:59Z",
)


class Exe02TimestampTests(unittest.TestCase):
    def rejected_issue(self, stamp):
        with self.assertRaises(IssuePayloadError) as caught:
            decode_issue(issue_payload(updated_at=stamp))
        error = caught.exception
        self.assertEqual(error.code, "invalid_input")
        self.assertEqual(error.message, "updated_at must be a UTC timestamp")
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        if type(stamp) is str and stamp:
            self.assertNotIn(stamp, str(error))

    def test_impossible_calendar_dates_are_not_issue_versions(self):
        for stamp in INVALID_DATES:
            with self.subTest(stamp=stamp):
                self.rejected_issue(stamp)

    def test_unicode_digits_are_not_canonical_utc(self):
        for stamp in NON_ASCII:
            with self.subTest(stamp=stamp):
                self.rejected_issue(stamp)

    def test_real_calendar_dates_keep_exact_canonical_bytes(self):
        for stamp in VALID_DATES:
            with self.subTest(stamp=stamp):
                raw = issue_payload(updated_at=stamp)
                issue = decode_issue(raw)
                expected = {key: json.loads(raw)[key] for key in
                            ("number", "title", "state", "body", "updated_at")}
                self.assertEqual(issue.updated_at, stamp)
                self.assertEqual(canonical_issue(issue), json.dumps(
                    expected, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False, allow_nan=False,
                ).encode("utf-8"))

    def test_existing_closed_timestamp_grammar_is_preserved(self):
        for stamp in (
            None, True, 2026, "", "2026-10-17", "2026-10-17T01:02:03+00:00",
            "2026-10-17T01:02:03.000Z", "2026-10-17T01:02:60Z",
            "2026-10-17T24:00:00Z", "2026-10-17T01:02:03Z\n",
            "2026-10-17 01:02:03Z", "x" * 100000,
        ):
            with self.subTest(stamp_type=type(stamp).__name__):
                self.rejected_issue(stamp)

    def test_read_rejects_bad_provider_version_after_owned_child_exit(self):
        for stamp in (INVALID_DATES[0], INVALID_DATES[2], NON_ASCII[0]):
            with self.subTest(stamp=stamp):
                spawn = RecordingPopen(emit_script(issue_payload(updated_at=stamp)))
                result = do_read(runner_for(popen=spawn))
                assert_failed(self, result)
                self.assertEqual(result.error, "updated_at must be a UTC timestamp")
                self.assertEqual(len(spawn.children), 1)
                self.assertEqual(spawn.children[0].returncode, 0)

    def test_read_rejects_invalid_host_clock_for_issue_and_file(self):
        for capability, arguments, payload in (
            (ISSUE_CAP, None, issue_payload()),
            (FILE_CAP, file_args(), file_payload()),
        ):
            for stamp in (INVALID_DATES[0], INVALID_DATES[2], NON_ASCII[0]):
                with self.subTest(capability=capability, stamp=stamp):
                    spawn = RecordingPopen(emit_script(payload))
                    runner = runner_for(popen=spawn, clock=lambda: stamp)
                    result = do_read(runner, capability=capability, arguments=arguments)
                    assert_failed(self, result)
                    self.assertEqual(result.error,
                                     "observation clock did not produce a valid timestamp")
                    self.assertEqual(len(spawn.children), 1)
                    self.assertEqual(spawn.children[0].returncode, 0)

    def test_valid_clock_preserves_issue_and_pinned_file_provenance(self):
        stamp = "2000-02-29T23:59:59Z"
        for capability, arguments, payload, version in (
            (ISSUE_CAP, None, issue_payload(updated_at=stamp), stamp),
            (FILE_CAP, file_args(), file_payload(), SHA),
        ):
            with self.subTest(capability=capability):
                spawn = RecordingPopen(emit_script(payload))
                result = do_read(
                    runner_for(popen=spawn, clock=lambda: stamp),
                    capability=capability, arguments=arguments,
                )
                self.assertEqual(result.status, "succeeded", result.error)
                self.assertEqual(result.observed_at, stamp)
                self.assertEqual(result.version, version)
                self.assertIsNotNone(result.body)
                self.assertIsNone(result.error)
                self.assertEqual(len(spawn.children), 1)
                self.assertEqual(spawn.children[0].returncode, 0)


if __name__ == "__main__":
    unittest.main()
