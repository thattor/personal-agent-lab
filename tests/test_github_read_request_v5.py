"""Tests for pal.github_read_request_v5 (EXE02-request/1).

Pure validation tests: no subprocess, network, environment or filesystem use.
"""

import dataclasses
import unittest

from pal.github_read_request_v5 import (
    ReadRequest,
    ReadRequestError,
    prepare_read,
)

REPO = "thattor/personal-agent-lab"
SHA = "a" * 40
ISSUE_CAP = "github.issue.read"
FILE_CAP = "github.file.read"


def issue_args(number=42):
    return {"repository": REPO, "number": number}


def file_args(path="README.md", ref=SHA):
    return {"repository": REPO, "path": path, "ref": ref}


class DictSubclass(dict):
    pass


class PrepareReadTest(unittest.TestCase):
    def _error(self, *args, **kwargs):
        with self.assertRaises(ReadRequestError) as cm:
            prepare_read(*args, **kwargs)
        err = cm.exception
        self.assertIsNone(err.__cause__)
        self.assertIsNone(err.__context__)
        self.assertEqual(err.args, (err.message,))
        self.assertLessEqual(len(err.message), 120)
        return err

    def assert_invalid(self, *args, **kwargs):
        self.assertEqual("invalid_input", self._error(*args, **kwargs).code)

    def assert_denied(self, *args, **kwargs):
        self.assertEqual("denied", self._error(*args, **kwargs).code)

    def assert_limit(self, *args, **kwargs):
        self.assertEqual("limit", self._error(*args, **kwargs).code)

    def test_issue_exact_argv_and_defaults(self):
        req = prepare_read(ISSUE_CAP, issue_args(42))
        self.assertIsInstance(req, ReadRequest)
        self.assertEqual(req.capability, ISSUE_CAP)
        self.assertEqual(
            req.argv,
            (
                "gh",
                "api",
                "--method",
                "GET",
                "--hostname",
                "github.com",
                "repos/thattor/personal-agent-lab/issues/42",
            ),
        )
        self.assertEqual(req.timeout_seconds, 30)
        self.assertEqual(req.max_bytes, 1048576)

    def test_issue_explicit_bounds(self):
        req = prepare_read(
            ISSUE_CAP, issue_args(7), timeout_seconds=12, max_bytes=99
        )
        self.assertEqual(
            req.argv,
            (
                "gh",
                "api",
                "--method",
                "GET",
                "--hostname",
                "github.com",
                "repos/thattor/personal-agent-lab/issues/7",
            ),
        )
        self.assertEqual(req.timeout_seconds, 12)
        self.assertEqual(req.max_bytes, 99)

    def test_file_exact_argv(self):
        req = prepare_read(FILE_CAP, file_args("README.md"))
        self.assertEqual(req.capability, FILE_CAP)
        self.assertEqual(len(req.argv), 7)
        self.assertEqual(
            req.argv,
            (
                "gh",
                "api",
                "--method",
                "GET",
                "--hostname",
                "github.com",
                "repos/thattor/personal-agent-lab/contents/README.md?ref=" + SHA,
            ),
        )

    def test_file_unicode_and_metachar_encoding(self):
        req = prepare_read(FILE_CAP, file_args("docs/日本 語/a$b;c#d?e.md"))
        self.assertEqual(
            req.argv[-1],
            "repos/thattor/personal-agent-lab/contents/"
            "docs/%E6%97%A5%E6%9C%AC%20%E8%AA%9E/a%24b%3Bc%23d%3Fe.md"
            "?ref=" + SHA,
        )

    def test_file_percent_and_nested_path(self):
        req = prepare_read(FILE_CAP, file_args("a%b"))
        self.assertEqual(
            req.argv[-1],
            "repos/thattor/personal-agent-lab/contents/a%25b?ref=" + SHA,
        )
        req = prepare_read(FILE_CAP, file_args("x/y/z/file name.txt"))
        self.assertEqual(
            req.argv[-1],
            "repos/thattor/personal-agent-lab/contents/x/y/z/file%20name.txt"
            "?ref=" + SHA,
        )

    def test_file_ordinary_unicode_and_symbols_accepted(self):
        req = prepare_read(FILE_CAP, file_args("a b+c&=d/メモ.txt"))
        self.assertEqual(
            req.argv[-1],
            "repos/thattor/personal-agent-lab/contents/"
            "a%20b%2Bc%26%3Dd/%E3%83%A1%E3%83%A2.txt?ref=" + SHA,
        )

    def test_immutability(self):
        req = prepare_read(FILE_CAP, file_args())
        self.assertIsInstance(req.argv, tuple)
        self.assertTrue(all(type(item) is str for item in req.argv))
        for field in ("capability", "argv", "timeout_seconds", "max_bytes"):
            with self.assertRaises(dataclasses.FrozenInstanceError):
                setattr(req, field, None)
        self.assertTrue(
            issubclass(dataclasses.FrozenInstanceError, AttributeError)
        )

    def test_input_dict_mutation_after_call(self):
        args = file_args("README.md")
        req = prepare_read(FILE_CAP, args)
        args["path"] = "../escape"
        args["ref"] = "b" * 40
        args["extra"] = 1
        self.assertEqual(
            req.argv[-1],
            "repos/thattor/personal-agent-lab/contents/README.md?ref=" + SHA,
        )

    def test_capability_rejected(self):
        for bad in (
            "github.issue.write",
            "github.unknown.read",
            "GITHUB.ISSUE.READ",
            "",
            42,
            None,
            b"github.issue.read",
        ):
            self.assert_invalid(bad, issue_args())

    def test_capability_key_mismatch(self):
        self.assert_invalid(ISSUE_CAP, file_args())
        self.assert_invalid(FILE_CAP, issue_args())
        self.assert_invalid(FILE_CAP, {"repository": REPO, "number": 1})
        self.assert_invalid(
            ISSUE_CAP, {"repository": REPO, "path": "a", "ref": SHA}
        )

    def test_arguments_type_and_keys(self):
        self.assert_invalid(ISSUE_CAP, None)
        self.assert_invalid(ISSUE_CAP, "repository")
        self.assert_invalid(ISSUE_CAP, [("repository", REPO), ("number", 1)])
        self.assert_invalid(ISSUE_CAP, DictSubclass(issue_args()))
        self.assert_invalid(ISSUE_CAP, {"repository": REPO})
        self.assert_invalid(
            ISSUE_CAP, {"repository": REPO, "number": 1, "extra": 1}
        )
        self.assert_invalid(ISSUE_CAP, {"repository": REPO, "number": 1, 7: "x"})
        self.assert_invalid(ISSUE_CAP, {"repository": REPO, b"number": 1})

    def test_argument_keys_require_exact_str_type(self):
        class TextKey(str):
            pass

        self.assert_invalid(
            ISSUE_CAP, {TextKey("repository"): REPO, "number": 1}
        )
        self.assert_invalid(
            FILE_CAP, {"repository": REPO, TextKey("path"): "a", "ref": SHA}
        )

    def test_repository_denied_or_invalid(self):
        for foreign in (
            "other/repo",
            "Thattor/personal-agent-lab",
            REPO + " ",
            " " + REPO,
            REPO + "\n",
        ):
            self.assert_denied(
                ISSUE_CAP, {"repository": foreign, "number": 1}
            )
        self.assert_invalid(ISSUE_CAP, {"repository": 123, "number": 1})
        self.assert_invalid(ISSUE_CAP, {"repository": None, "number": 1})
        self.assert_invalid(
            FILE_CAP, {"repository": ["x"], "path": "a", "ref": SHA}
        )

    def test_issue_number_validation(self):
        for bad in (
            True,
            False,
            0,
            -1,
            -100,
            "1",
            1.0,
            None,
            2**63,
            2**64,
            10**5000,
        ):
            self.assert_invalid(ISSUE_CAP, issue_args(bad))
        req = prepare_read(ISSUE_CAP, issue_args(1))
        self.assertEqual(
            req.argv[-1], "repos/thattor/personal-agent-lab/issues/1"
        )
        req = prepare_read(ISSUE_CAP, issue_args(2**63 - 1))
        self.assertEqual(
            req.argv[-1],
            "repos/thattor/personal-agent-lab/issues/9223372036854775807",
        )

    def test_path_rejections(self):
        bad_paths = (
            "/abs",
            "a//b",
            "a/./b",
            "a/../b",
            "..",
            ".",
            "a/",
            "",
            "a\\b",
            "\\",
            "a\x00b",
            "a\nb",
            "a\x1fb",
            "a\x7fb",
            "a\ud800b",
            "\udfff",
            123,
            None,
            b"a/b",
        )
        for bad in bad_paths:
            self.assert_invalid(FILE_CAP, file_args(bad))

    def test_ref_rejections(self):
        bad_refs = (
            "A" * 40,
            "a" * 39,
            "a" * 41,
            "main",
            "refs/heads/main",
            "g" * 40,
            "a" * 39 + " ",
            123,
            None,
            True,
            b"a" * 40,
        )
        for bad in bad_refs:
            self.assert_invalid(FILE_CAP, file_args("README.md", bad))

    def test_ref_accepts_full_lowercase_hex(self):
        for ref in ("0" * 40, "f" * 40, "0123456789abcdef" * 2 + "01234567"):
            req = prepare_read(FILE_CAP, file_args("a.txt", ref))
            self.assertTrue(req.argv[-1].endswith("?ref=" + ref))

    def test_timeout_seconds_bounds(self):
        for ok in (1, 30):
            req = prepare_read(ISSUE_CAP, issue_args(), timeout_seconds=ok)
            self.assertEqual(req.timeout_seconds, ok)
        self.assert_limit(ISSUE_CAP, issue_args(), timeout_seconds=31)
        self.assert_limit(ISSUE_CAP, issue_args(), timeout_seconds=10**9)
        for bad in (0, -1, True, False, 30.0, "30", None):
            self.assert_invalid(ISSUE_CAP, issue_args(), timeout_seconds=bad)

    def test_max_bytes_bounds(self):
        for ok in (1, 1048576):
            req = prepare_read(ISSUE_CAP, issue_args(), max_bytes=ok)
            self.assertEqual(req.max_bytes, ok)
        self.assert_limit(ISSUE_CAP, issue_args(), max_bytes=1048577)
        for bad in (0, -5, True, False, 1.5, "1024", None):
            self.assert_invalid(ISSUE_CAP, issue_args(), max_bytes=bad)

    def test_rejection_ordering(self):
        self.assert_denied(
            FILE_CAP,
            {"repository": "other/repo", "path": "../x", "ref": "z"},
        )
        self.assert_denied(
            ISSUE_CAP,
            {"repository": "other/repo", "number": 1},
            timeout_seconds=99,
        )
        self.assert_invalid(
            "not.a.cap", {"repository": "other/repo", "number": 1}
        )
        self.assert_invalid(
            ISSUE_CAP, {"repository": REPO}, timeout_seconds=31
        )

    def test_no_raw_input_echo(self):
        sentinel = "S3NT1NEL-do-not-echo"
        cases = (
            (sentinel, issue_args(), {}),
            (
                FILE_CAP,
                {"repository": "x/" + sentinel, "path": "a", "ref": SHA},
                {},
            ),
            (FILE_CAP, file_args("../" + sentinel + "/x"), {}),
            (FILE_CAP, file_args("a", "ref-" + sentinel), {}),
            (FILE_CAP, file_args("a\ud800" + sentinel), {}),
        )
        for cap, args, kw in cases:
            err = self._error(cap, args, **kw)
            self.assertIn(err.code, ("invalid_input", "denied", "limit"))
            for surface in (
                str(err),
                repr(err),
                err.message,
                str(err.args),
                repr(err.args),
            ):
                self.assertNotIn(sentinel, surface)


if __name__ == "__main__":
    unittest.main()
