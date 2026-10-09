"""READ01/1 HostReader: exact C11 read dispatch to explicit MEM/ART/VER owners.

Stateless and stdlib-only. It never opens a database, retries, falls back to
another owner, calls a model, or grants completion/dispatch authority. The host
purpose is propagated unchanged to the owner; an invalid purpose is a host bug
and raises ValueError before any dispatch.
"""
import re

from pal.contracts_v5 import ContractError, ErrorCode, Ref, RefKind, Result, WorkRef

__all__ = ['HostReader', 'PURPOSES', 'checked_result']

PURPOSES = frozenset({'model_context', 'verification', 'user_view'})
_BODY_KEYS = frozenset({'ref', 'content', 'media_type', 'hash', 'observed_at',
                        'source_refs', 'usable'})
_OPTIONAL_BODY_KEYS = frozenset({'work_ref', 'version'})
_HEX64 = re.compile(r'[0-9a-f]{64}')


def _unavailable(message='owner unavailable'):
    return Result.failure(ErrorCode.UNAVAILABLE, message)


def _valid_body(value, ref):
    """True only for the strict C11 response shape for exactly the requested Ref."""
    try:
        if (type(value) is not dict
                or not _BODY_KEYS <= set(value) <= _BODY_KEYS | _OPTIONAL_BODY_KEYS):
            return False
        if Ref.from_json(value['ref']).to_json() != ref:
            return False
        texts = (value['content'], value['media_type'], value['hash'], value['observed_at'])
        if any(type(text) is not str for text in texts):
            return False
        content, media_type, digest, observed_at = texts
        content.encode('utf-8')
        if not media_type or not observed_at or not _HEX64.fullmatch(digest):
            return False
        if value.get('work_ref') is not None:
            WorkRef.from_json(value['work_ref'])
        if 'version' in value and type(value['version']) is not str:
            return False
        if type(value['source_refs']) is not list:
            return False
        for item in value['source_refs']:
            Ref.from_json(item)
        return type(value['usable']) is bool
    except (ContractError, UnicodeError):
        return False


def checked_result(result, ref):
    """Return an owner Result unchanged if it is a valid C11 Result for ref (a Ref
    JSON dict); a non-Result or malformed success body becomes unavailable.
    Owner failures are valid and are passed through so their codes stay visible."""
    if type(result) is not Result:
        return _unavailable()
    if not result.ok:
        return result
    try:
        value = result.value.to_json()
    except Exception:
        return _unavailable()
    return result if _valid_body(value, ref) else _unavailable()


class HostReader:
    """read({ref}, *, purpose) -> C11 Result, dispatched by Ref kind only."""

    def __init__(self, memory, artifacts, verifications):
        owners = {RefKind.RECORD: memory, RefKind.ARTIFACT: artifacts,
                  RefKind.VERIFICATION: verifications}
        if any(not callable(getattr(owner, 'read', None)) for owner in owners.values()):
            raise TypeError('memory, artifacts and verifications owners must provide read')
        self._owners = owners

    def read(self, request, *, purpose):
        if type(purpose) is not str or purpose not in PURPOSES:
            raise ValueError('invalid read purpose')
        try:
            if type(request) is not dict or set(request) != {'ref'}:
                raise ContractError('missing key')
            ref = Ref.from_json(request['ref'])
        except ContractError as error:
            return Result.failure(ErrorCode.INVALID_INPUT, f'invalid request: {error.reason}')
        owner = self._owners.get(ref.kind)
        if owner is None:
            return _unavailable('no current owner for this ref kind')
        wire = ref.to_json()
        try:
            result = owner.read({'ref': dict(wire)}, purpose=purpose)
        except Exception:
            return _unavailable()
        return checked_result(result, wire)
