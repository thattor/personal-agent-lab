"""Tests for pal.github_file_payload_v5 (PAL v5 slice D).

All fixtures are synthetic, built with json.dumps/base64 or hand-written
bytes; nothing is copied from real repository responses.
"""

import base64
import dataclasses
import json
import unittest

import pal.github_file_payload_v5 as module
from pal.github_file_payload_v5 import (
    DecodedFile,
    FilePayloadError,
    decode_file,
)

SHA = "0123456789abcdef0123456789abcdef01234567"
MARKER = "SECRET-MARKER-7Q"


def b64(data, newline=None):
    text = base64.b64encode(data).decode("ascii")
    if newline is None:
        return text
    return newline.join(text[i:i + 60] for i in range(0, len(text), 60))


def payload(content, size, sha=SHA, extra=None, drop=()):
    obj = {
        "type": "file",
        "encoding": "base64",
        "content": content,
        "size": size,
        "sha": sha,
    }
    if extra:
        obj.update(extra)
    for key in drop:
        obj.pop(key, None)
    return json.dumps(obj).encode("utf-8")


def payload_for(data, **kwargs):
    return payload(b64(data), len(data), **kwargs)


class DecodeFileTests(unittest.TestCase):
    maxDiff = None

    def assert_error(self, raw, code, message, **kwargs):
        with self.assertRaises(FilePayloadError) as cm:
            decode_file(raw, **kwargs)
        err = cm.exception
        self.assertIs(type(err), FilePayloadError)
        self.assertEqual(err.code, code)
        self.assertEqual(err.message, message)
        self.assertEqual(str(err), message)
        self.assertEqual(err.args, (message,))
        self.assertTrue(message.isascii())
        self.assertLessEqual(len(message), 80)
        self.assertIsNone(err.__cause__)
        self.assertIsNone(err.__context__)
        for rendered in (str(err), repr(err), str(err.args)):
            self.assertNotIn(MARKER, rendered)
        return err

    # --- Valid inputs -----------------------------------------------------

    def test_t01_wrapped_known_text(self):
        text = "h\u00e9llo \u4e16\u754c\n" * 20
        data = text.encode("utf-8")
        wrapped = b64(data, "\n") + "\n"
        result = decode_file(payload(wrapped, len(data)))
        self.assertIs(type(result), DecodedFile)
        self.assertEqual(result.content, text)
        self.assertEqual(result.data, data)
        self.assertEqual(result.byte_count, len(data))
        self.assertEqual(result.blob_sha, SHA)

    def test_t02_literal_vector(self):
        result = decode_file(payload("aGVsbG8=", 5))
        self.assertEqual(result.content, "hello")
        self.assertEqual(result.data, b"hello")
        self.assertEqual(result.byte_count, 5)
        self.assertEqual(result.blob_sha, SHA)

    def test_t03_empty_file(self):
        for content in ("", "\n"):
            result = decode_file(payload(content, 0))
            self.assertEqual(result.content, "")
            self.assertEqual(result.data, b"")
            self.assertEqual(result.byte_count, 0)

    def test_t04_crlf_wrapping(self):
        data = b"crlf wrapped data block\n" * 30
        raw = payload(b64(data, "\r\n") + "\r\n", len(data))
        result = decode_file(raw)
        self.assertEqual(result.data, data)
        self.assertEqual(result.content, data.decode("utf-8"))

    def test_t05_no_normalization(self):
        data = b"a\r\nb\rc\n"
        result = decode_file(payload_for(data))
        self.assertEqual(result.data, data)
        self.assertEqual(result.content, "a\r\nb\rc\n")

        decomposed = "e\u0301".encode("utf-8")
        result = decode_file(payload_for(decomposed))
        self.assertEqual(result.content, "e\u0301")
        self.assertNotEqual(result.content, "\u00e9")

        bom = "\ufeffbody".encode("utf-8")
        result = decode_file(payload_for(bom))
        self.assertEqual(result.content, "\ufeffbody")

    def test_t06_extra_fields_allowed(self):
        extra = {
            "name": "f.txt",
            "path": "dir/f.txt",
            "url": "https://example.invalid/api/x",
            "git_url": None,
            "html_url": None,
            "download_url": "https://example.invalid/dl",
            "_links": {
                "self": "https://example.invalid/api/x",
                "git": None,
                "html": None,
            },
        }
        result = decode_file(payload("aGVsbG8=", 5, extra=extra))
        self.assertEqual(result.content, "hello")

    def test_t07_dataclass_shape(self):
        self.assertTrue(dataclasses.is_dataclass(DecodedFile))
        names = [f.name for f in dataclasses.fields(DecodedFile)]
        self.assertEqual(names, ["content", "data", "byte_count", "blob_sha"])
        result = decode_file(payload("aGVsbG8=", 5))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.byte_count = 99
        self.assertFalse(hasattr(result, "__dict__"))
        self.assertIs(type(result.data), bytes)
        self.assertIs(type(result.content), str)
        self.assertIs(type(result.byte_count), int)
        self.assertIs(type(result.blob_sha), str)
        other = decode_file(payload("aGVsbG8=", 5))
        self.assertEqual(result, other)
        self.assertEqual(hash(result), hash(other))

    # --- Bounds and argument types ---------------------------------------

    def test_t08_size_bounds(self):
        small = payload("aGVsbG8=", 5)
        self.assertEqual(decode_file(small).byte_count, 5)

        padded = small + b" " * (1048576 - len(small))
        self.assertEqual(len(padded), 1048576)
        self.assertEqual(decode_file(padded).byte_count, 5)
        self.assertEqual(
            decode_file(padded, max_bytes=1048576).byte_count, 5
        )
        self.assert_error(
            padded + b" ", "limit", "payload exceeds max_bytes"
        )
        self.assert_error(
            small,
            "limit",
            "payload exceeds max_bytes",
            max_bytes=len(small) - 1,
        )

    def test_t09_max_bytes(self):
        raw = payload("aGVsbG8=", 5)

        class IntSub(int):
            pass

        for bad in (True, False, 0, -1, 1.0, "10", None, IntSub(10)):
            self.assert_error(
                raw,
                "invalid_input",
                "max_bytes must be a positive int",
                max_bytes=bad,
            )
        self.assert_error(
            raw,
            "limit",
            "max_bytes exceeds hard maximum",
            max_bytes=1048577,
        )
        self.assert_error(
            "x",
            "invalid_input",
            "max_bytes must be a positive int",
            max_bytes=0,
        )
        with self.assertRaises(TypeError):
            decode_file(raw, 10)

    def test_t10_payload_type(self):
        class BytesSub(bytes):
            pass

        for bad in (
            "{}",
            bytearray(b"{}"),
            memoryview(b"{}"),
            BytesSub(b"{}"),
            None,
            5,
        ):
            self.assert_error(bad, "invalid_input", "payload must be bytes")

    # --- Raw UTF-8 and JSON -----------------------------------------------

    def test_t11_raw_utf8(self):
        for raw in (b"\xff", b"\xc0\xaf", b"\xed\xa0\x80"):
            self.assert_error(
                raw, "invalid_input", "payload is not valid UTF-8"
            )
        bom_json = b"\xef\xbb\xbf" + payload("aGVsbG8=", 5)
        self.assert_error(
            bom_json, "invalid_input", "payload is not valid JSON"
        )

    def test_t12_malformed_json(self):
        for raw in (
            b"",
            b" ",
            b"{",
            b'{"a":',
            b'{"type": "file",}',
            b"{} trailing",
            b'{"a": ' + b"1" * 5000 + b"}",
        ):
            self.assert_error(
                raw, "invalid_input", "payload is not valid JSON"
            )
        deep = b"[" * 200000
        self.assert_error(
            deep, "invalid_input", "payload is not valid JSON"
        )

    def test_t13_duplicate_keys(self):
        dup_top = (
            b'{"type": "file", "type": "file", "encoding": "base64", '
            b'"content": "aGVsbG8=", "size": 5, "sha": "'
            + SHA.encode()
            + b'"}'
        )
        self.assert_error(
            dup_top, "invalid_input", "payload has duplicate JSON keys"
        )
        dup_equal = b'{"a": 1, "a": 1, "type": "file"}'
        self.assert_error(
            dup_equal, "invalid_input", "payload has duplicate JSON keys"
        )
        dup_nested = (
            b'{"type": "file", "encoding": "base64", '
            b'"content": "aGVsbG8=", "size": 5, "sha": "'
            + SHA.encode()
            + b'", "x": {"k": 1, "k": 2}}'
        )
        self.assert_error(
            dup_nested, "invalid_input", "payload has duplicate JSON keys"
        )

    def test_t14_non_finite_numbers(self):
        base = (
            b'{"type": "file", "encoding": "base64", '
            b'"content": "aGVsbG8=", "size": 5, "sha": "'
            + SHA.encode()
            + b'", "x": '
        )
        for token in (b"NaN", b"Infinity", b"-Infinity", b"1e400"):
            self.assert_error(
                base + token + b"}",
                "invalid_input",
                "payload has non-finite JSON number",
            )

    # --- File object shape -------------------------------------------------

    def test_t15_not_an_object(self):
        entry = json.dumps(
            {
                "type": "file",
                "encoding": "base64",
                "content": "aGVsbG8=",
                "size": 5,
                "sha": SHA,
            }
        )
        for raw in (
            f"[{entry}, {entry}]".encode("utf-8"),
            b'"text"',
            b"5",
            b"3.5",
            b"null",
            b"true",
        ):
            self.assert_error(
                raw, "invalid_input", "payload is not a JSON file object"
            )

    def test_t16_type_field(self):
        for value in ("dir", "symlink", "submodule", "File", "FILE", 1, None, True):
            self.assert_error(
                payload("aGVsbG8=", 5, extra={"type": value}),
                "invalid_input",
                "type must be file",
            )
        self.assert_error(
            payload("aGVsbG8=", 5, drop=("type",)),
            "invalid_input",
            "type must be file",
        )

    def test_t17_encoding_field(self):
        for value in ("none", "", "BASE64", "Base64", None, 64, True):
            self.assert_error(
                payload("aGVsbG8=", 5, extra={"encoding": value}),
                "invalid_input",
                "encoding must be base64",
            )
        self.assert_error(
            payload("aGVsbG8=", 5, drop=("encoding",)),
            "invalid_input",
            "encoding must be base64",
        )

    def test_t18_content_field(self):
        for value in (None, 5, ["aGVs"], True, 1.0, {"x": 1}):
            self.assert_error(
                payload("aGVsbG8=", 5, extra={"content": value}),
                "invalid_input",
                "content must be a string",
            )
        self.assert_error(
            payload("aGVsbG8=", 5, drop=("content",)),
            "invalid_input",
            "content must be a string",
        )

    def test_t19_size_field(self):
        for value in (None, -1, 1.0, True, "5", [5]):
            self.assert_error(
                payload("aGVsbG8=", 5, extra={"size": value}),
                "invalid_input",
                "size must be a nonnegative int",
            )
        self.assert_error(
            payload("aGVsbG8=", 5, drop=("size",)),
            "invalid_input",
            "size must be a nonnegative int",
        )

    def test_t20_sha_field(self):
        for bad in (
            "A" * 40,
            "a" * 39,
            "a" * 41,
            "a" * 39 + "g",
            "a" * 64,
            "a" * 39 + "\n",
            "a" * 39 + " ",
            12345,
            None,
            True,
        ):
            self.assert_error(
                payload("aGVsbG8=", 5, extra={"sha": bad}),
                "invalid_input",
                "sha must be 40 lowercase hex",
            )
        self.assert_error(
            payload("aGVsbG8=", 5, drop=("sha",)),
            "invalid_input",
            "sha must be 40 lowercase hex",
        )

    def test_t21_forbidden_fields(self):
        for extra in (
            {"target": "branch"},
            {"target": None},
            {"submodule_git_url": "git://example.invalid/x"},
            {"submodule_git_url": None},
        ):
            self.assert_error(
                payload("aGVsbG8=", 5, extra=extra),
                "invalid_input",
                "target and submodule_git_url are not allowed",
            )

    # --- Size, Base64 and decoded text ------------------------------------

    def test_t22_declared_size_vs_max(self):
        self.assert_error(
            payload("!!!!", 201), "limit", "size exceeds max_bytes", max_bytes=200
        )
        raw = payload("aGVsbG8=", 201)
        self.assert_error(
            raw, "limit", "size exceeds max_bytes", max_bytes=200
        )
        raw_mismatch = payload("aGVsbG8=", 200)
        self.assert_error(
            raw_mismatch,
            "invalid_input",
            "size does not match decoded content",
            max_bytes=200,
        )

    def test_t23_invalid_base64(self):
        cases = [
            "aGVs G8=",
            "aGVs\tG8=",
            "aGVs\x0bG8=",
            "aGVs\x0cG8=",
            "aGVs\u2028G8=",
            "aGVs\u0085G8=",
            "aGVs-G8=",
            "aGVs_G8=",
            "aGVsbG8",
            "aGVsbG8=====",
            "aGVs====",
            "aGVs=G8=",
            "aGV",
            "aGVs\u00e9G8=",
            "QR==",
            "QUJ=",
            "aGVsbG9=",
        ]
        for content in cases:
            with self.subTest(content=content):
                self.assert_error(
                    payload(content, 5),
                    "invalid_input",
                    "content is not canonical base64",
                )

    def test_t24_size_mismatch(self):
        for size in (4, 6):
            self.assert_error(
                payload("aGVsbG8=", size),
                "invalid_input",
                "size does not match decoded content",
            )

    def test_t25_binary_content(self):
        for data in (b"\xff\xfe\x00", b"\xe3\x81", b"\x80"):
            self.assert_error(
                payload_for(data),
                "invalid_input",
                "content is not valid UTF-8",
            )

    def test_t26_base64_overhead(self):
        data = b"x" * 600
        raw = payload_for(data)
        self.assertGreater(len(raw), 700)
        self.assert_error(
            raw, "limit", "payload exceeds max_bytes", max_bytes=700
        )
        result = decode_file(raw)
        self.assertEqual(result.data, data)
        self.assertEqual(result.byte_count, 600)

    # --- Error hygiene -----------------------------------------------------

    def test_t27_no_input_echo(self):
        marked_sha = payload(
            "aGVsbG8=", 5, sha="z" * 40, extra={"note": MARKER}
        )
        self.assertIn(MARKER.encode("ascii"), marked_sha)
        self.assert_error(
            marked_sha, "invalid_input", "sha must be 40 lowercase hex"
        )

        marked_json = MARKER.encode("ascii") + payload("aGVsbG8=", 5)
        self.assert_error(
            marked_json, "invalid_input", "payload is not valid JSON"
        )

        marked_dup = (
            b'{"note": "'
            + MARKER.encode("ascii")
            + b'", "note": "x", "type": "file"}'
        )
        self.assert_error(
            marked_dup, "invalid_input", "payload has duplicate JSON keys"
        )

        marked_b64 = payload(
            "aGVs" + MARKER + "==", 5, extra={"note": MARKER}
        )
        self.assert_error(
            marked_b64, "invalid_input", "content is not canonical base64"
        )

    def test_t28_all_export(self):
        self.assertEqual(len(module.__all__), 3)
        self.assertEqual(
            set(module.__all__),
            {"DecodedFile", "FilePayloadError", "decode_file"},
        )


if __name__ == "__main__":
    unittest.main()
