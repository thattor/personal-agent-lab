"""Pure constructor for fixed GitHub read requests (EXE02-request/1, PAL v5).

This module validates a C07 capability/arguments pair and builds a fixed
``gh api`` argv tuple for the pinned repository thattor/personal-agent-lab.
It never executes anything: no subprocess, network, credential, environment,
filesystem or DB access, and it issues no operation or receipt IDs.

A ``ReadRequest`` is not an authorization decision. Its existence does not
prove a grant, an operation reservation, or that it came from
``prepare_read``. Authority checks, C15 reservation, process execution and
timeout enforcement, response parsing and provenance all belong to EXE01
and the EXE02 executor. Only ``prepare_read`` output is the supported
request form.
"""

from dataclasses import dataclass
from urllib.parse import quote

__all__ = ("ReadRequest", "ReadRequestError", "prepare_read")

REPOSITORY = "thattor/personal-agent-lab"
MAX_TIMEOUT_SECONDS = 30
MAX_BYTES = 1048576

_ISSUE_CAPABILITY = "github.issue.read"
_FILE_CAPABILITY = "github.file.read"
_CAPABILITIES = frozenset((_ISSUE_CAPABILITY, _FILE_CAPABILITY))
_HEX_DIGITS = frozenset("0123456789abcdef")

_MSG_CAPABILITY = "capability must be github.issue.read or github.file.read"
_MSG_ARGUMENT_KEYS = "arguments must be a dict with exactly the required str keys"
_MSG_REPOSITORY_TYPE = "repository must be a str"
_MSG_REPOSITORY_DENIED = "repository is not thattor/personal-agent-lab"
_MSG_NUMBER = "number must be an int >= 1 with at most 63 bits"
_MSG_PATH = "path must be a nonempty relative POSIX path without escapes or controls"
_MSG_REF = "ref must be a lowercase 40-hex commit SHA"
_MSG_TIMEOUT_TYPE = "timeout_seconds must be an int >= 1"
_MSG_TIMEOUT_LIMIT = "timeout_seconds exceeds 30"
_MSG_MAX_BYTES_TYPE = "max_bytes must be an int >= 1"
_MSG_MAX_BYTES_LIMIT = "max_bytes exceeds 1048576"


class ReadRequestError(Exception):
    """Bounded rejection raised by ``prepare_read``.

    ``code`` is one of ``"invalid_input"``, ``"denied"`` or ``"limit"``;
    ``message`` is a fixed constant string that never contains raw input
    data, and the exception retains no caught-exception context.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ReadRequest:
    """Immutable, validated read request for a fixed ``gh api`` argv.

    Only ``prepare_read`` output is the supported form; direct construction
    is not validated. The value is not an authorization gate.
    """

    capability: str
    argv: tuple[str, ...]
    timeout_seconds: int
    max_bytes: int


def _valid_path(path: str) -> bool:
    if type(path) is not str or not path:
        return False
    for ch in path:
        code = ord(ch)
        if (
            code <= 0x1F
            or code == 0x7F
            or 0xD800 <= code <= 0xDFFF
            or ch == "\\"
        ):
            return False
    for segment in path.split("/"):
        if segment in ("", ".", ".."):
            return False
    return True


def _valid_ref(ref: str) -> bool:
    return (
        type(ref) is str
        and len(ref) == 40
        and all(ch in _HEX_DIGITS for ch in ref)
    )


def prepare_read(
    capability: str,
    arguments: dict,
    *,
    timeout_seconds: int = MAX_TIMEOUT_SECONDS,
    max_bytes: int = MAX_BYTES,
) -> ReadRequest:
    """Validate a C07 read request and return an immutable ``ReadRequest``.

    Raises ``ReadRequestError`` on any rejection; never returns None or a
    partial value.
    """
    if type(capability) is not str or capability not in _CAPABILITIES:
        raise ReadRequestError("invalid_input", _MSG_CAPABILITY)

    if capability == _ISSUE_CAPABILITY:
        required_keys = {"repository", "number"}
    else:
        required_keys = {"repository", "path", "ref"}
    if (
        type(arguments) is not dict
        or any(type(key) is not str for key in arguments)
        or set(arguments) != required_keys
    ):
        raise ReadRequestError("invalid_input", _MSG_ARGUMENT_KEYS)

    repository = arguments["repository"]
    if type(repository) is not str:
        raise ReadRequestError("invalid_input", _MSG_REPOSITORY_TYPE)
    if repository != REPOSITORY:
        raise ReadRequestError("denied", _MSG_REPOSITORY_DENIED)

    if capability == _ISSUE_CAPABILITY:
        number = arguments["number"]
        if type(number) is not int or number < 1 or number.bit_length() > 63:
            raise ReadRequestError("invalid_input", _MSG_NUMBER)
        endpoint = "repos/" + REPOSITORY + "/issues/" + str(number)
    else:
        path = arguments["path"]
        ref = arguments["ref"]
        if not _valid_path(path):
            raise ReadRequestError("invalid_input", _MSG_PATH)
        if not _valid_ref(ref):
            raise ReadRequestError("invalid_input", _MSG_REF)
        encoded = "/".join(
            quote(segment, safe="") for segment in path.split("/")
        )
        endpoint = "repos/" + REPOSITORY + "/contents/" + encoded + "?ref=" + ref

    if type(timeout_seconds) is not int or timeout_seconds < 1:
        raise ReadRequestError("invalid_input", _MSG_TIMEOUT_TYPE)
    if timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise ReadRequestError("limit", _MSG_TIMEOUT_LIMIT)
    if type(max_bytes) is not int or max_bytes < 1:
        raise ReadRequestError("invalid_input", _MSG_MAX_BYTES_TYPE)
    if max_bytes > MAX_BYTES:
        raise ReadRequestError("limit", _MSG_MAX_BYTES_LIMIT)

    argv = ("gh", "api", "--method", "GET", "--hostname", "github.com", endpoint)
    return ReadRequest(capability, argv, timeout_seconds, max_bytes)
