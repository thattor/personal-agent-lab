"""PRI01/1 managed in-process mock turns using public PAL owner calls."""
from functools import wraps
import hashlib
import sqlite3
import uuid

from pal.contracts_v5 import ContractError, DraftBrief, ErrorInfo, Grant, Ref, RefKind, Result, WorkRef, dumps, loads
from pal.mock_host_v5 import MockHostSession
from pal.primary_wire_v5 import PrimaryProposalError, parse_primary_output
from pal.sanitize import sanitize

_PROFILE = 'managed-inprocess-mock/1'
_ACTIVE = ('pending', 'preparing', 'admitted', 'returned', 'applying')
_SYSTEM = ('Return exactly one JSON object {reply,proposal}. Proposal is none; new_work with a '
           'DraftBrief; answer with disclosed work_ref/question_id and current record_ref; control '
           'pause/resume/cancel or change with DraftBrief and current origin_record_ref; or memory '
           'stop_reference of a disclosed record. DraftBrief has purpose,target{repository,issue_numbers,'
           'files},constraints,conditions[{description,check}],context_refs. Check is artifact_saved,'
           'source_fetched or semantic. Select exact supplied identifiers only. No grants, minted IDs, '
           'completion, continue/attach/remember/correct or guessed target. A reply grants no authority.')


class _Refusal(Exception):
    def __init__(self, code):
        self.code = code


class _TransactionFailure(_Refusal):
    def __init__(self):
        super().__init__('unavailable')


def _refuse(code='unavailable'):
    raise _Refusal(code)


