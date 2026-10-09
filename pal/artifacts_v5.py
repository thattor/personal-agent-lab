"""ART01 immutable local drafts; trusted same-connection collaborators only."""
from datetime import datetime, timezone
import sqlite3
import uuid

from pal.artifact_content_v5 import ArtifactContentError, prepare_content
from pal.artifact_integrity_v5 import check_bytes
from pal.contracts_v5 import ContractError, Ref, RefKind, Result, WorkRef, dumps, loads

__all__ = ['ArtifactStore']
_MAX_INT = 9223372036854775807
_FIELDS = {'key', 'work_ref', 'step_id', 'content', 'media_type', 'source_refs'}
_SCHEMA = (
    'CREATE TABLE IF NOT EXISTS v5_art_body ('
    'id TEXT PRIMARY KEY, step_id TEXT NOT NULL UNIQUE, work_json TEXT NOT NULL,'
    'body BLOB NOT NULL, media_type TEXT NOT NULL, hash TEXT NOT NULL,'
    'byte_count INTEGER NOT NULL, observed_at TEXT NOT NULL, sources_json TEXT NOT NULL, binding_json TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS v5_art_replay ('
    'key TEXT PRIMARY KEY, input_json TEXT NOT NULL, result_json TEXT NOT NULL,'
    'artifact_id TEXT NOT NULL UNIQUE)',
)


def _error(code='unavailable'):
    return Result.failure(code, 'artifact operation ' + code)


def _obj(value, keys):
    value = loads(dumps(value))
    if type(value) is not dict or set(value) != set(keys):
        raise ContractError()
    return value


def _id(value):
    if type(value) is not str or not value:
        raise ContractError()
    dumps(value)
    return value


def _work(value):
    work = WorkRef.from_json(value)
    if work.revision > _MAX_INT or work.epoch > _MAX_INT:
        raise ContractError()
    return work


def _refs(value):
    if type(value) is not list:
        raise ContractError()
    refs = tuple(Ref.from_json(item) for item in value)
    if len(set(refs)) != len(refs):
        raise ContractError()
    return refs


def _records(value):
    refs = _refs(value)
    if not refs or any(ref.kind is not RefKind.RECORD for ref in refs):
        raise ContractError()
    return refs


def _request(value):
    data = _obj(value, _FIELDS)
    _id(data['key'])
    _id(data['step_id'])
    _work(data['work_ref'])
    _refs(data['source_refs'])
    prepared = prepare_content(data['content'], data['media_type'])
    return data, prepared


def _receipt(value):
    value = _obj(value, {'artifact_ref', 'hash', 'bytes'})
    if Ref.from_json(value['artifact_ref']).kind is not RefKind.ARTIFACT:
        raise ContractError()
    # check_bytes validates metadata without hashing a potentially large body.
    checked = check_bytes(b'', value['hash'], value['bytes'])
    if checked.status == 'unknown':
        raise ContractError()
    return value


