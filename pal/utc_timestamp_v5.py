"""Pure validation of the existing EXE02 second-resolution UTC wire format.

A valid calendar value is not evidence of freshness or clock trust. Callers
retain responsibility for source authority, observation and provenance.
"""

from datetime import datetime
import re

__all__ = ("is_canonical_utc",)

_WIRE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


def is_canonical_utc(value: object) -> bool:
    """Require exact ASCII YYYY-MM-DDTHH:MM:SSZ and a real calendar instant.

    Deliberately keep offsets, fractions and leap seconds outside the existing
    format. No normalization, wall-clock access or caller data is returned.
    """
    if type(value) is not str or len(value) != 20 or _WIRE.fullmatch(value) is None:
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True
