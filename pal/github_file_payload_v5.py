"""Bounded decoder for the GitHub contents file object (PAL v5 slice D).

Local byte-processing helper only: no I/O, IDs, receipts, Git object hash
checking or provenance verification. blob_sha is provider metadata.
"""

import base64
import binascii
import dataclasses
import json

__all__ = ("DecodedFile", "FilePayloadError", "decode_file")

_HARD_MAX_BYTES = 1048576

_MSG_MAX_BYTES_INVALID = "max_bytes must be a positive int"
_MSG_MAX_BYTES_LIMIT = "max_bytes exceeds hard maximum"
_MSG_PAYLOAD_TYPE = "payload must be bytes"
_MSG_PAYLOAD_LIMIT = "payload exceeds max_bytes"
_MSG_PAYLOAD_UTF8 = "payload is not valid UTF-8"
_MSG_DUPLICATE_KEYS = "payload has duplicate JSON keys"
_MSG_NON_FINITE = "payload has non-finite JSON number"
_MSG_JSON = "payload is not valid JSON"
_MSG_OBJECT = "payload is not a JSON file object"
_MSG_TYPE = "type must be file"
_MSG_ENCODING = "encoding must be base64"
_MSG_CONTENT = "content must be a string"
_MSG_SIZE = "size must be a nonnegative int"
_MSG_SHA = "sha must be 40 lowercase hex"
_MSG_FORBIDDEN_FIELDS = "target and submodule_git_url are not allowed"
_MSG_SIZE_LIMIT = "size exceeds max_bytes"
_MSG_BASE64 = "content is not canonical base64"
_MSG_DECODED_LIMIT = "decoded content exceeds max_bytes"
_MSG_SIZE_MISMATCH = "size does not match decoded content"
_MSG_CONTENT_UTF8 = "content is not valid UTF-8"

_B64_ALPHABET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
)
_HEX_DIGITS = frozenset("0123456789abcdef")


class FilePayloadError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


class _DuplicateKey(Exception):
    pass


class _NonFinite(Exception):
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class DecodedFile:
    content: str
    data: bytes
    byte_count: int
    blob_sha: str


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise _DuplicateKey
        out[key] = value
    return out


def _reject_constant(raw):
    raise _NonFinite


def _finite_float(raw):
    value = float(raw)
    if value == float("inf") or value == float("-inf"):
        raise _NonFinite
    return value


def decode_file(payload: bytes, *, max_bytes: int = _HARD_MAX_BYTES) -> DecodedFile:
    if type(max_bytes) is not int or max_bytes <= 0:
        raise FilePayloadError("invalid_input", _MSG_MAX_BYTES_INVALID)
    if max_bytes > _HARD_MAX_BYTES:
        raise FilePayloadError("limit", _MSG_MAX_BYTES_LIMIT)
    if type(payload) is not bytes:
        raise FilePayloadError("invalid_input", _MSG_PAYLOAD_TYPE)
    if len(payload) > max_bytes:
        raise FilePayloadError("limit", _MSG_PAYLOAD_LIMIT)

    failure = None
    text = ""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        failure = _MSG_PAYLOAD_UTF8
    if failure is not None:
        raise FilePayloadError("invalid_input", failure)

    failure = None
    obj = None
    try:
        obj = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except _DuplicateKey:
        failure = _MSG_DUPLICATE_KEYS
    except _NonFinite:
        failure = _MSG_NON_FINITE
    except (ValueError, RecursionError):
        failure = _MSG_JSON
    if failure is not None:
        raise FilePayloadError("invalid_input", failure)

    if type(obj) is not dict:
        raise FilePayloadError("invalid_input", _MSG_OBJECT)

    kind = obj.get("type")
    if type(kind) is not str or kind != "file":
        raise FilePayloadError("invalid_input", _MSG_TYPE)

    encoding = obj.get("encoding")
    if type(encoding) is not str or encoding != "base64":
        raise FilePayloadError("invalid_input", _MSG_ENCODING)

    content = obj.get("content")
    if type(content) is not str:
        raise FilePayloadError("invalid_input", _MSG_CONTENT)

    size = obj.get("size")
    if type(size) is not int or size < 0:
        raise FilePayloadError("invalid_input", _MSG_SIZE)

    sha = obj.get("sha")
    if (
        type(sha) is not str
        or len(sha) != 40
        or any(c not in _HEX_DIGITS for c in sha)
    ):
        raise FilePayloadError("invalid_input", _MSG_SHA)

    if "target" in obj or "submodule_git_url" in obj:
        raise FilePayloadError("invalid_input", _MSG_FORBIDDEN_FIELDS)

    if size > max_bytes:
        raise FilePayloadError("limit", _MSG_SIZE_LIMIT)

    stripped = content.replace("\r", "").replace("\n", "")
    if len(stripped) % 4 != 0 or any(
        c not in _B64_ALPHABET for c in stripped
    ):
        raise FilePayloadError("invalid_input", _MSG_BASE64)

    failure = None
    data = b""
    try:
        data = base64.b64decode(stripped, validate=True)
    except (binascii.Error, ValueError):
        failure = _MSG_BASE64
    if failure is None and base64.b64encode(data) != stripped.encode("ascii"):
        failure = _MSG_BASE64
    if failure is not None:
        raise FilePayloadError("invalid_input", failure)

    if len(data) > max_bytes:
        raise FilePayloadError("limit", _MSG_DECODED_LIMIT)
    if len(data) != size:
        raise FilePayloadError("invalid_input", _MSG_SIZE_MISMATCH)

    failure = None
    decoded_text = ""
    try:
        decoded_text = data.decode("utf-8")
    except UnicodeDecodeError:
        failure = _MSG_CONTENT_UTF8
    if failure is not None:
        raise FilePayloadError("invalid_input", failure)

    return DecodedFile(
        content=decoded_text,
        data=data,
        byte_count=len(data),
        blob_sha=sha,
    )
