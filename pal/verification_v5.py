"""VER01 deterministic saved verification; trusted same-connection collaborators only."""
import sqlite3
import uuid

from pal.contracts_v5 import (CheckKind, Condition, ContractError, Ref, RefKind,
                              Result, WorkRef, dumps, loads)

__all__ = ['VerificationStore']
_MAX_INT = 9223372036854775807
_FIELDS = {'key', 'work_ref', 'artifact_refs'}
_CONTEXT_FIELDS = {'work_ref', 'conditions', 'artifact_refs', 'source_refs'}
_ARTIFACT_FIELDS = {'artifact_ref', 'work_ref', 'step_id', 'hash', 'bytes', 'source_refs'}
_RECORD_FIELDS = {'verification_ref', 'work_ref', 'conditions', 'artifact_refs',
                  'artifacts', 'required_refs', 'source_refs', 'checks', 'receipt'}
_SCHEMA = (
    'CREATE TABLE IF NOT EXISTS v5_ver_body ('
    'id TEXT PRIMARY KEY, input_json TEXT NOT NULL, record_json TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS v5_ver_replay ('
    'key TEXT PRIMARY KEY, input_json TEXT NOT NULL, result_json TEXT NOT NULL,'
    'verification_id TEXT NOT NULL UNIQUE)',
)
_HEX = frozenset('0123456789abcdef')
_GATE_STATES = {'available', 'not_found', 'denied', 'unavailable'}


