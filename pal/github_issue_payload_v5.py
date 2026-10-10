"""Bounded decoder for the GitHub issue object (PAL v5 EXE-02 leaf).

Local byte-processing helper only: no I/O, IDs, receipts or provenance
verification. ``issues/N`` also answers for pull-request numbers, so any
payload containing a ``pull_request`` member is rejected outright.

Only the five fixed fields — number, title, state, body (str or explicit
JSON null) and updated_at — are validated and retained. Every other
response member (URLs, tokens, user, labels, repository data) is discarded
and is never serialized into the canonical output. ``canonical_issue``
emits a small sorted-key JSON encoding of exactly those five fields.
"""

import dataclasses
import json
import re

__all__ = (
    "DecodedIssue",
    "IssuePayloadError",
    "canonical_issue",
    "decode_issue",
)

_HARD_MAX_BYTES = 1048576
_MAX_NUMBER = (1 << 63) - 1
_MAX_TITLE_BYTES = 4096
_MAX_BODY_BYTES = 262144
_STATES = frozenset(("open", "closed"))
_UPDATED_AT = re.compile(
    r"\A\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])"
    r"T([01]\d|2[0-3]):[0-5]\d:[0-5]\dZ\Z"
)

_MSG_MAX_BYTES_INVALID = "max_bytes must be a positive int"
_MSG_MAX_BYTES_LIMIT = "max_bytes exceeds hard maximum"
_MSG_PAYLOAD_TYPE = "payload must be bytes"
_MSG_PAYLOAD_LIMIT = "payload exceeds max_bytes"
_MSG_PAYLOAD_UTF8 = "payload is not valid UTF-8"
_MSG_DUPLICATE_KEYS = "payload has duplicate JSON keys"
_MSG_NON_FINITE = "payload has non-finite JSON number"
_MSG_JSON = "payload is not valid JSON"
_MSG_OBJECT = "payload is not a JSON issue object"
_MSG_PULL_REQUEST = "payload is a pull request, not an issue"
_MSG_NUMBER = "number must be an int >= 1 with at most 63 bits"
_MSG_TITLE = "title must be a bounded str"
_MSG_STATE = "state must be open or closed"
_MSG_BODY = "body must be a bounded str or null"
_MSG_UPDATED_AT = "updated_at must be a UTC timestamp"
_MSG_ISSUE_TYPE = "issue must be a DecodedIssue"


class IssuePayloadError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


class _DuplicateKey(Exception):
    pass


class _NonFinite(Exception):
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class DecodedIssue:
    """The five retained issue fields; ``body`` keeps an explicit null."""

    number: int
    title: str
    state: str
    body: str | None
    updated_at: str


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


def _bounded_str(value, limit):
    if type(value) is not str:
        return False
    try:
        return len(value.encode("utf-8")) <= limit
    except UnicodeEncodeError:
        return False


def decode_issue(payload: bytes, *, max_bytes: int = _HARD_MAX_BYTES) -> DecodedIssue:
    """Decode a bounded GitHub issue JSON payload.

    Raises ``IssuePayloadError`` on any rejection; never returns a partial
    value and never retains unlisted response members.
    """
    if type(max_bytes) is not int or max_bytes <= 0:
        raise IssuePayloadError("invalid_input", _MSG_MAX_BYTES_INVALID)
    if max_bytes > _HARD_MAX_BYTES:
        raise IssuePayloadError("limit", _MSG_MAX_BYTES_LIMIT)
    if type(payload) is not bytes:
        raise IssuePayloadError("invalid_input", _MSG_PAYLOAD_TYPE)
    if len(payload) > max_bytes:
        raise IssuePayloadError("limit", _MSG_PAYLOAD_LIMIT)

    failure = None
    text = ""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        failure = _MSG_PAYLOAD_UTF8
    if failure is not None:
        raise IssuePayloadError("invalid_input", failure)

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
        raise IssuePayloadError("invalid_input", failure)

    if type(obj) is not dict:
        raise IssuePayloadError("invalid_input", _MSG_OBJECT)

    if "pull_request" in obj:
        raise IssuePayloadError("invalid_input", _MSG_PULL_REQUEST)

    number = obj.get("number")
    if type(number) is not int or not 1 <= number <= _MAX_NUMBER:
        raise IssuePayloadError("invalid_input", _MSG_NUMBER)

    title = obj.get("title")
    if not _bounded_str(title, _MAX_TITLE_BYTES):
        raise IssuePayloadError("invalid_input", _MSG_TITLE)

    state = obj.get("state")
    if type(state) is not str or state not in _STATES:
        raise IssuePayloadError("invalid_input", _MSG_STATE)

    if "body" not in obj or (
        obj["body"] is not None and not _bounded_str(obj["body"], _MAX_BODY_BYTES)
    ):
        raise IssuePayloadError("invalid_input", _MSG_BODY)

    updated_at = obj.get("updated_at")
    if type(updated_at) is not str or _UPDATED_AT.fullmatch(updated_at) is None:
        raise IssuePayloadError("invalid_input", _MSG_UPDATED_AT)

    return DecodedIssue(
        number=number,
        title=title,
        state=state,
        body=obj["body"],
        updated_at=updated_at,
    )


def canonical_issue(issue: DecodedIssue) -> bytes:
    """Small canonical JSON (sorted keys, tight separators) of exactly the
    five retained fields; an explicit null ``body`` is preserved."""
    if not isinstance(issue, DecodedIssue):
        raise IssuePayloadError("invalid_input", _MSG_ISSUE_TYPE)
    if (
        type(issue.number) is not int
        or type(issue.title) is not str
        or type(issue.state) is not str
        or (issue.body is not None and type(issue.body) is not str)
        or type(issue.updated_at) is not str
    ):
        raise IssuePayloadError("invalid_input", _MSG_ISSUE_TYPE)
    return json.dumps(
        {
            "number": issue.number,
            "title": issue.title,
            "state": issue.state,
            "body": issue.body,
            "updated_at": issue.updated_at,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