class ArtifactStore:
    def __init__(self, connection, *, authorize_save, source_gate, id_factory=None, clock=None):
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError('connection must be sqlite3.Connection')
        if connection.isolation_level is not None or connection.in_transaction:
            raise ValueError('connection must be idle with isolation_level=None')
        if not callable(authorize_save) or not callable(source_gate):
            raise TypeError('trusted collaborators must be callable')
        if id_factory is not None and not callable(id_factory):
            raise TypeError('id_factory must be callable')
        if clock is not None and not callable(clock):
            raise TypeError('clock must be callable')
        self._conn = connection
        self._authorize = authorize_save
        self._source_gate = source_gate
        self._id_factory = id_factory or (lambda prefix: prefix + '-' + uuid.uuid4().hex)
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())
        connection.execute('BEGIN IMMEDIATE')
        try:
            for sql in _SCHEMA:
                connection.execute(sql)
            connection.execute('COMMIT')
        except BaseException:
            self._rollback()
            raise

    def _idle(self):
        if self._conn.isolation_level is not None or self._conn.in_transaction:
            raise ValueError('operation requires idle isolation_level=None connection')

    def _rollback(self):
        if self._conn.in_transaction:
            self._conn.rollback()

    def _guard(self, call):
        # A disappeared savepoint detects a commit/replaced transaction; trusted
        # collaborator commits cannot be undone or represented as rolled back.
        changes = self._conn.total_changes
        self._conn.execute('SAVEPOINT v5_art_callback')
        result = call()
        if not self._conn.in_transaction:
            raise ContractError()
        self._conn.execute('RELEASE v5_art_callback')
        if changes != self._conn.total_changes:
            raise ContractError()
        return result

    def _gate(self, refs):
        state = self._guard(lambda: self._source_gate(self._conn, refs))
        if type(state) is not str or state not in {'available', 'not_found', 'denied', 'unavailable'}:
            raise ContractError()
        return state

    def save(self, request):
        self._idle()
        try:
            data, prepared = _request(request)
            canonical = dumps(data)
        except (ContractError, ArtifactContentError):
            return _error('invalid_input')
        try:
            self._conn.execute('BEGIN IMMEDIATE')
            previous = self._conn.execute(
                'SELECT input_json,result_json,artifact_id FROM v5_art_replay WHERE key=?', (data['key'],)).fetchone()
            if previous is not None:
                result = (_error('conflict') if previous[0] != canonical else
                          Result.success(self._saved_receipt(previous)))
                self._rollback()
                return result
            if self._conn.execute('SELECT 1 FROM v5_art_body WHERE step_id=?',
                                  (data['step_id'],)).fetchone() is not None:
                self._rollback()
                return _error('conflict')
            authorized = self._guard(lambda: self._authorize(self._conn, {
                'work_ref': data['work_ref'], 'step_id': data['step_id'],
                'action': {'kind': 'compose', **{k: data[k] for k in
                           ('content', 'media_type', 'source_refs')}}}))
            if type(authorized) is not Result:
                raise ContractError()
            authorized = Result.from_json(authorized.to_json())
            if not authorized.ok:
                self._rollback()
                return _error(authorized.error.code.value)
            provenance = _obj(authorized.value.to_json(), {'source_refs'})['source_refs']
            refs = _records(provenance)
            if not set(_refs(data['source_refs'])) <= set(refs):
                raise ContractError()
            state = self._gate(refs)
            if state != 'available':
                self._rollback()
                return _error(state)
            artifact_id = _id(self._id_factory('artifact'))
            observed = _id(self._clock())
            receipt = {'artifact_ref': Ref('artifact', artifact_id).to_json(),
                       'hash': prepared.sha256, 'bytes': prepared.byte_count}
            self._conn.execute(
                'INSERT INTO v5_art_body '
                '(id,step_id,work_json,body,media_type,hash,byte_count,observed_at,sources_json,binding_json) '
                'VALUES (?,?,?,?,?,?,?,?,?,?)',
                (artifact_id, data['step_id'], dumps(data['work_ref']), prepared.data,
                 prepared.media_type, prepared.sha256, prepared.byte_count, observed, dumps(provenance),
                 dumps({'id': artifact_id, 'step_id': data['step_id'], 'work_ref': data['work_ref'],
                        'media_type': prepared.media_type, 'hash': prepared.sha256,
                        'bytes': prepared.byte_count, 'observed_at': observed, 'source_refs': provenance})))
            self._conn.execute('INSERT INTO v5_art_replay VALUES (?,?,?,?)',
                               (data['key'], canonical, dumps(receipt), artifact_id))
            self._conn.execute('COMMIT')
            return Result.success(receipt)
        except Exception:
            self._rollback()
            return _error()
        except BaseException:
            self._rollback()
            raise

    def _saved_receipt(self, row):
        # A receipt is historical metadata, never a permission to read body bytes.
        data, prepared = _request(loads(row[0]))
        receipt = _receipt(loads(row[1]))
        if (receipt['hash'] != prepared.sha256 or receipt['bytes'] != prepared.byte_count or
                receipt['artifact_ref']['id'] != _id(row[2])):
            raise ContractError()
        return receipt

    def get_by_key(self, request):
        self._idle()
        try:
            key = _id(_obj(request, {'key'})['key'])
        except ContractError:
            return _error('invalid_input')
        try:
            row = self._conn.execute('SELECT input_json,result_json,artifact_id FROM v5_art_replay WHERE key=?',
                                     (key,)).fetchone()
            if row is None:
                return _error('not_found')
            if loads(row[0])['key'] != key:
                raise ContractError()
            return Result.success(self._saved_receipt(row))
        except Exception:
            return _error()

    def _loaded(self, ref):
        row = self._conn.execute(
            'SELECT id,step_id,work_json,body,media_type,hash,byte_count,observed_at,sources_json,binding_json '
            'FROM v5_art_body WHERE id=?', (ref.id,)).fetchone()
        if row is None:
            return _error('not_found'), None
        identity, step, work_json, body, media, digest, count, observed, sources_json, binding_json = row
        _id(identity)
        _id(step)
        _id(observed)
        work = _work(loads(work_json))
        refs = _records(loads(sources_json))
        binding = {'id': identity, 'step_id': step, 'work_ref': work.to_json(),
                   'media_type': media, 'hash': digest, 'bytes': count,
                   'observed_at': observed, 'source_refs': [r.to_json() for r in refs]}
        if dumps(loads(binding_json)) != dumps(binding):
            raise ContractError()
        if check_bytes(body, digest, count).status != 'met':
            raise ContractError()
        prepared = prepare_content(body.decode('utf-8'), media)
        if prepared.data != body:
            raise ContractError()
        matches = self._conn.execute(
            'SELECT input_json,result_json FROM v5_art_replay WHERE artifact_id=?', (ref.id,)).fetchall()
        bindings = []
        for original, result in matches:
            receipt = _receipt(loads(result))
            if receipt['artifact_ref'] == ref.to_json():
                data, expected = _request(loads(original))
                if (data['step_id'] != step or _work(data['work_ref']) != work or
                        expected.data != body or expected.media_type != media or
                        receipt['hash'] != digest or receipt['bytes'] != count or
                        not set(_refs(data['source_refs'])) <= set(refs)):
                    raise ContractError()
                bindings.append(data)
        if len(bindings) != 1 or identity != ref.id:
            raise ContractError()
        info = {'artifact_ref': ref.to_json(), 'work_ref': work.to_json(), 'step_id': step,
                'hash': digest, 'bytes': count, 'source_refs': [r.to_json() for r in refs]}
        return info, (prepared.content, media, observed, refs)

    def inspect(self, connection, request):
        if connection is not self._conn or not connection.in_transaction or connection.isolation_level is not None:
            raise ValueError('inspect requires the supplied active connection')
        try:
            ref = Ref.from_json(_obj(request, {'ref'})['ref'])
        except ContractError:
            return _error('invalid_input')
        if ref.kind is not RefKind.ARTIFACT:
            return _error()
        try:
            info, body = self._loaded(ref)
            if body is None:
                return info
            state = self._gate(body[3])
            return Result.success(info) if state == 'available' else _error(
                'denied' if state == 'denied' else 'unavailable')
        except Exception:
            return _error()

    def read(self, request, *, purpose):
        self._idle()
        if type(purpose) is not str or purpose not in {'model_context', 'verification', 'user_view'}:
            raise ValueError('unsupported artifact read purpose')
        try:
            ref = Ref.from_json(_obj(request, {'ref'})['ref'])
        except ContractError:
            return _error('invalid_input')
        if ref.kind is not RefKind.ARTIFACT:
            return _error()
        try:
            self._conn.execute('BEGIN')
            info, body = self._loaded(ref)
            if body is None:
                result = info
            else:
                content, media, observed, refs = body
                state = self._gate(refs)
                if state == 'available' or (state == 'denied' and purpose == 'user_view'):
                    result = Result.success({'ref': ref.to_json(), 'content': content,
                        'media_type': media, 'hash': info['hash'], 'observed_at': observed,
                        'work_ref': info['work_ref'], 'source_refs': info['source_refs'],
                        'usable': state == 'available'})
                else:
                    result = _error('denied' if state == 'denied' else 'unavailable')
            self._rollback()
            return result
        except Exception:
            self._rollback()
            return _error()
        except BaseException:
            self._rollback()
            raise