def _public(method):
    @wraps(method)
    def checked(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except _Refusal as error:
            return Result.failure(error.code, 'Primary operation refused')
        except Exception:
            return Result.failure('unavailable', 'Primary operation unavailable')
    return checked


def _closed(value, required, optional=()):
    if (type(value) is not dict or set(value) - set(required) - set(optional)
            or set(required) - set(value)):
        _refuse('invalid_input')
    return value


def _text(value, *, identifier=False):
    if type(value) is not str:
        _refuse('invalid_input')
    try:
        value.encode('utf-8', 'strict')
    except UnicodeError:
        _refuse('invalid_input')
    if identifier and not value:
        _refuse('invalid_input')
    return value


def _hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _digest(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        _refuse()
    return value


def _result(result):
    if type(result) is not Result:
        _refuse()
    return Result.from_json(result.to_json())


def _value(result):
    result = _result(result)
    if not result.ok:
        _refuse(result.error.code)
    return result.value.to_json()


def _record(value):
    try:
        ref = Ref.from_json(value)
        if ref.kind is not RefKind.RECORD:
            _refuse('invalid_input')
        return ref
    except ContractError:
        _refuse('invalid_input')


class PrimaryHost:
    def __init__(self, connection, *, guard, memory, tasks, request_scope, invoke,
                 model_id='mock-primary'):
        if (not isinstance(connection, sqlite3.Connection) or connection.isolation_level is not None
                or connection.in_transaction or type(guard) is not MockHostSession
                or type(request_scope) is not Grant or not callable(invoke)
                or type(model_id) is not str or not model_id):
            raise ValueError('invalid Primary host configuration')
        model_id.encode('utf-8', 'strict')
        if (tasks.startup_guard is not guard or getattr(tasks, '_conn', None) is not connection
                or getattr(memory, '_conn', None) is not connection or guard.db_uuid is None):
            raise ValueError('Primary owners must share their registered host connection')
        guard.check_connection(connection)
        self._conn, self._guard, self._memory, self._tasks = connection, guard, memory, tasks
        self._scope, self._invoke, self._model_id = request_scope, invoke, model_id
        with guard.operation():
            self._write(self._initialize)

    def _initialize(self):
        self._conn.execute('CREATE TABLE IF NOT EXISTS v5_pri_session '
                           '(id TEXT PRIMARY KEY,runner TEXT NOT NULL,db_uuid TEXT NOT NULL,profile TEXT NOT NULL)')
        self._conn.execute('CREATE TABLE IF NOT EXISTS v5_pri_turn '
            '(id TEXT PRIMARY KEY,user_session TEXT NOT NULL,client_key TEXT NOT NULL,record_json TEXT NOT NULL,'
            'input_hash TEXT NOT NULL,host_session TEXT NOT NULL,runner TEXT NOT NULL,db_uuid TEXT NOT NULL,'
            'profile TEXT NOT NULL,phase TEXT NOT NULL,nonce TEXT,snapshot_json TEXT,intent_json TEXT,'
            'outcome_json TEXT,event_id TEXT,call_id TEXT,outcome_hash TEXT,call_hash TEXT,'
            'admission_hash TEXT NOT NULL,UNIQUE(user_session,client_key))')
        self._conn.execute('CREATE TABLE IF NOT EXISTS v5_pri_call '
            '(id TEXT PRIMARY KEY,turn_id TEXT NOT NULL UNIQUE,host_session TEXT NOT NULL,runner TEXT NOT NULL,'
            'db_uuid TEXT NOT NULL,profile TEXT NOT NULL,reservation_id TEXT NOT NULL,status TEXT NOT NULL,'
            'model_id TEXT NOT NULL,input_hash TEXT NOT NULL,output_hash TEXT,nonce TEXT NOT NULL,'
            'snapshot_hash TEXT NOT NULL,intent_hash TEXT,turn_hash TEXT NOT NULL)')
        identity = self._guard.session_id
        expected = {'id': identity, 'runner': self._guard.runner_id,
                    'db_uuid': self._guard.db_uuid, 'profile': _PROFILE}
        old = self._one('SELECT * FROM v5_pri_session WHERE id=?', (identity,))
        if old is None:
            self._conn.execute('INSERT INTO v5_pri_session VALUES (?,?,?,?)', tuple(expected.values()))
        elif old != expected:
            _refuse()

    def _one(self, sql, args=()):
        cursor = self._conn.execute(sql, args)
        row = cursor.fetchone()
        return None if row is None else dict(zip((c[0] for c in cursor.description), row))

    def _rows(self, sql, args=()):
        cursor = self._conn.execute(sql, args)
        keys = [c[0] for c in cursor.description]
        return [dict(zip(keys, row)) for row in cursor.fetchall()]

    def _idle(self):
        if self._conn.isolation_level is not None or self._conn.in_transaction:
            _refuse()
        self._guard.check_connection(self._conn)

    def _write(self, operation):
        self._idle()
        self._conn.execute('BEGIN IMMEDIATE')
        self._conn.execute('SAVEPOINT v5_pri_write')
        try:
            value = operation()
            if not self._conn.in_transaction:
                raise _TransactionFailure()
            try:
                self._conn.execute('RELEASE v5_pri_write')
            except sqlite3.Error:
                raise _TransactionFailure() from None
            self._conn.execute('COMMIT')
            return value
        except BaseException:
            if self._conn.in_transaction:
                self._conn.execute('ROLLBACK')
            raise

    def _json(self, value):
        if type(value) is not str:
            _refuse()
        parsed = loads(value)
        if dumps(parsed) != value:
            _refuse()
        return parsed

    def _binding(self, row):
        saved = self._one('SELECT * FROM v5_pri_session WHERE id=?', (row['host_session'],))
        if (saved is None or saved != {'id': row['host_session'], 'runner': row['runner'],
                                      'db_uuid': row['db_uuid'], 'profile': row['profile']}
                or row['db_uuid'] != self._guard.db_uuid or row['profile'] != _PROFILE):
            _refuse()

    def _turn(self, identity):
        row = self._one('SELECT * FROM v5_pri_turn WHERE id=?', (identity,))
        if row is None:
            _refuse('not_found')
        for key in ('id', 'user_session', 'client_key', 'host_session', 'runner', 'db_uuid', 'profile'):
            _text(row[key], identifier=True)
        _digest(row['input_hash'])
        _record(self._json(row['record_json']))
        self._binding(row)
        if _digest(row['admission_hash']) != self._admission_hash(row):
            _refuse()
        if row['phase'] not in (*_ACTIVE, 'terminal'):
            _refuse()
        if row['phase'] != 'pending' and row['nonce'] is None:
            _refuse()
        if row['nonce'] is not None:
            _text(row['nonce'], identifier=True)
        if row['phase'] == 'pending' and (row['nonce'] is not None or row['snapshot_json'] is not None):
            _refuse()
        if (row['phase'] == 'terminal') != (row['outcome_json'] is not None and row['event_id'] is not None):
            _refuse()
        if row['phase'] == 'applying' and (row['intent_json'] is None or row['snapshot_json'] is None):
            _refuse()
        call = self._call(row)
        if row['phase'] in ('pending', 'preparing') and call is not None:
            _refuse()
        if row['phase'] in ('admitted', 'returned', 'applying') and call is None:
            _refuse()
        if row['phase'] == 'returned' and call['status'] != 'returned':
            _refuse()
        if row['phase'] == 'admitted' and call['status'] not in ('admitted', 'raised', 'not_entered'):
            _refuse()
        if row['phase'] != 'terminal' and (row['phase'] == 'applying') != (row['intent_json'] is not None):
            _refuse()
        if row['phase'] == 'applying' and (call['status'] != 'returned' or call['output_hash'] is None):
            _refuse()
        if row['phase'] == 'terminal':
            if call is not None and call['status'] == 'admitted':
                _refuse()
            if _digest(row['outcome_hash']) != _hash(row['outcome_json']):
                _refuse()
            outcome = self._outcome(row)
            if outcome['status'] == 'committed' and (call is None or call['status'] != 'returned'):
                _refuse()
        elif any(row[key] is not None for key in ('outcome_json', 'event_id', 'outcome_hash')):
            _refuse()
        return row

    def _ready(self):
        self._idle()
        if self._guard.phase != 'ready':
            _refuse('conflict')
        if self._one("SELECT id FROM v5_pri_turn WHERE phase!='terminal' AND host_session!=? LIMIT 1",
                     (self._guard.session_id,)):
            _refuse('conflict')

    def _body(self, ref, expected=None, *, purpose='model_context'):
        # Owner reads cooperate under a savepoint; this is not a hostile-code sandbox.
        owned = not self._conn.in_transaction
        if owned:
            self._conn.execute('BEGIN')
        changes = self._conn.total_changes
        self._conn.execute('SAVEPOINT v5_pri_read')
        try:
            result = self._memory.read({'ref': ref.to_json()}, purpose=purpose)
            if not self._conn.in_transaction:
                raise _TransactionFailure()
            if self._conn.total_changes != changes:
                _refuse()
            body = _value(result)
            if (type(body) is not dict or set(body) != {'ref', 'content', 'media_type', 'hash',
                    'observed_at', 'source_refs', 'usable'} or Ref.from_json(body['ref']) != ref
                    or body['media_type'] != 'text/plain' or type(body['usable']) is not bool
                    or body['source_refs'] != []):
                _refuse()
            text = _text(body['content'])
            _text(body['observed_at'], identifier=True)
            digest = _digest(body['hash'])
            if _hash(text) != digest or (expected is not None and expected != digest):
                _refuse()
            if purpose == 'model_context' and not body['usable']:
                _refuse('denied')
            try:
                self._conn.execute('RELEASE v5_pri_read')
            except sqlite3.Error:
                raise _TransactionFailure() from None
            return body
        except BaseException:
            if self._conn.in_transaction:
                try:
                    self._conn.execute('ROLLBACK TO v5_pri_read')
                    self._conn.execute('RELEASE v5_pri_read')
                except sqlite3.Error:
                    pass
            raise
        finally:
            if owned and self._conn.in_transaction:
                self._conn.execute('ROLLBACK')

    @_public
    def submit(self, request):
        data = _closed(request, ('client_key', 'session_id', 'text'))
        key, session, text = (_text(data['client_key'], identifier=True),
                              _text(data['session_id'], identifier=True), _text(data['text']))
        if len(text.encode('utf-8')) > 16384:
            _refuse('limit')
        self._idle()
        with self._guard.operation():
            saved = _value(self._memory.append({'client_key': dumps(['PRI01.append', session, key]),
                                               'session_id': session, 'role': 'user', 'text': text}))
            if type(saved) is not dict or set(saved) != {'record_ref'}:
                _refuse()
            ref = _record(saved['record_ref'])
            # Admission records only MEM's immutable hash, including a stopped history record.
            body = self._body(ref, purpose='user_view')
            def admit():
                old = self._one('SELECT id FROM v5_pri_turn WHERE user_session=? AND client_key=?', (session, key))
                if old is not None:
                    row = self._turn(old['id'])
                    if row['record_json'] != dumps(ref) or row['input_hash'] != body['hash']:
                        _refuse()
                    return {'turn_id': row['id'], 'status': self._status(row)}
                identity = 'turn-' + uuid.uuid4().hex
                admission = dict(zip(('id', 'user_session', 'client_key', 'record_json', 'input_hash',
                                      'host_session', 'runner', 'db_uuid', 'profile'),
                    (identity, session, key, dumps(ref), body['hash'], self._guard.session_id,
                     self._guard.runner_id, self._guard.db_uuid, _PROFILE)))
                self._conn.execute('INSERT INTO v5_pri_turn VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,?)',
                    (*admission.values(), 'pending', self._admission_hash(admission)))
                return {'turn_id': identity, 'status': 'pending'}
            return Result.success(self._write(admit))

    def _status(self, row):
        return self._outcome(row)['status'] if row['phase'] == 'terminal' else 'pending'

    def _metadata(self, row):
        data = self._json(row['snapshot_json'])
        if type(data) is not dict or set(data) != {'fingerprint', 'exposure'}:
            _refuse()
        _digest(data['fingerprint'])
        if type(data['exposure']) is not list:
            _refuse()
        seen = set()
        for item in data['exposure']:
            if type(item) is not dict or set(item) != {'ref', 'hash'}:
                _refuse()
            ref = _record(item['ref'])
            if ref in seen:
                _refuse()
            seen.add(ref); _digest(item['hash'])
        if _record(self._json(row['record_json'])) not in seen:
            _refuse()
        current = next(item for item in data['exposure'] if item['ref'] == self._json(row['record_json']))
        if current['hash'] != row['input_hash']:
            _refuse()
        return data

    def _exposure_check(self, metadata):
        for item in metadata['exposure']:
            self._body(_record(item['ref']), item['hash'])

    def _outcome(self, row):
        outcome = self._json(row['outcome_json'])
        if (type(outcome) is not dict or set(outcome) - {'status', 'effect_refs', 'reply', 'error'}
                or not {'status', 'effect_refs'} <= set(outcome)
                or outcome['status'] not in ('committed', 'failed', 'interrupted')
                or type(outcome['effect_refs']) is not list):
            _refuse()
        for value in outcome['effect_refs']:
            Ref.from_json(value)
        if len({dumps(value) for value in outcome['effect_refs']}) != len(outcome['effect_refs']):
            _refuse()
        if 'error' in outcome:
            error = ErrorInfo.from_json(outcome['error'])
            if error.refs or error.message != ('Reply sources unavailable' if outcome['status'] == 'committed'
                                               else 'Primary turn did not commit'):
                _refuse()
            if outcome['status'] == 'committed' and error.code.value != 'denied':
                _refuse()
        if outcome['status'] != 'committed' and ('reply' in outcome or outcome['effect_refs'] or 'error' not in outcome):
            _refuse()
        if 'reply' in outcome:
            _text(outcome['reply'])
            if sanitize(outcome['reply']) != outcome['reply'] or len(outcome['reply'].encode('utf-8')) > 16384:
                _refuse()
        return outcome

    def _view(self, row):
        if row['phase'] != 'terminal':
            return Result.success({'status': 'pending', 'effect_refs': []})
        outcome = self._outcome(row)
        if 'reply' in outcome:
            metadata = self._metadata(row)
            try:
                self._exposure_check(metadata)
            except _TransactionFailure:
                raise
            except Exception:
                outcome.pop('reply')
                outcome['error'] = {'code': 'denied', 'message': 'Reply sources unavailable', 'refs': []}
        return Result.success(outcome)

    @_public
    def get_turn(self, request):
        identity = _text(_closed(request, ('turn_id',))['turn_id'], identifier=True)
        self._guard.check_connection(self._conn)
        with self._guard.operation():
            return self._read_view(identity)

    def _read_view(self, identity):
        owned = not self._conn.in_transaction
        if owned:
            self._conn.execute('BEGIN')
        self._conn.execute('SAVEPOINT v5_pri_view')
        try:
            result = self._view(self._turn(identity))
            try:
                self._conn.execute('RELEASE v5_pri_view')
            except sqlite3.Error:
                raise _TransactionFailure() from None
            return result
        except BaseException:
            if self._conn.in_transaction:
                try:
                    self._conn.execute('ROLLBACK TO v5_pri_view')
                    self._conn.execute('RELEASE v5_pri_view')
                except sqlite3.Error:
                    pass
            raise
        finally:
            if owned and self._conn.in_transaction:
                self._conn.execute('ROLLBACK')

    def _candidates(self, session, current, allowed):
        value = _value(self._tasks.list_candidates({'session_id': session, 'limit': 10}))
        if type(value) is not dict or set(value) != {'works', 'truncated'} or type(value['truncated']) is not bool:
            _refuse()
        try:
            parse_primary_output('{"reply":"","proposal":{"kind":"none"}}',
                current_record_ref=current, candidates=value['works'], allowed_record_refs=allowed)
        except PrimaryProposalError:
            _refuse()
        return value

    @staticmethod
    def _fingerprint(candidates):
        return _hash(dumps({'works': [[w['work_ref']['goal_id'], w['work_ref']['revision'],
                       [q['id'] for q in w['open_questions']], w['text_withheld']]
                       for w in candidates['works']], 'truncated': candidates['truncated']}))

    def _snapshot(self, row):
        ref = _record(self._json(row['record_json']))
        current = self._body(ref, row['input_hash'])
        recent = _value(self._memory.list_recent({'session_id': row['user_session'], 'limit': 6}))
        if (type(recent) is not dict or set(recent) != {'record_refs', 'truncated'}
                or type(recent['truncated']) is not bool or type(recent['record_refs']) is not list
                or len(recent['record_refs']) > 6):
            _refuse()
        records = [current]; seen = {ref}
        truncated = recent['truncated']
        for value in recent['record_refs']:
            selected = _record(value)
            if selected in seen:
                continue
            seen.add(selected)
            if len(records) == 6:
                truncated = True
                continue
            records.append(self._body(selected))
        candidates = self._candidates(row['user_session'], ref, [ref])
        snapshot = {'record_ref': ref.to_json(), 'session_id': row['user_session'], 'candidates': candidates,
                    'context': {'summaries': [], 'records': records, 'records_truncated': truncated}}
        while len(dumps(snapshot).encode('utf-8')) > 32768:
            if len(records) == 1:
                _refuse('limit')
            records.pop(); snapshot['context']['records_truncated'] = True
        hashes = {Ref.from_json(body['ref']): body['hash'] for body in records}
        exposure = list(hashes)
        for candidate in candidates['works']:
            if not candidate['text_withheld']:
                for value in candidate['dependency_refs']:
                    dependency = _record(value)
                    if dependency not in hashes:
                        hashes[dependency] = self._body(dependency)['hash']; exposure.append(dependency)
        metadata = {'fingerprint': self._fingerprint(candidates),
                    'exposure': [{'ref': source.to_json(), 'hash': hashes[source]} for source in exposure]}
        return snapshot, metadata

    def _snapshot_check(self, row, metadata):
        current = _record(self._json(row['record_json']))
        latest = self._candidates(row['user_session'], current, [current])
        if self._fingerprint(latest) != metadata['fingerprint']:
            _refuse('stale')
        self._exposure_check(metadata)

    def _call(self, row):
        call = self._one('SELECT * FROM v5_pri_call WHERE turn_id=?', (row['id'],))
        if call is None:
            if row['call_id'] is not None or row['call_hash'] is not None:
                _refuse()
            return None
        if (call['id'] != dumps(['PRI01.call', row['id']])
                or call['id'] != row['call_id'] or call['nonce'] != row['nonce']
                or any(call[k] != row[k] for k in ('host_session', 'runner', 'db_uuid', 'profile'))
                or call['status'] not in ('admitted', 'returned', 'raised', 'not_entered', 'interrupted')):
            _refuse()
        for key in ('reservation_id', 'model_id'):
            _text(call[key], identifier=True)
        _digest(call['input_hash'])
        if (_digest(row['call_hash']) != _hash(dumps(call))
                or _digest(call['turn_hash']) != self._turn_hash(row)):
            _refuse()
        if _digest(call['snapshot_hash']) != _hash(row['snapshot_json']):
            _refuse()
        self._metadata(row)
        if (row['intent_json'] is None) != (call['intent_hash'] is None):
            _refuse()
        if row['intent_json'] is not None:
            if _digest(call['intent_hash']) != _hash(row['intent_json']):
                _refuse()
            self._stored_intent(row)
        if call['output_hash'] is not None:
            _digest(call['output_hash'])
        return call

    @staticmethod
    def _admission_hash(row):
        return _hash(dumps({key: row[key] for key in ('id', 'user_session', 'client_key', 'record_json',
                      'input_hash', 'host_session', 'runner', 'db_uuid', 'profile')}))

    @classmethod
    def _turn_hash(cls, row):
        return _hash(dumps({'admission': cls._admission_hash(row), 'nonce': row['nonce']}))

    def _bind_call(self, identity):
        call = self._one('SELECT * FROM v5_pri_call WHERE turn_id=?', (identity,))
        if call is None:
            _refuse()
        self._conn.execute('UPDATE v5_pri_turn SET call_hash=? WHERE id=?', (_hash(dumps(call)), identity))

    def _end(self, row, status, output=None):
        def end():
            call = self._call(self._turn(row['id']))
            if call is None or call['status'] != 'admitted':
                _refuse()
            try:
                output_hash = _hash(output) if type(output) is str else None
            except UnicodeError:
                output_hash = None
            self._conn.execute('UPDATE v5_pri_call SET status=?,output_hash=? WHERE id=?',
                               (status, output_hash, call['id']))
            if status == 'returned':
                self._conn.execute("UPDATE v5_pri_turn SET phase='returned' WHERE id=?", (row['id'],))
            self._bind_call(row['id'])
        self._write(end)

    def _not_entered(self, identity):
        row = self._turn(identity)
        call = self._call(row)
        if call is not None and call['status'] == 'admitted':
            self._end(row, 'not_entered')

    def _intent(self, row, output, metadata):
        proposal = output['proposal']; kind = proposal['kind']
        key = dumps(['PRI01.effect', row['id'], kind])
        ref = self._json(row['record_json'])
        scope = None
        if kind == 'none':
            request = None
        elif kind == 'new_work':
            brief = DraftBrief.from_json(proposal['brief']).to_json()
            brief['context_refs'] = [item['ref'] for item in metadata['exposure']]
            request = {'key': key, 'session_id': row['user_session'], 'origin_record_ref': ref, 'brief': brief}
            scope = self._scope.to_json()
        elif kind in ('answer', 'control'):
            if kind == 'answer':
                command = {'kind': 'answer', 'question_id': proposal['question_id'], 'answer_record_ref': ref}
            else:
                command = loads(dumps(proposal['command']))
                if type(command) is dict:
                    command['brief']['context_refs'] = [item['ref'] for item in metadata['exposure']]
            request = {'key': key, 'work_ref': proposal['work_ref'], 'command': command}
        else:
            request = {'key': key, 'source_ref': proposal['operation']['source_ref']}
        return {'kind': kind, 'request': request, 'request_scope': scope, 'reply': sanitize(output['reply'])}

    def _stored_intent(self, row):
        intent = self._json(row['intent_json'])
        if type(intent) is not dict or set(intent) != {'kind', 'request', 'request_scope', 'reply'}:
            _refuse()
        _text(intent['reply'])
        kind, request = intent['kind'], intent['request']
        if kind not in ('new_work', 'answer', 'control', 'memory') or type(request) is not dict:
            _refuse()
        if request.get('key') != dumps(['PRI01.effect', row['id'], kind]):
            _refuse()
        if kind == 'new_work':
            if (set(request) != {'key', 'session_id', 'origin_record_ref', 'brief'}
                    or request['session_id'] != row['user_session']
                    or request['origin_record_ref'] != self._json(row['record_json'])):
                _refuse()
            DraftBrief.from_json(request['brief']); Grant.from_json(intent['request_scope'])
        elif kind in ('answer', 'control'):
            if set(request) != {'key', 'work_ref', 'command'}:
                _refuse()
            WorkRef.from_json(request['work_ref'])
            command = request['command']
            if kind == 'answer':
                if (type(command) is not dict or set(command) != {'kind', 'question_id', 'answer_record_ref'}
                        or command['kind'] != 'answer' or command['answer_record_ref'] != self._json(row['record_json'])):
                    _refuse()
                _text(command['question_id'], identifier=True)
            elif type(command) is str:
                if command not in ('pause', 'resume', 'cancel'):
                    _refuse()
            elif (type(command) is dict and set(command) == {'kind', 'brief', 'origin_record_ref'}
                  and command['kind'] == 'change' and command['origin_record_ref'] == self._json(row['record_json'])):
                DraftBrief.from_json(command['brief'])
            else:
                _refuse()
        elif set(request) != {'key', 'source_ref'}:
            _refuse()
        else:
            _record(request['source_ref'])
        if kind != 'new_work' and intent['request_scope'] is not None:
            _refuse()
        return intent

    def _dispatch(self, row, intent, *, lookup=False):
        kind, request = intent['kind'], intent['request']
        if lookup:
            method = (self._tasks.get_create_by_key if kind == 'new_work' else
                      self._memory.get_stop_reference_by_key if kind == 'memory' else self._tasks.get_control_by_key)
            return method({'key': request['key']})
        if kind == 'new_work':
            return self._tasks.create(request, request_scope=Grant.from_json(intent['request_scope']))
        if kind == 'memory':
            return self._memory.stop_reference(request, session_id=row['user_session'])
        return self._tasks.control(request)

    def _receipt(self, row, intent, result):
        value = _value(result); kind = intent['kind']
        if kind == 'memory':
            if value != {'affected_refs': [intent['request']['source_ref']]}:
                _refuse()
            return value['affected_refs'], None
        expected = {'work_ref', 'expert_id', 'state', 'grant'} if kind == 'new_work' else {'work_ref', 'state', 'control_status'}
        if type(value) is not dict or set(value) != expected:
            _refuse()
        work = WorkRef.from_json(value['work_ref'])
        if kind == 'new_work':
            if work.revision != 1 or value['state'] != 'queued':
                _refuse()
            Grant.from_json(value['grant']); _text(value['expert_id'], identifier=True)
        else:
            original = WorkRef.from_json(intent['request']['work_ref'])
            command = intent['request']['command']
            revision = original.revision + (type(command) is dict and command.get('kind') == 'change')
            if (work.goal_id != original.goal_id or work.revision != revision
                    or value['control_status'] not in ('none', 'draining', 'pause_requested')
                    or value['state'] not in ('queued', 'running', 'waiting_input', 'paused', 'completed', 'cancelled', 'failed')):
                _refuse()
        refs = [self._json(row['record_json'])] if kind == 'answer' else []
        return refs, '[work {} revision {}: {}]'.format(work.goal_id, work.revision, value['state'])

    def _terminal(self, identity, status, *, reply=None, refs=(), code=None):
        def terminal():
            row = self._turn(identity)
            if row['phase'] == 'terminal':
                return
            call = self._call(row)
            if status == 'interrupted' and call is not None and call['status'] == 'admitted':
                if self._guard.phase != 'startup' or row['host_session'] == self._guard.session_id:
                    _refuse()
                self._conn.execute("UPDATE v5_pri_call SET status='interrupted' WHERE id=?", (call['id'],))
                self._bind_call(identity)
            outcome = {'status': status, 'effect_refs': [Ref.from_json(ref).to_json() for ref in refs]}
            if reply is not None:
                if len(reply.encode('utf-8')) > 16384:
                    _refuse()
                metadata = self._metadata(row)
                try:
                    self._exposure_check(metadata)
                    outcome['reply'] = reply
                except _TransactionFailure:
                    raise
                except Exception:
                    code_out = 'denied'
                    outcome['error'] = {'code': code_out, 'message': 'Reply sources unavailable', 'refs': []}
            if code is not None:
                outcome['error'] = {'code': str(code), 'message': 'Primary turn did not commit', 'refs': []}
            event_refs = list(dict.fromkeys([_record(self._json(row['record_json'])), *(Ref.from_json(r) for r in refs)]))
            event = _value(self._tasks.append_event(self._conn, {'key': dumps(['PRI01.turn', identity]),
                'session_id': row['user_session'], 'kind': 'result' if status == 'committed' else 'error',
                'text': 'Primary turn ' + status, 'refs': [ref.to_json() for ref in event_refs]}))
            if type(event) is not dict or set(event) != {'event_id'}:
                _refuse()
            _text(event['event_id'], identifier=True)
            if row['nonce'] is None:
                self._conn.execute('UPDATE v5_pri_turn SET nonce=? WHERE id=?', (uuid.uuid4().hex, identity))
            self._conn.execute("UPDATE v5_pri_turn SET phase='terminal',outcome_json=?,event_id=?,outcome_hash=? WHERE id=?",
                               (dumps(outcome), event['event_id'], _hash(dumps(outcome)), identity))
        self._write(terminal)

    def _finish(self, identity, status, **kwargs):
        try:
            self._terminal(identity, status, **kwargs)
        except Exception:
            pass
        return self._read_view(identity)

    @_public
    def run_turn(self, request):
        identity = _text(_closed(request, ('turn_id',))['turn_id'], identifier=True)
        self._ready()
        row = self._turn(identity)
        if row['phase'] != 'pending':
            return self._read_view(identity)
        with self._guard.activity():
            nonce = uuid.uuid4().hex
            def claim():
                count = self._conn.execute("UPDATE v5_pri_turn SET phase='preparing',nonce=? WHERE id=? AND phase='pending'",
                                           (nonce, identity)).rowcount
                return count == 1
            if not self._write(claim):
                return self._read_view(identity)
            row = self._turn(identity)
            try:
                snapshot, metadata = self._snapshot(row)
                self._snapshot_check(row, metadata)
                self._write(lambda: self._conn.execute('UPDATE v5_pri_turn SET snapshot_json=? WHERE id=?', (dumps(metadata), identity)))
                reservation = _value(self._tasks.reserve_budget({'key': dumps(['PRI01.reserve', identity]), 'kind': 'model', 'role': 'primary'}))
                if (type(reservation) is not dict or set(reservation) != {'reservation_id', 'remaining'}
                        or type(reservation['remaining']) is not dict or set(reservation['remaining']) != {'host'}
                        or type(reservation['remaining']['host']) is not int or reservation['remaining']['host'] < 0):
                    _refuse()
                reservation_id = _text(reservation['reservation_id'], identifier=True)
                call_id = dumps(['PRI01.call', identity])
                _value(self._tasks.consume({'reservation_id': reservation_id, 'call_or_operation_id': call_id}))
                call_request = {'call_id': call_id, 'reservation_id': reservation_id, 'role': 'primary',
                    'messages': [{'role': 'system', 'text': _SYSTEM}, {'role': 'user', 'text': dumps(snapshot)}],
                    'source_refs': [item['ref'] for item in metadata['exposure']], 'output_kind': 'primary_proposal'}
                self._snapshot_check(row, metadata)
                def admit():
                    self._exposure_check(metadata)
                    self._conn.execute('INSERT INTO v5_pri_call VALUES (?,?,?,?,?,?,?,?,?,?,NULL,?,?,NULL,?)',
                        (call_id, identity, row['host_session'], row['runner'], row['db_uuid'], row['profile'],
                         reservation_id, 'admitted', self._model_id, _hash(dumps(call_request)), nonce,
                         _hash(dumps(metadata)), self._turn_hash(row)))
                    self._conn.execute("UPDATE v5_pri_turn SET phase='admitted',call_id=? WHERE id=? AND nonce=?", (call_id, identity, nonce))
                    self._bind_call(identity)
                self._write(admit)
                self._exposure_check(metadata)
            except _Refusal as error:
                try:
                    self._not_entered(identity)
                except Exception:
                    pass
                return self._finish(identity, 'failed', code=error.code)
            except Exception:
                try:
                    self._not_entered(identity)
                except Exception:
                    pass
                return self._finish(identity, 'failed', code='unavailable')
            try:
                raw = self._invoke(call_request)
            except BaseException as error:
                try:
                    self._end(row, 'raised')
                except Exception:
                    pass
                if not isinstance(error, Exception):
                    raise
                return self._finish(identity, 'failed', code='unavailable')
            self._end(row, 'returned', raw)
            try:
                output = parse_primary_output(raw, current_record_ref=_record(snapshot['record_ref']),
                    candidates=snapshot['candidates']['works'],
                    allowed_record_refs=[_record(body['ref']) for body in snapshot['context']['records']])
                self._snapshot_check(row, metadata)
                intent = self._intent(row, output, metadata)
                if intent['kind'] == 'none':
                    return self._finish(identity, 'committed', reply=intent['reply'])
                self._snapshot_check(row, metadata)
                def save_intent():
                    self._conn.execute("UPDATE v5_pri_turn SET phase='applying',intent_json=? WHERE id=?", (dumps(intent), identity))
                    self._conn.execute('UPDATE v5_pri_call SET intent_hash=? WHERE id=?', (_hash(dumps(intent)), call_id))
                    self._bind_call(identity)
                self._write(save_intent)
            except (PrimaryProposalError, _Refusal) as error:
                return self._finish(identity, 'failed', code=error.code)
            except Exception:
                return self._finish(identity, 'failed', code='unavailable')
            try:
                owner = _result(self._dispatch(row, intent))
                if not owner.ok:
                    if owner.error.code.value == 'unavailable':
                        return self._read_view(identity)
                    return self._finish(identity, 'failed', code=owner.error.code)
                refs, acknowledgement = self._receipt(row, intent, owner)
            except Exception:
                return self._read_view(identity)
            reply = intent['reply'] + ('\n' + acknowledgement if acknowledgement else '')
            return self._finish(identity, 'committed', reply=reply, refs=refs)

    @_public
    def control(self, request):
        data = _closed(request, ('client_key', 'session_id', 'work_ref', 'command'))
        key, session = _text(data['client_key'], identifier=True), _text(data['session_id'], identifier=True)
        try:
            work = WorkRef.from_json(data['work_ref'])
        except ContractError:
            _refuse('invalid_input')
        if type(data['command']) is not str or data['command'] not in ('pause', 'resume', 'cancel'):
            _refuse('invalid_input')
        self._idle()
        with self._guard.operation():
            result = _result(self._tasks.control({'key': dumps(['PRI01.control', session, key]),
                                                  'work_ref': work.to_json(), 'command': data['command']}))
            return result if result.ok else Result.failure(result.error.code, 'Structured control refused')

    @_public
    def stop_reference(self, request):
        data = _closed(request, ('client_key', 'session_id', 'source_ref'))
        key, session = _text(data['client_key'], identifier=True), _text(data['session_id'], identifier=True)
        ref = _record(data['source_ref'])
        self._idle()
        with self._guard.operation():
            result = _result(self._memory.stop_reference({'key': dumps(['PRI01.stop', session, key]),
                                                          'source_ref': ref.to_json()}, session_id=session))
            return result if result.ok else Result.failure(result.error.code, 'Structured stop refused')

    @_public
    def recover_turns(self):
        self._idle()
        if self._guard.phase != 'startup':
            _refuse('conflict')
        outcome = {'interrupted_turn_ids': [], 'committed_turn_ids': [], 'held_turn_ids': []}
        with self._guard.operation():
            rows = self._rows("SELECT id FROM v5_pri_turn WHERE phase!='terminal' AND host_session!=? ORDER BY rowid",
                              (self._guard.session_id,))
            for candidate in rows:
                identity = _text(candidate['id'], identifier=True)
                try:
                    row = self._turn(identity)
                    call = self._call(row)
                    if row['phase'] == 'applying':
                        if call is None or call['status'] != 'returned':
                            _refuse()
                        intent = self._stored_intent(row)
                        result = _result(self._dispatch(row, intent, lookup=True))
                        if not result.ok and result.error.code.value != 'not_found':
                            _refuse()
                        if result.ok:
                            refs, acknowledgement = self._receipt(row, intent, result)
                            reply = intent['reply'] + ('\n' + acknowledgement if acknowledgement else '')
                            self._terminal(identity, 'committed', reply=reply, refs=refs)
                            outcome['committed_turn_ids'].append(identity)
                            continue
                    self._terminal(identity, 'interrupted', code='unavailable')
                    outcome['interrupted_turn_ids'].append(identity)
                except Exception:
                    outcome['held_turn_ids'].append(identity)
        return Result.success(outcome)