class _Failure(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _error(code='unavailable'):
    return Result.failure(code, 'verification operation ' + code)


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


def _ref(value, kind):
    ref = Ref.from_json(value)
    if ref.kind is not kind:
        raise ContractError()
    return ref


def _artifact_refs(value):
    if type(value) is not list:
        raise ContractError()
    return [_ref(item, RefKind.ARTIFACT) for item in value]


def _record_refs(value):
    if type(value) is not list:
        raise ContractError()
    refs = [Ref.from_json(item) for item in value]
    if (not refs or len(set(refs)) != len(refs)
            or any(ref.kind is not RefKind.RECORD for ref in refs)):
        raise ContractError()
    return refs


def _conditions(value):
    if type(value) is not list:
        raise ContractError()
    conditions = [Condition.from_json(item) for item in value]
    if not conditions or len({condition.id for condition in conditions}) != len(conditions):
        raise ContractError()
    return conditions


def _hash(value):
    if type(value) is not str or len(value) != 64 or any(ch not in _HEX for ch in value):
        raise ContractError()
    return value


def _bytes(value):
    if type(value) is not int or not 0 <= value <= 1048576:
        raise ContractError()
    return value


def _request(value):
    data = _obj(value, _FIELDS)
    _id(data['key'])
    _work(data['work_ref'])
    _artifact_refs(data['artifact_refs'])
    return data


def _context_data(result):
    data = _obj(result.value.to_json(), _CONTEXT_FIELDS)
    refs = _artifact_refs(data['artifact_refs'])
    if len(set(refs)) != len(refs):
        raise ContractError()
    return (_work(data['work_ref']), _conditions(data['conditions']),
            refs, _record_refs(data['source_refs']))


def _artifact_meta(result, ref):
    data = _obj(result.value.to_json(), _ARTIFACT_FIELDS)
    if _ref(data['artifact_ref'], RefKind.ARTIFACT) != ref:
        raise ContractError()
    work = _work(data['work_ref'])
    _id(data['step_id'])
    _hash(data['hash'])
    _bytes(data['bytes'])
    _record_refs(data['source_refs'])
    return data, work


def _checks(conditions, artifact_refs):
    checks = []
    for condition in conditions:
        if condition.check is CheckKind.ARTIFACT_SAVED:
            if artifact_refs:
                status, reason = 'met', 'ordered artifact set saved and verified'
                evidence = [ref.to_json() for ref in artifact_refs]
            else:
                status, reason, evidence = 'unmet', 'current artifact set is empty', []
        elif condition.check is CheckKind.SEMANTIC:
            status, reason, evidence = 'unknown', 'semantic evaluator unavailable', []
        else:
            status, reason, evidence = 'unknown', 'no fetch evidence owner connected', []
        checks.append({'condition_id': condition.id, 'status': status,
                       'reason': reason, 'evidence_refs': evidence})
    return checks


class VerificationStore:
    def __init__(self, connection, *, context, artifact_inspect, source_gate, id_factory=None):
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError('connection must be sqlite3.Connection')
        if connection.isolation_level is not None or connection.in_transaction:
            raise ValueError('connection must be idle with isolation_level=None')
        if not callable(context) or not callable(artifact_inspect) or not callable(source_gate):
            raise TypeError('trusted collaborators must be callable')
        if id_factory is not None and not callable(id_factory):
            raise TypeError('id_factory must be callable')
        self._conn = connection
        self._context = context
        self._artifact_inspect = artifact_inspect
        self._source_gate = source_gate
        self._id_factory = id_factory or (lambda prefix: prefix + '-' + uuid.uuid4().hex)
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
        self._conn.execute('SAVEPOINT v5_ver_callback')
        try:
            result = call()
            if not self._conn.in_transaction or changes != self._conn.total_changes:
                raise ContractError()
            self._conn.execute('RELEASE v5_ver_callback')
            return result
        except BaseException:
            if self._conn.in_transaction:
                try:
                    self._conn.execute('ROLLBACK TO v5_ver_callback')
                    self._conn.execute('RELEASE v5_ver_callback')
                except sqlite3.Error:
                    # A collaborator may have committed/replaced the transaction;
                    # that cannot be undone by cleanup of our former savepoint.
                    pass
            raise

    def _call(self, callback, request, **kwargs):
        result = self._guard(lambda: callback(self._conn, request, **kwargs))
        if type(result) is not Result:
            raise ContractError()
        return Result.from_json(result.to_json())

    def _gate(self, refs):
        state = self._guard(lambda: self._source_gate(self._conn, tuple(refs)))
        if type(state) is not str or state not in _GATE_STATES:
            raise ContractError()
        return state

    def verify(self, request):
        self._idle()
        try:
            data = _request(request)
            canonical = dumps(data)
        except ContractError:
            return _error('invalid_input')
        try:
            self._conn.execute('BEGIN IMMEDIATE')
            previous = self._conn.execute(
                'SELECT input_json,result_json,verification_id FROM v5_ver_replay WHERE key=?',
                (data['key'],)).fetchone()
            if previous is not None:
                if previous[0] != canonical:
                    self._rollback()
                    return _error('conflict')
                receipt = self._receipt_from_row(previous)
                self._rollback()
                return Result.success(receipt)
            result = self._call(self._context, {'work_ref': data['work_ref']}, purpose='save')
            if not result.ok:
                code = result.error.code.value
                self._rollback()
                return _error(code if code in ('not_found', 'stale', 'denied', 'conflict') else 'unavailable')
            work, conditions, current_refs, required = _context_data(result)
            if work != _work(data['work_ref']):
                self._rollback()
                return _error('stale')
            if [ref.to_json() for ref in current_refs] != data['artifact_refs']:
                self._rollback()
                return _error('conflict')
            metas = []
            for ref in current_refs:
                inspected = self._call(self._artifact_inspect, {'ref': ref.to_json()})
                if not inspected.ok:
                    code = inspected.error.code.value
                    self._rollback()
                    return _error('denied' if code == 'denied' else 'unavailable')
                meta, meta_work = _artifact_meta(inspected, ref)
                if meta_work.goal_id != work.goal_id or meta_work.revision != work.revision:
                    self._rollback()
                    return _error('stale')
                if meta_work.epoch > work.epoch:
                    raise ContractError()
                metas.append(meta)
            sources = list(required)
            for meta in metas:
                for ref in _record_refs(meta['source_refs']):
                    if ref not in sources:
                        sources.append(ref)
            state = self._gate(sources)
            if state != 'available':
                self._rollback()
                return _error('denied' if state == 'denied' else 'unavailable')
            checks = _checks(conditions, current_refs)
            verification_id = _id(self._guard(lambda: self._id_factory('verification')))
            verification_ref = Ref(RefKind.VERIFICATION, verification_id).to_json()
            receipt = {'verification_ref': verification_ref, 'checks': checks}
            record = {'verification_ref': verification_ref, 'work_ref': work.to_json(),
                      'conditions': [c.to_json() for c in conditions],
                      'artifact_refs': [r.to_json() for r in current_refs],
                      'artifacts': metas,
                      'required_refs': [r.to_json() for r in required],
                      'source_refs': [r.to_json() for r in sources],
                      'checks': checks, 'receipt': receipt}
            self._conn.execute('INSERT INTO v5_ver_body (id,input_json,record_json) VALUES (?,?,?)',
                               (verification_id, canonical, dumps(record)))
            self._conn.execute('INSERT INTO v5_ver_replay VALUES (?,?,?,?)',
                               (data['key'], canonical, dumps(receipt), verification_id))
            self._conn.execute('COMMIT')
            return Result.success(receipt)
        except Exception:
            self._rollback()
            return _error()
        except BaseException:
            self._rollback()
            raise

    def _receipt_from_row(self, row):
        input_json, result_json, verification_id = row
        data = _request(loads(input_json))
        if dumps(data) != input_json:
            raise ContractError()
        stored = self._stored(_id(verification_id))
        if stored is None or stored['data'] != data:
            raise ContractError()
        if loads(result_json) != stored['receipt']:
            raise ContractError()
        return stored['receipt']

    def get_by_key(self, request):
        self._idle()
        try:
            key = _id(_obj(request, {'key'})['key'])
        except ContractError:
            return _error('invalid_input')
        try:
            row = self._conn.execute(
                'SELECT input_json,result_json,verification_id FROM v5_ver_replay WHERE key=?',
                (key,)).fetchone()
            if row is None:
                return _error('not_found')
            if loads(row[0])['key'] != key:
                raise ContractError()
            return Result.success(self._receipt_from_row(row))
        except Exception:
            return _error()

    def _stored(self, verification_id):
        row = self._conn.execute(
            'SELECT input_json,record_json FROM v5_ver_body WHERE id=?', (verification_id,)).fetchone()
        if row is None:
            return None
        data = _request(loads(row[0]))
        if dumps(data) != row[0]:
            raise ContractError()
        record = _obj(loads(row[1]), _RECORD_FIELDS)
        verification_ref = _ref(record['verification_ref'], RefKind.VERIFICATION)
        work = _work(record['work_ref'])
        conditions = _conditions(record['conditions'])
        refs = _artifact_refs(record['artifact_refs'])
        if len(set(refs)) != len(refs):
            raise ContractError()
        required = _record_refs(record['required_refs'])
        sources = _record_refs(record['source_refs'])
        if type(record['artifacts']) is not list:
            raise ContractError()
        metas = [_obj(meta, _ARTIFACT_FIELDS) for meta in record['artifacts']]
        if verification_ref.id != verification_id or work != _work(data['work_ref']):
            raise ContractError()
        if [ref.to_json() for ref in refs] != data['artifact_refs'] or len(metas) != len(refs):
            raise ContractError()
        union = list(required)
        for meta, ref in zip(metas, refs):
            if _ref(meta['artifact_ref'], RefKind.ARTIFACT) != ref:
                raise ContractError()
            meta_work = _work(meta['work_ref'])
            if (meta_work.goal_id != work.goal_id or meta_work.revision != work.revision
                    or meta_work.epoch > work.epoch):
                raise ContractError()
            _id(meta['step_id'])
            _hash(meta['hash'])
            _bytes(meta['bytes'])
            for item in _record_refs(meta['source_refs']):
                if item not in union:
                    union.append(item)
        if sources != union:
            raise ContractError()
        checks = _checks(conditions, refs)
        if record['checks'] != checks:
            raise ContractError()
        receipt = {'verification_ref': verification_ref.to_json(), 'checks': checks}
        if record['receipt'] != receipt:
            raise ContractError()
        return {'data': data, 'work': work, 'conditions': conditions, 'refs': refs,
                'metas': metas, 'required': required, 'sources': sources,
                'checks': checks, 'receipt': receipt}

    def _current_status(self, stored):
        """Return 'valid'|'invalidated', or raise _Failure with the error code."""
        try:
            result = self._call(self._context, {'work_ref': stored['data']['work_ref']},
                                purpose='status')
            if not result.ok:
                code = result.error.code.value
                if code == 'stale':
                    return 'invalidated'
                raise _Failure(code if code in ('not_found', 'unavailable') else 'unavailable')
            work, conditions, refs, required = _context_data(result)
        except ContractError:
            raise _Failure('unavailable')
        if work != stored['work'] or conditions != stored['conditions'] or required != stored['required']:
            raise _Failure('unavailable')
        if refs != stored['refs']:
            if len(refs) > len(stored['refs']) and refs[:len(stored['refs'])] == stored['refs']:
                return 'invalidated'
            raise _Failure('unavailable')
        for meta in stored['metas']:
            try:
                inspected = self._call(self._artifact_inspect, {'ref': meta['artifact_ref']})
                if not inspected.ok:
                    code = inspected.error.code.value
                    if code == 'denied':
                        return 'invalidated'
                    raise _Failure('unavailable')
                current, _ = _artifact_meta(
                    inspected, Ref.from_json(meta['artifact_ref']))
                if current != meta:
                    raise ContractError()
            except ContractError:
                raise _Failure('unavailable')
        try:
            state = self._gate(stored['sources'])
        except ContractError:
            raise _Failure('unavailable')
        if state == 'denied':
            return 'invalidated'
        if state != 'available':
            raise _Failure('unavailable')
        return 'valid'

    def _typed_result(self, ref):
        stored = self._stored(ref.id)
        if stored is None:
            raise _Failure('not_found')
        return {'work_ref': stored['work'].to_json(),
                'artifact_refs': [r.to_json() for r in stored['refs']],
                'checks': stored['checks'],
                'source_refs': [r.to_json() for r in stored['sources']],
                'status': self._current_status(stored)}

    def get_verification(self, request):
        self._idle()
        try:
            ref = Ref.from_json(_obj(request, {'verification_ref'})['verification_ref'])
        except ContractError:
            return _error('invalid_input')
        if ref.kind is not RefKind.VERIFICATION:
            return _error('invalid_input')
        try:
            self._conn.execute('BEGIN')
            value = self._typed_result(ref)
            self._rollback()
            return Result.success(value)
        except _Failure as exc:
            self._rollback()
            return _error(exc.code)
        except Exception:
            self._rollback()
            return _error()
        except BaseException:
            self._rollback()
            raise

    def inspect(self, connection, request):
        if connection is not self._conn or not connection.in_transaction or connection.isolation_level is not None:
            raise ValueError('inspect requires the supplied active connection')
        try:
            ref = Ref.from_json(_obj(request, {'verification_ref'})['verification_ref'])
        except ContractError:
            return _error('invalid_input')
        if ref.kind is not RefKind.VERIFICATION:
            return _error('invalid_input')
        try:
            return Result.success(self._typed_result(ref))
        except _Failure as exc:
            return _error(exc.code)
        except Exception:
            return _error()
