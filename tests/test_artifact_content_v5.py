"""Tests for ART01-content/1 bounded artifact content preparation."""

import dataclasses
import hashlib
import re
import unittest

from pal.artifact_content_v5 import (
    MAX_CONTENT_BYTES,
    ArtifactContent,
    ArtifactContentError,
    prepare_content,
)

MAX = 1048576
CODES = {"invalid_input", "limit"}
MARKER = "RAW-INPUT-MARKER"


def assert_error(test, content, media_type, code):
    with test.assertRaises(ArtifactContentError) as cm:
        prepare_content(content, media_type)
    test.assertEqual(cm.exception.code, code)
    return cm.exception


class KnownResultTests(unittest.TestCase):
    def test_ascii_plain_known_bytes_and_hash(self):
        result = prepare_content("hello", "text/plain")
        self.assertIsInstance(result, ArtifactContent)
        self.assertEqual(result.content, "hello")
        self.assertEqual(result.media_type, "text/plain")
        self.assertIs(type(result.data), bytes)
        self.assertEqual(result.data, b"hello")
        self.assertEqual(result.byte_count, 5)
        self.assertEqual(
            result.sha256,
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        )

    def test_markdown_known_hash(self):
        result = prepare_content("abc", "text/markdown")
        self.assertEqual(result.media_type, "text/markdown")
        self.assertEqual(result.data, b"abc")
        self.assertEqual(result.byte_count, 3)
        self.assertEqual(
            result.sha256,
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_empty_content(self):
        result = prepare_content("", "text/plain")
        self.assertEqual(result.content, "")
        self.assertEqual(result.data, b"")
        self.assertEqual(result.byte_count, 0)
        self.assertEqual(
            result.sha256,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_multibyte_counts_utf8_bytes(self):
        cases = [
            ("\u00e9", b"\xc3\xa9"),
            ("\u3042", b"\xe3\x81\x82"),
            ("\U0001f600", b"\xf0\x9f\x98\x80"),
            ("a\u00e9\u3042\U0001f600", b"a\xc3\xa9\xe3\x81\x82\xf0\x9f\x98\x80"),
        ]
        for text, expected in cases:
            with self.subTest(expected=expected):
                result = prepare_content(text, "text/plain")
                self.assertEqual(result.content, text)
                self.assertEqual(result.data, expected)
                self.assertEqual(result.byte_count, len(expected))
                self.assertEqual(result.sha256, hashlib.sha256(expected).hexdigest())

    def test_sha256_is_lowercase_hex(self):
        result = prepare_content("\u3042", "text/markdown")
        self.assertRegex(result.sha256, re.compile(r"\A[0-9a-f]{64}\Z"))

    def test_repeated_calls_are_equal(self):
        first = prepare_content("same", "text/plain")
        second = prepare_content("same", "text/plain")
        self.assertEqual(first, second)


class PreservationTests(unittest.TestCase):
    def test_line_endings_preserved(self):
        text = "a\r\nb\rc\n\r\n"
        result = prepare_content(text, "text/plain")
        self.assertEqual(result.content, text)
        self.assertEqual(result.data, b"a\r\nb\rc\n\r\n")
        self.assertEqual(result.byte_count, 9)

    def test_unicode_normalization_not_applied(self):
        nfc = prepare_content("\u00e9", "text/plain")
        nfd = prepare_content("e\u0301", "text/plain")
        self.assertEqual(nfc.content, "\u00e9")
        self.assertEqual(nfd.content, "e\u0301")
        self.assertEqual(nfc.data, b"\xc3\xa9")
        self.assertEqual(nfd.data, b"e\xcc\x81")
        self.assertEqual(nfd.byte_count, 3)
        self.assertNotEqual(nfc.sha256, nfd.sha256)

    def test_bom_nul_tabs_and_whitespace_preserved(self):
        text = "\ufeff lead\x00nul\ttab  trailing  "
        result = prepare_content(text, "text/markdown")
        self.assertEqual(result.content, text)
        self.assertEqual(result.data.decode("utf-8"), text)
        self.assertTrue(result.data.startswith(b"\xef\xbb\xbf"))


class LimitTests(unittest.TestCase):
    def test_limit_constant(self):
        self.assertEqual(MAX_CONTENT_BYTES, MAX)

    def test_exact_maximum_accepted(self):
        cases = {
            "one-byte": "a" * MAX,
            "two-byte": "\u00e9" * (MAX // 2),
            "three-byte": "\u3042" * 349525 + "a",
            "four-byte": "\U0001f600" * (MAX // 4),
        }
        for name, text in cases.items():
            with self.subTest(name):
                result = prepare_content(text, "text/markdown")
                self.assertEqual(result.byte_count, MAX)
                self.assertEqual(len(result.data), MAX)
                self.assertEqual(result.data, text.encode("utf-8"))
                self.assertEqual(result.sha256, hashlib.sha256(result.data).hexdigest())
                self.assertEqual(result.content, text)

    def test_excess_bytes_rejected(self):
        cases = {
            "one-byte": "a" * (MAX + 1),
            "two-byte": "\u00e9" * (MAX // 2) + "a",
            "three-byte-fewer-chars-than-limit": "\u3042" * 349526,
            "four-byte": "\U0001f600" * (MAX // 4) + "a",
        }
        for name, text in cases.items():
            with self.subTest(name):
                assert_error(self, text, "text/plain", "limit")


class InvalidInputTests(unittest.TestCase):
    def test_wrong_content_types(self):
        class TextSub(str):
            pass

        for value in (None, b"x", bytearray(b"x"), 1, True, ["x"], TextSub("x")):
            with self.subTest(type=type(value).__name__):
                assert_error(self, value, "text/plain", "invalid_input")

    def test_wrong_media_type_types(self):
        class TextSub(str):
            pass

        for value in (None, b"text/plain", 1, TextSub("text/plain")):
            with self.subTest(type=type(value).__name__):
                assert_error(self, "x", value, "invalid_input")

    def test_unsupported_media_types(self):
        for value in (
            "",
            "text/html",
            "TEXT/PLAIN",
            "Text/Markdown",
            "text/plain; charset=utf-8",
            " text/plain",
            "text/plain ",
            "text/x-markdown",
            "application/json",
        ):
            with self.subTest(media_type=value):
                assert_error(self, "x", value, "invalid_input")

    def test_surrogates_rejected(self):
        for value in ("\ud800", "a\udfffb", "\ud83d\ude00", "ok\udc80"):
            with self.subTest(length=len(value)):
                assert_error(self, value, "text/plain", "invalid_input")


class ErrorBoundaryTests(unittest.TestCase):
    def test_errors_are_bounded_without_raw_input_or_context(self):
        cases = [
            ("content type", MARKER.encode("ascii"), "text/plain", "invalid_input"),
            ("media type", "x", MARKER, "invalid_input"),
            ("surrogate", MARKER + "\ud800", "text/plain", "invalid_input"),
            ("limit", MARKER + "a" * MAX, "text/plain", "limit"),
        ]
        for name, content, media_type, code in cases:
            with self.subTest(name):
                err = assert_error(self, content, media_type, code)
                self.assertIn(err.code, CODES)
                self.assertIsInstance(err.message, str)
                self.assertTrue(err.message)
                self.assertLessEqual(len(err.message), 200)
                self.assertNotIsInstance(err, UnicodeError)
                self.assertIsNone(err.__cause__)
                self.assertIsNone(err.__context__)
                rendered = [str(err), repr(err), err.message]
                rendered.extend(repr(arg) for arg in err.args)
                rendered.extend(repr(value) for value in vars(err).values())
                for text in rendered:
                    self.assertLessEqual(len(text), 400)
                    self.assertNotIn(MARKER, text)


class ImmutabilityTests(unittest.TestCase):
    def test_fields_cannot_be_changed_added_or_deleted(self):
        result = prepare_content("hello", "text/plain")
        for name, value in (
            ("content", "x"),
            ("media_type", "text/markdown"),
            ("data", b"x"),
            ("sha256", "0" * 64),
            ("byte_count", 1),
        ):
            with self.subTest(name):
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    setattr(result, name, value)
        with self.assertRaises(AttributeError):
            result.extra = 1
        with self.assertRaises(AttributeError):
            del result.content
        self.assertIs(type(result.data), bytes)
        self.assertEqual(result.content, "hello")
        self.assertEqual(result.data, b"hello")
        self.assertEqual(result.byte_count, 5)


if __name__ == "__main__":
    unittest.main()
