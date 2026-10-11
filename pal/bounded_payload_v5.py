"""Bounded in-memory byte accumulator for PAL v5 (EXE02-bytes/1).

Local preparation component only: no I/O, no threading, no shared state.
"""

MAX_PAYLOAD_BYTES = 1048576

INVALID_INPUT = "invalid_input"
LIMIT = "limit"
INVALID_INPUT_MESSAGE = "invalid payload input"
LIMIT_MESSAGE = "payload byte limit exceeded"

__all__ = [
    "MAX_PAYLOAD_BYTES",
    "INVALID_INPUT",
    "LIMIT",
    "INVALID_INPUT_MESSAGE",
    "LIMIT_MESSAGE",
    "PayloadBuffer",
    "PayloadLimitError",
]


class PayloadLimitError(Exception):
    """Error with a fixed code/message pair; never carries caller input."""

    def __init__(self, code):
        if type(code) is str and code == LIMIT:
            code = LIMIT
            message = LIMIT_MESSAGE
        else:
            code = INVALID_INPUT
            message = INVALID_INPUT_MESSAGE
        super().__init__(message)
        self.code = code
        self.message = message


class PayloadBuffer:
    """In-memory byte accumulator bounded by a strict positive int maximum."""

    __slots__ = ("_max_bytes", "_data")

    def __init__(self, *, max_bytes=MAX_PAYLOAD_BYTES):
        if type(max_bytes) is not int:
            raise PayloadLimitError(INVALID_INPUT)
        if max_bytes <= 0:
            raise PayloadLimitError(INVALID_INPUT)
        if max_bytes > MAX_PAYLOAD_BYTES:
            raise PayloadLimitError(LIMIT)
        self._max_bytes = max_bytes
        self._data = bytearray()

    def append(self, chunk):
        if type(chunk) is not bytes:
            raise PayloadLimitError(INVALID_INPUT)
        if len(self._data) + len(chunk) > self._max_bytes:
            raise PayloadLimitError(LIMIT)
        self._data += chunk

    def getvalue(self):
        return bytes(self._data)

    @property
    def byte_count(self):
        return len(self._data)
