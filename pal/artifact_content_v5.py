"""ART01-content/1: bounded UTF-8 artifact content preparation.

Pure helper for PAL contract v5 C08. It validates the content and media type,
encodes the exact text as UTF-8 and hashes exactly those bytes. It mints no Ref,
key or ID, checks no sources, and performs no DB, filesystem, provider or network
access. ART-01 later owns WorkRef/source availability, saved IDs, idempotency and
C11 readback; an ArtifactContent is not a receipt or completion evidence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

__all__ = [
    "ALLOWED_MEDIA_TYPES",
    "MAX_CONTENT_BYTES",
    "ArtifactContent",
    "ArtifactContentError",
    "prepare_content",
]

MAX_CONTENT_BYTES = 1048576
ALLOWED_MEDIA_TYPES = frozenset({"text/plain", "text/markdown"})

INVALID_INPUT = "invalid_input"
LIMIT = "limit"


class ArtifactContentError(ValueError):
    """Bounded failure: code is invalid_input or limit; message is fixed text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True, slots=True)
class ArtifactContent:
    """Prepared artifact value; build it with prepare_content()."""

    content: str = field(repr=False)
    media_type: str
    data: bytes = field(repr=False)
    sha256: str
    byte_count: int


def prepare_content(content: str, media_type: str) -> ArtifactContent:
    """Return the exact UTF-8 bytes and sha256 of content, or raise.

    Checks run in order: content type, media_type type, media_type value,
    UTF-8 encodability, then the inclusive MAX_CONTENT_BYTES limit.
    """
    if type(content) is not str:
        raise ArtifactContentError(INVALID_INPUT, "content must be str")
    if type(media_type) is not str:
        raise ArtifactContentError(INVALID_INPUT, "media_type must be str")
    if media_type not in ALLOWED_MEDIA_TYPES:
        raise ArtifactContentError(
            INVALID_INPUT, "media_type must be text/plain or text/markdown"
        )
    # Raise after the handler exits so no encoder exception or input is chained.
    try:
        data = content.encode("utf-8")
    except UnicodeEncodeError:
        data = None
    if data is None:
        raise ArtifactContentError(INVALID_INPUT, "content must be valid UTF-8 text")
    if len(data) > MAX_CONTENT_BYTES:
        raise ArtifactContentError(LIMIT, "content exceeds 1048576 UTF-8 bytes")
    return ArtifactContent(
        content=content,
        media_type=media_type,
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        byte_count=len(data),
    )
