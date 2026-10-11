"""Byte integrity check of a saved body against host-supplied metadata.

VER01-integrity/1 preparation component. It compares byte length and SHA-256
only. It issues no Condition/Ref, saves no verification, judges no meaning and
performs no I/O. The host must prove that the expected metadata is canonical.
"""

import hashlib
from dataclasses import dataclass

__all__ = ("IntegrityCheck", "check_bytes")

_MAX_BYTES = 1048576
_SHA256_HEX_LENGTH = 64
_LOWER_HEX = frozenset("0123456789abcdef")

_MET = "met"
_UNMET = "unmet"
_UNKNOWN = "unknown"

_INVALID_EXPECTED_SHA256 = "invalid_expected_sha256"
_INVALID_EXPECTED_BYTES = "invalid_expected_bytes"
_INVALID_DATA = "invalid_data"
_DATA_EXCEEDS_LIMIT = "data_exceeds_limit"
_BYTE_COUNT_MISMATCH = "byte_count_mismatch"
_SHA256_MISMATCH = "sha256_mismatch"
_INTEGRITY_MATCH = "integrity_match"


@dataclass(frozen=True, slots=True)
class IntegrityCheck:
    """Outcome of one byte integrity check. It carries no input values."""

    status: str
    reason: str


def _is_sha256_hex(value):
    return (
        type(value) is str
        and len(value) == _SHA256_HEX_LENGTH
        and all(char in _LOWER_HEX for char in value)
    )


def _is_byte_count(value):
    return type(value) is int and 0 <= value <= _MAX_BYTES


def check_bytes(data, expected_sha256, expected_bytes):
    """Check data against an expected lowercase SHA-256 hex and byte count.

    Invalid metadata or non-bytes data returns unknown. Over-limit or
    mismatched data returns unmet. An over-limit or wrong-length body is
    never hashed.
    """
    if not _is_sha256_hex(expected_sha256):
        return IntegrityCheck(_UNKNOWN, _INVALID_EXPECTED_SHA256)
    if not _is_byte_count(expected_bytes):
        return IntegrityCheck(_UNKNOWN, _INVALID_EXPECTED_BYTES)
    if type(data) is not bytes:
        return IntegrityCheck(_UNKNOWN, _INVALID_DATA)
    byte_count = len(data)
    if byte_count > _MAX_BYTES:
        return IntegrityCheck(_UNMET, _DATA_EXCEEDS_LIMIT)
    if byte_count != expected_bytes:
        return IntegrityCheck(_UNMET, _BYTE_COUNT_MISMATCH)
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        return IntegrityCheck(_UNMET, _SHA256_MISMATCH)
    return IntegrityCheck(_MET, _INTEGRITY_MATCH)
