"""Host-owned canonical store. Executors never receive this object or database path.

Each public mutation opens/closes a transaction. Caller-supplied keys dedupe over
canonical sorted JSON of the operation's explicitly constructed semantic fields.
Wall time and generated IDs are excluded. No transaction spans model execution.
"""
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from .sanitize import sanitize


class Conflict(ValueError):
    pass


class InvalidTransition(ValueError):
    pass


class StaleResult(ValueError):
    pass


class EvidenceRejected(ValueError):
    pass


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def uid():
    return uuid.uuid4().hex


_SCHEMA = '''
CREATE TABLE IF NOT EXISTS records (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, role TEXT NOT NULL,
 content TEXT NOT NULL, usable INTEGER NOT NULL DEFAULT 1,
 source_event_id TEXT UNIQUE, manifest TEXT NOT NULL DEFAULT '[]', supersedes TEXT REFERENCES records(id));
CREATE TABLE IF NOT EXISTS notes (
 id TEXT PRIMARY KEY, content TEXT NOT NULL, sources TEXT NOT NULL, usable INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS goals (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('queued','running','waiting_input','paused','completed','cancelled','failed','unknown')),
 revision INTEGER NOT NULL, acceptance_id TEXT NOT NULL, epoch INTEGER NOT NULL DEFAULT 0,
 budget INTEGER NOT NULL DEFAULT 3, total_claims INTEGER NOT NULL DEFAULT 0,
 reason TEXT NOT NULL DEFAULT '', question_id TEXT, ambiguity INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS acceptances (
 id TEXT PRIMARY KEY, goal_id TEXT NOT NULL REFERENCES goals(id), criteria TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS revisions (
 goal_id TEXT NOT NULL REFERENCES goals(id), revision INTEGER NOT NULL,
 acceptance_id TEXT NOT NULL REFERENCES acceptances(id), specification TEXT NOT NULL,
 sources TEXT NOT NULL, criteria TEXT NOT NULL, PRIMARY KEY(goal_id,revision));
CREATE TRIGGER IF NOT EXISTS revisions_no_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'immutable revision'); END;
CREATE TRIGGER IF NOT EXISTS revisions_no_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'immutable revision'); END;
CREATE TRIGGER IF NOT EXISTS acceptance_no_update BEFORE UPDATE ON acceptances BEGIN SELECT RAISE(ABORT,'immutable acceptance'); END;
CREATE TRIGGER IF NOT EXISTS acceptance_no_delete BEFORE DELETE ON acceptances BEGIN SELECT RAISE(ABORT,'immutable acceptance'); END;
CREATE TABLE IF NOT EXISTS attempts (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, goal_id TEXT NOT NULL REFERENCES goals(id),
 revision INTEGER NOT NULL, acceptance_id TEXT NOT NULL REFERENCES acceptances(id), epoch INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('running','pass','fail','unverified','error','fenced','abandoned','waiting')),
 manifest TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', external_intent INTEGER NOT NULL DEFAULT 0);
CREATE UNIQUE INDEX IF NOT EXISTS single_running_slot ON attempts((1)) WHERE status='running';
CREATE TABLE IF NOT EXISTS artifacts (
 id TEXT PRIMARY KEY, body BLOB NOT NULL, hash TEXT NOT NULL, size INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS receipts (
 id TEXT PRIMARY KEY, attempt_id TEXT UNIQUE NOT NULL REFERENCES attempts(id), artifact_id TEXT NOT NULL REFERENCES artifacts(id),
 hash TEXT NOT NULL, size INTEGER NOT NULL, revision INTEGER NOT NULL, epoch INTEGER NOT NULL);
CREATE TRIGGER IF NOT EXISTS artifact_no_update BEFORE UPDATE ON artifacts BEGIN SELECT RAISE(ABORT,'immutable artifact'); END;
CREATE TRIGGER IF NOT EXISTS artifact_no_delete BEFORE DELETE ON artifacts BEGIN SELECT RAISE(ABORT,'immutable artifact'); END;
CREATE TRIGGER IF NOT EXISTS receipt_no_update BEFORE UPDATE ON receipts BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
CREATE TRIGGER IF NOT EXISTS receipt_no_delete BEFORE DELETE ON receipts BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
CREATE TABLE IF NOT EXISTS outcomes (
 attempt_id TEXT PRIMARY KEY REFERENCES attempts(id), receipt_id TEXT REFERENCES receipts(id),
 check_status TEXT NOT NULL, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, goal_id TEXT REFERENCES goals(id),
 kind TEXT NOT NULL, payload TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS dedupe (
 key TEXT PRIMARY KEY, kind TEXT NOT NULL, hash TEXT NOT NULL, result TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rejections (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id TEXT NOT NULL, reason TEXT NOT NULL,
 UNIQUE(attempt_id,reason));
CREATE TABLE IF NOT EXISTS approvals (
 id TEXT PRIMARY KEY, goal_id TEXT NOT NULL REFERENCES goals(id), revision INTEGER NOT NULL,
 fingerprint TEXT NOT NULL, valid INTEGER NOT NULL DEFAULT 1, consumed INTEGER NOT NULL DEFAULT 0);
'''


_SELECTION_SCHEMA = '''
CREATE TABLE IF NOT EXISTS control_selections (
 selection_id TEXT PRIMARY KEY,
 source_record_id TEXT NOT NULL REFERENCES records(id),
 source_key TEXT NOT NULL,
 action TEXT NOT NULL CHECK(action IN ('cancel','correct')),
 proposal TEXT NOT NULL,
 consumed_by TEXT);
'''


def schema_statements(script):
    """Split complete SQL statements without executescript's implicit commit."""
    pending = ''
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            yield pending
            pending = ''
    if pending.strip():
        raise RuntimeError('incomplete canonical schema statement')


class Store:
    SCHEMA_VERSION = 2
    MAX_TOTAL_CLAIMS = 9

    def __init__(self, path, fault=None):
        self.path = str(Path(path))
        self.fault = fault or (lambda point: None)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, self.SCHEMA_VERSION):
                raise RuntimeError('unsupported canonical schema version')
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('BEGIN IMMEDIATE')
            try:
                # Recheck after acquiring the writer lock: another initializer
                # may have upgraded the database while this connection waited.
                version = db.execute('PRAGMA user_version').fetchone()[0]
                if version not in (0, 1, self.SCHEMA_VERSION):
                    raise RuntimeError('unsupported canonical schema version')
                if version < self.SCHEMA_VERSION:
                    for statement in schema_statements(_SCHEMA + _SELECTION_SCHEMA):
                        db.execute(statement)
                    db.execute('PRAGMA user_version=2')
                    self.fault('schema.before_commit')
                    db.commit()
                    self.fault('schema.after_commit')
                else:
                    db.commit()
            except BaseException:
                if db.in_transaction:
                    db.rollback()
                raise

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=5000')
        db.execute('PRAGMA synchronous=FULL')
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def _tx(self, operation):
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                self.fault(operation + '.before_commit')
                db.commit()
                self.fault(operation + '.after_commit')
            except BaseException:
                if db.in_transaction:
                    db.rollback()
                raise

    def _dedupe(self, db, key, kind, payload):
        if not isinstance(key, str) or not key or len(key) > 200:
            raise ValueError('invalid idempotency key')
        if sanitize(key) != key:
            raise ValueError('idempotency key contains secret-like content')
        digest = hashlib.sha256(encode(sanitize(payload)).encode()).hexdigest()
        old = db.execute('SELECT * FROM dedupe WHERE key=?', (key,)).fetchone()
        if old:
            if old['kind'] != kind or old['hash'] != digest:
                raise Conflict('idempotency key payload conflict')
            return digest, json.loads(old['result'])
        return digest, None

    def _remember(self, db, key, kind, digest, result):
        db.execute('INSERT INTO dedupe VALUES (?,?,?,?)', (key, kind, digest, encode(result)))
        return result

    def _event(self, db, goal_id, kind, payload):
        db.execute('INSERT INTO events(id,goal_id,kind,payload) VALUES (?,?,?,?)',
                   (uid(), goal_id, kind, encode(sanitize(payload))))

    def _goal(self, db, goal_id):
        row = db.execute('SELECT * FROM goals WHERE id=?', (goal_id,)).fetchone()
        if row is None:
            raise InvalidTransition('unknown Goal')
        return dict(row)

    def get_goal(self, goal_id):
        with self._connection() as db:
            return self._goal(db, goal_id)

    def _usable(self, db, manifest):
        for source in manifest:
            table = 'notes' if source.startswith('note:') else 'records'
            identity = source[5:] if table == 'notes' else source
            row = db.execute('SELECT usable FROM ' + table + ' WHERE id=?', (identity,)).fetchone()
            if not row or not row['usable']:
                return False
            if table == 'notes':
                note = db.execute('SELECT sources FROM notes WHERE id=?', (identity,)).fetchone()
                if not self._usable(db, json.loads(note['sources'])):
                    return False
            else:
                record = db.execute('SELECT manifest FROM records WHERE id=?', (identity,)).fetchone()
                if not self._usable(db, json.loads(record['manifest'])):
                    return False
        return True

    def record(self, key, role, content, manifest=(), supersedes=None):
        if role not in ('user', 'assistant'):
            raise ValueError('invalid role')
        content = sanitize(content)
        with self._tx('record') as db:
            digest, old = self._dedupe(db, key, 'record', [role, content, list(manifest), supersedes])
            if old is not None:
                return old
            if not self._usable(db, manifest):
                raise StaleResult('reference stopped before reply publication')
            identity = uid()
            if supersedes:
                db.execute('UPDATE records SET usable=0 WHERE id=?', (supersedes,))
                self._disable_notes(db, supersedes)
                self._invalidate_source(db, supersedes)
            db.execute('INSERT INTO records(id,role,content,manifest,supersedes) VALUES (?,?,?,?,?)',
                       (identity, role, content, encode(list(manifest)), supersedes))
            return self._remember(db, key, 'record', digest, {'id': identity, 'role': role, 'content': content})

    def note(self, key, content, sources):
        if not sources:
            raise ValueError('derived memory requires source records')
        with self._tx('note') as db:
            digest, old = self._dedupe(db, key, 'note', [content, sources])
            if old is not None:
                return old
            if not self._usable(db, sources) or any(s.startswith('note:') for s in sources):
                raise StaleResult('unavailable note source')
            identity = uid()
            db.execute('INSERT INTO notes(id,content,sources) VALUES (?,?,?)', (identity, sanitize(content), encode(sources)))
            return self._remember(db, key, 'note', digest, {'id': identity})

    def context(self):
        with self._connection() as db:
            records = [dict(r) for r in db.execute('SELECT * FROM records WHERE usable=1 AND source_event_id IS NULL ORDER BY seq') if self._usable(db, [r['id']])]
            notes = [dict(r) for r in db.execute('SELECT * FROM notes WHERE usable=1') if self._usable(db, json.loads(r['sources']))]
            # Re-read source rows for selected notes; summaries never replace negation/conditions.
            selected = records[-30:]
            selected_ids = {r['id'] for r in selected}
            for note in notes[:20]:
                for source in json.loads(note['sources']):
                    if source not in selected_ids:
                        row = db.execute('SELECT * FROM records WHERE id=?', (source,)).fetchone()
                        if row is not None and row['source_event_id'] is None:
                            selected.append(dict(row))
                            selected_ids.add(source)
            selected.sort(key=lambda r: r['seq'])
            # Audit/outbox reports are inspectable, not conversational memory.
            return {'records': selected, 'notes': notes[:20], 'manifest': [r['id'] for r in selected] + ['note:' + n['id'] for n in notes[:20]]}

    def _criteria(self, criteria):
        if not isinstance(criteria, dict) or set(criteria) != {'kind', 'max_bytes'}:
            raise ValueError('unsupported acceptance contract')
        if criteria['kind'] != 'local_draft' or type(criteria['max_bytes']) is not int or not 1 <= criteria['max_bytes'] <= 65536:
            raise ValueError('unsupported draft bounds')
        return criteria

    def create_goal(self, key, specification, criteria, sources=()):
        with self._tx('create') as db:
            return self._create_goal(db, key, specification, criteria, sources)

    def _create_goal(self, db, key, specification, criteria, sources=()):
        criteria = self._criteria(criteria)
        specification = sanitize(specification)
        digest, old = self._dedupe(db, key, 'goal', [specification, criteria, list(sources)])
        if old is not None:
            return old
        if not self._usable(db, sources):
            raise StaleResult('Goal cites unavailable source')
        identity, acceptance = uid(), uid()
        db.execute('INSERT INTO goals(id,state,revision,acceptance_id) VALUES (?,\'queued\',1,?)', (identity, acceptance))
        db.execute('INSERT INTO acceptances VALUES (?,?,?)', (acceptance, identity, encode(criteria)))
        db.execute('INSERT INTO revisions VALUES (?,1,?,?,?,?)', (identity, acceptance, specification, encode(list(sources)), encode(criteria)))
        self.fault('create.mid_transaction')
        self._event(db, identity, 'goal.queued', {'revision': 1})
        return self._remember(db, key, 'goal', digest, self._goal(db, identity))


    def claim(self, manifest=()):
        with self._tx('claim') as db:
            if db.execute("SELECT 1 FROM attempts WHERE status='running'").fetchone():
                return None
            goal = db.execute("SELECT * FROM goals WHERE state='queued' ORDER BY seq LIMIT 1").fetchone()
            if not goal:
                return None
            goal = dict(goal)
            if goal['budget'] <= 0 or goal['total_claims'] >= self.MAX_TOTAL_CLAIMS:
                self._wait(db, goal['id'], 'retry_budget_exhausted')
                return None
            revision = db.execute('SELECT * FROM revisions WHERE goal_id=? AND revision=?', (goal['id'], goal['revision'])).fetchone()
            sources = list(dict.fromkeys(list(manifest) + json.loads(revision['sources'])))
            if not self._usable(db, sources):
                self._wait(db, goal['id'], 'reference_stopped')
                return None
            identity, epoch = uid(), goal['epoch'] + 1
            db.execute("UPDATE goals SET state='running',epoch=?,budget=budget-1,total_claims=total_claims+1,reason='',question_id=NULL WHERE id=? AND state='queued' AND epoch=?", (epoch, goal['id'], goal['epoch']))
            db.execute("INSERT INTO attempts(id,goal_id,revision,acceptance_id,epoch,status,manifest) VALUES (?,?,?,?,?,'running',?)", (identity, goal['id'], goal['revision'], goal['acceptance_id'], epoch, encode(sources)))
            self.fault('claim.mid_transaction')
            self._event(db, goal['id'], 'attempt.claimed', {'attempt_id': identity, 'epoch': epoch})
            row = dict(db.execute('SELECT * FROM attempts WHERE id=?', (identity,)).fetchone())
            row['specification'] = revision['specification']
            row['criteria'] = json.loads(revision['criteria'])
            return row

    def _active(self, db, attempt_id):
        row = db.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone()
        if not row:
            return None
        goal = self._goal(db, row['goal_id'])
        if row['status'] != 'running' or goal['state'] != 'running' or row['epoch'] != goal['epoch'] or row['revision'] != goal['revision'] or not self._usable(db, json.loads(row['manifest'])):
            return None
        return dict(row)

    def _reject(self, db, attempt_id, reason):
        db.execute('INSERT OR IGNORE INTO rejections(attempt_id,reason) VALUES (?,?)', (attempt_id, reason))

    def _fence(self, db, goal_id):
        db.execute("UPDATE attempts SET status='fenced' WHERE goal_id=? AND status='running'", (goal_id,))
        db.execute('UPDATE approvals SET valid=0 WHERE goal_id=?', (goal_id,))
        db.execute('UPDATE goals SET epoch=epoch+1,question_id=NULL WHERE id=?', (goal_id,))

    def _wait(self, db, goal_id, reason):
        question = uid()
        db.execute("UPDATE goals SET state='waiting_input',reason=?,question_id=? WHERE id=?", (sanitize(reason), question, goal_id))
        self._event(db, goal_id, 'goal.waiting_input', {'reason': reason, 'question_id': question})

    def fail(self, attempt_id, reason, check_status='error'):
        if check_status not in ('error', 'fail', 'unverified'):
            raise ValueError('invalid outcome')
        rejected = False
        with self._tx('fail') as db:
            old = db.execute('SELECT * FROM outcomes WHERE attempt_id=?', (attempt_id,)).fetchone()
            if old:
                if old['check_status'] != check_status or old['detail'] != sanitize(reason):
                    raise Conflict('conflicting Attempt outcome')
                return dict(old)
            attempt = self._active(db, attempt_id)
            if not attempt:
                self._reject(db, attempt_id, 'stale failure')
                rejected = True
            else:
                db.execute('UPDATE attempts SET status=?,error=? WHERE id=? AND status=\'running\'', (check_status, sanitize(reason), attempt_id))
                db.execute('INSERT INTO outcomes VALUES (?,NULL,?,?)', (attempt_id, check_status, sanitize(reason)))
                goal = self._goal(db, attempt['goal_id'])
                # Error/fail do not blindly auto-retry identical failures.
                if check_status == 'unverified':
                    prior = db.execute('SELECT COUNT(*) FROM outcomes o JOIN attempts a ON a.id=o.attempt_id WHERE a.goal_id=? AND a.revision=? AND o.check_status=? AND o.detail=?', (goal['id'], goal['revision'], check_status, sanitize(reason))).fetchone()[0]
                    if prior >= 2:
                        self._wait(db, goal['id'], 'repeated_unverified_requires_diagnosis')
                    elif goal['budget'] > 0 and goal['total_claims'] < self.MAX_TOTAL_CLAIMS:
                        db.execute("UPDATE goals SET state='queued',reason='unverified' WHERE id=?", (goal['id'],))
                    else:
                        self._wait(db, goal['id'], 'unverified')
                elif check_status == 'fail' and goal['budget'] > 0 and goal['total_claims'] < self.MAX_TOTAL_CLAIMS:
                    prior = db.execute('SELECT COUNT(*) FROM outcomes o JOIN attempts a ON a.id=o.attempt_id WHERE a.goal_id=? AND a.revision=? AND o.check_status=? AND o.detail=?', (goal['id'], goal['revision'], check_status, sanitize(reason))).fetchone()[0]
                    if prior >= 2:
                        self._wait(db, goal['id'], 'repeated_failure_requires_diagnosis')
                    else:
                        db.execute("UPDATE goals SET state='queued',reason=? WHERE id=?", (sanitize(reason), goal['id']))
                else:
                    db.execute("UPDATE goals SET state='failed',reason=? WHERE id=?", (sanitize(reason), goal['id']))
                self._event(db, goal['id'], 'attempt.' + check_status, {'attempt_id': attempt_id, 'reason': reason})
        if rejected:
            raise StaleResult('stale Attempt result')
        return {'attempt_id': attempt_id, 'receipt_id': None, 'check_status': check_status, 'detail': sanitize(reason)}

    def waiting(self, attempt_id, reason):
        with self._tx('waiting') as db:
            attempt = self._active(db, attempt_id)
            if not attempt:
                raise StaleResult('stale input request')
            db.execute("UPDATE attempts SET status='waiting' WHERE id=?", (attempt_id,))
            self._wait(db, attempt['goal_id'], reason)
            return self._goal(db, attempt['goal_id'])

    def control(self, key, goal_id, action, text=None, criteria=None, question_id=None, epoch=None):
        with self._tx('control') as db:
            return self._control(db, key, goal_id, action, text, criteria, question_id, epoch)

    def _control(self, db, key, goal_id, action, text=None, criteria=None, question_id=None, epoch=None):
        payload = [goal_id, action, text, criteria, question_id, epoch]
        digest, old = self._dedupe(db, key, 'control', payload)
        if old is not None:
            return old
        goal = self._goal(db, goal_id)
        if action == 'cancel' and goal['state'] not in ('completed', 'cancelled'):
            self._fence(db, goal_id)
            db.execute("UPDATE goals SET state='cancelled',reason='user_cancelled' WHERE id=?", (goal_id,))
        elif action == 'pause' and goal['state'] in ('queued', 'running'):
            self._fence(db, goal_id)
            db.execute("UPDATE goals SET state='paused',reason='user_paused' WHERE id=?", (goal_id,))
        elif action == 'resume' and goal['state'] == 'paused':
            db.execute("UPDATE goals SET state='queued',reason='' WHERE id=?", (goal_id,))
        elif action == 'input' and goal['state'] == 'waiting_input' and goal['question_id'] == question_id and goal['epoch'] == epoch and text:
            if goal['total_claims'] >= self.MAX_TOTAL_CLAIMS:
                raise InvalidTransition('global retry cap reached')
            self._fence(db, goal_id)
            db.execute("UPDATE goals SET state='queued',budget=MAX(budget,1),reason='' WHERE id=?", (goal_id,))
            db.execute("INSERT INTO records(id,role,content) VALUES (?,'user',?)", (uid(), sanitize(text)))
        elif action == 'correct' and goal['state'] not in ('completed', 'cancelled', 'unknown') and text:
            previous = db.execute('SELECT * FROM revisions WHERE goal_id=? AND revision=?', (goal_id, goal['revision'])).fetchone()
            self._fence(db, goal_id)
            acceptance = goal['acceptance_id']
            new_criteria = self._criteria(criteria) if criteria is not None else json.loads(previous['criteria'])
            if encode(new_criteria) != previous['criteria']:
                acceptance = uid()
                db.execute('INSERT INTO acceptances VALUES (?,?,?)', (acceptance, goal_id, encode(new_criteria)))
            revision = goal['revision'] + 1
            db.execute('INSERT INTO revisions VALUES (?,?,?,?,?,?)', (goal_id, revision, acceptance, sanitize(text), '[]', encode(new_criteria)))
            db.execute("UPDATE goals SET state='queued',revision=?,acceptance_id=?,budget=3,reason='' WHERE id=?", (revision, acceptance, goal_id))
        else:
            raise InvalidTransition('invalid control transition or stale input question')
        self.fault('control.mid_transaction')
        self._event(db, goal_id, 'goal.' + action, {'revision': self._goal(db, goal_id)['revision']})
        return self._remember(db, key, 'control', digest, self._goal(db, goal_id))


    def _disable_notes(self, db, source_id):
        for note in db.execute('SELECT * FROM notes WHERE usable=1').fetchall():
            if source_id in json.loads(note['sources']):
                db.execute('UPDATE notes SET usable=0 WHERE id=?', (note['id'],))

    def forget(self, key, source_id):
        with self._tx('forget') as db:
            return self._forget(db, key, source_id)

    def _forget(self, db, key, source_id):
        digest, old = self._dedupe(db, key, 'forget', [source_id])
        if old is not None:
            return old
        if not db.execute('SELECT 1 FROM records WHERE id=?', (source_id,)).fetchone():
            raise ValueError('unknown source')
        db.execute('UPDATE records SET usable=0 WHERE id=?', (source_id,))
        self._disable_notes(db, source_id)
        affected = self._invalidate_source(db, source_id)
        self._event(db, None, 'reference.stopped', {'source_id':source_id})
        return self._remember(db, key, 'forget', digest, {'source_id': source_id, 'affected': affected})


    def _invalidate_source(self, db, source_id):
        affected = []
        for goal in db.execute("SELECT * FROM goals WHERE state NOT IN ('completed','cancelled','failed','unknown')").fetchall():
            revision = db.execute('SELECT * FROM revisions WHERE goal_id=? AND revision=?', (goal['id'], goal['revision'])).fetchone()
            explicit = source_id in json.loads(revision['sources'])
            active = db.execute("SELECT * FROM attempts WHERE goal_id=? AND status='running'", (goal['id'],)).fetchone()
            incidental = active and not self._usable(db, json.loads(active['manifest']))
            if not explicit and not incidental:
                continue
            self._fence(db, goal['id'])
            if explicit:
                self._wait(db, goal['id'], 'reference_stopped')
            else:
                db.execute("UPDATE goals SET state='queued',reason='context_reference_stopped' WHERE id=?", (goal['id'],))
            affected.append(goal['id'])
            self._event(db, goal['id'], 'goal.reference_stopped', {'source_id': source_id})
        return affected

    def recover(self):
        """Call once at supported process startup, with no other worker alive."""
        with self._tx('recover') as db:
            recovered = []
            for attempt in db.execute("SELECT * FROM attempts WHERE status='running'").fetchall():
                goal = self._goal(db, attempt['goal_id'])
                db.execute("UPDATE attempts SET status='abandoned',error='process_restart' WHERE id=?", (attempt['id'],))
                db.execute('UPDATE goals SET epoch=epoch+1 WHERE id=?', (goal['id'],))
                if attempt['external_intent']:
                    db.execute("UPDATE goals SET state='unknown',ambiguity=1,reason='external_effect_ambiguous' WHERE id=?", (goal['id'],))
                elif goal['budget'] > 0 and goal['total_claims'] < self.MAX_TOTAL_CLAIMS:
                    db.execute("UPDATE goals SET state='queued',reason='process_restart' WHERE id=?", (goal['id'],))
                else:
                    self._wait(db, goal['id'], 'retry_budget_exhausted')
                self._event(db, goal['id'], 'attempt.abandoned', {'attempt_id': attempt['id']})
                recovered.append(attempt['id'])
            return recovered

    def deliver(self):
        with self._tx('deliver') as db:
            count = 0
            for event in db.execute('SELECT * FROM events WHERE delivered=0 ORDER BY seq').fetchall():
                message = encode({'event': event['kind'], 'goal_id': event['goal_id'], 'detail': json.loads(event['payload'])})
                db.execute("INSERT OR IGNORE INTO records(id,role,content,source_event_id) VALUES (?,'assistant',?,?)", (uid(), message, event['id']))
                self.fault('deliver.mid_transaction')
                db.execute('UPDATE events SET delivered=1 WHERE id=?', (event['id'],))
                count += 1
            return count

    def inspect(self):
        with self._connection() as db:
            # A coherent read snapshot, no mutation capability exposed to UI.
            db.execute('BEGIN')
            names = ('records', 'notes', 'goals', 'revisions', 'acceptances', 'attempts', 'receipts', 'outcomes', 'events', 'approvals', 'rejections')
            result = {name: [dict(r) for r in db.execute('SELECT * FROM ' + name)] for name in names}
            result['artifacts'] = [dict(r) for r in db.execute('SELECT id,hash,size FROM artifacts')]
            return result

    def write_draft(self, attempt_id, content):
        """Host capability: accept bounded text proposal, mint receipt from actual bytes."""
        error = None
        receipt = None
        with self._tx('artifact') as db:
            attempt = self._active(db, attempt_id)
            if not attempt:
                self._reject(db, attempt_id, 'stale artifact')
                error = StaleResult('stale artifact proposal')
            else:
                criteria = json.loads(db.execute('SELECT criteria FROM acceptances WHERE id=?', (attempt['acceptance_id'],)).fetchone()['criteria'])
                cap = criteria['max_bytes']
                if not isinstance(content, str) or not content.strip() or len(content) > cap:
                    error = EvidenceRejected('invalid draft type, empty draft, or size bound')
                elif '\x00' in content or content.startswith('\ufeff'):
                    error = EvidenceRejected('draft contains forbidden NUL or BOM')
                else:
                    try:
                        body = sanitize(content).encode('utf-8', errors='strict')
                    except UnicodeError:
                        error = EvidenceRejected('invalid UTF-8 draft')
                    if error is None and len(body) > cap:
                        error = EvidenceRejected('draft exceeds byte bound')
                if error:
                    self._reject(db, attempt_id, str(error))
                else:
                    digest = hashlib.sha256(body).hexdigest()
                    old = db.execute('SELECT * FROM receipts WHERE attempt_id=?', (attempt_id,)).fetchone()
                    if old:
                        if old['hash'] != digest:
                            raise Conflict('conflicting artifact for Attempt')
                        receipt = dict(old)
                    else:
                        artifact_id, receipt_id = uid(), uid()
                        db.execute('INSERT INTO artifacts VALUES (?,?,?,?)', (artifact_id, body, digest, len(body)))
                        self.fault('artifact.mid_transaction')
                        db.execute('INSERT INTO receipts VALUES (?,?,?,?,?,?,?)', (receipt_id, attempt_id, artifact_id, digest, len(body), attempt['revision'], attempt['epoch']))
                        receipt = dict(db.execute('SELECT * FROM receipts WHERE id=?', (receipt_id,)).fetchone())
        if error:
            raise error
        return receipt

    def complete(self, attempt_id, receipt_id):
        error = None
        result = None
        with self._tx('complete') as db:
            old = db.execute('SELECT * FROM outcomes WHERE attempt_id=?', (attempt_id,)).fetchone()
            if old:
                if old['receipt_id'] != receipt_id or old['check_status'] != 'pass':
                    raise Conflict('conflicting completion')
                return dict(old)
            attempt = self._active(db, attempt_id)
            if not attempt:
                self._reject(db, attempt_id, 'stale completion')
                error = StaleResult('stale Attempt completion')
            else:
                receipt = db.execute('SELECT * FROM receipts WHERE id=? AND attempt_id=?', (receipt_id, attempt_id)).fetchone()
                if receipt is None or receipt['revision'] != attempt['revision'] or receipt['epoch'] != attempt['epoch']:
                    error = EvidenceRejected('missing or mismatched host receipt')
                else:
                    artifact = db.execute('SELECT * FROM artifacts WHERE id=?', (receipt['artifact_id'],)).fetchone()
                    criteria = json.loads(db.execute('SELECT criteria FROM acceptances WHERE id=?', (attempt['acceptance_id'],)).fetchone()['criteria'])
                    body = bytes(artifact['body'])
                    try:
                        text = body.decode('utf-8', errors='strict')
                    except UnicodeError:
                        text = ''
                    if not text.strip() or '\x00' in text or text.startswith('\ufeff') or len(body) > criteria['max_bytes'] or len(body) != receipt['size'] or hashlib.sha256(body).hexdigest() != receipt['hash']:
                        error = EvidenceRejected('host artifact readback mismatch')
                if error:
                    self._reject(db, attempt_id, str(error))
                else:
                    changed = db.execute("UPDATE goals SET state='completed',reason='' WHERE id=? AND state='running' AND revision=? AND epoch=?", (attempt['goal_id'], attempt['revision'], attempt['epoch'])).rowcount
                    if changed != 1:
                        raise StaleResult('completion CAS failed')
                    db.execute("UPDATE attempts SET status='pass' WHERE id=? AND status='running'", (attempt_id,))
                    db.execute("INSERT INTO outcomes VALUES (?,?,'pass','host_utf8_size_hash_readback')", (attempt_id, receipt_id))
                    self.fault('complete.mid_transaction')
                    self._event(db, attempt['goal_id'], 'goal.completed', {'attempt_id': attempt_id, 'receipt_id': receipt_id, 'artifact_id': receipt['artifact_id'], 'check_status': 'pass'})
                    result = dict(db.execute('SELECT * FROM outcomes WHERE attempt_id=?', (attempt_id,)).fetchone())
        if error:
            raise error
        return result

    def artifact(self, artifact_id):
        with self._connection() as db:
            row = db.execute('SELECT body FROM artifacts WHERE id=?', (artifact_id,)).fetchone()
            if not row:
                raise ValueError('unknown artifact')
            return bytes(row['body'])

    def ingress(self, key, content, intent='conversation', goal_id=None, control=None, request=None,
                classification=None, classifier_version=None):
        content = sanitize(content)
        if intent not in ('conversation', 'draft', 'control', 'forget'):
            raise ValueError('unsupported ingress intent')
        if classification is not None and (classification not in ('draft', 'conversation', 'unsupported')
                or intent != ('draft' if classification == 'draft' else 'conversation')
                or not isinstance(classifier_version, str) or not classifier_version):
            raise ValueError('invalid host classification')
        with self._tx('ingress') as db:
            digest, old = self._dedupe(db, key, 'ingress', request if request is not None else [content, intent, goal_id, control])
            if old is not None:
                return old
            record_id = uid()
            db.execute("INSERT INTO records(id,role,content) VALUES (?,'user',?)", (record_id, content))
            self.fault('ingress.mid_transaction')
            goal = None
            if intent == 'draft':
                goal = self._create_goal(db, 'handoff:' + key, content, {'kind': 'local_draft', 'max_bytes': 4096}, [record_id])
            elif intent == 'forget':
                if not isinstance(control,dict) or set(control) != {'source_id'}:
                    raise ValueError('forget requires source ID')
                self._forget(db, 'action:' + key, control['source_id'])
            elif intent == 'control':
                if not goal_id or not isinstance(control, dict):
                    raise ValueError('control requires Goal and action')
                goal = self._control(db, 'action:' + key, goal_id, **control)
            result = {'record_id': record_id, 'goal': goal, 'intent': intent}
            if classification is not None:
                result.update(classification=classification, classifier_version=classifier_version)
            if intent in ('control','forget'):
                result['action']='forget' if intent=='forget' else control['action']
            return self._remember(db, key, 'ingress', digest, result)

    def approve(self, key, goal_id, fingerprint):
        """Called only for explicit user approval, not an Executor capability."""
        with self._tx('approve') as db:
            digest, old = self._dedupe(db, key, 'approve', [goal_id, fingerprint])
            if old is not None:
                return old
            goal = self._goal(db, goal_id)
            if goal['state'] in ('cancelled','completed','unknown'):
                raise InvalidTransition('Goal cannot receive new approval')
            identity = uid()
            db.execute('INSERT INTO approvals(id,goal_id,revision,fingerprint) VALUES (?,?,?,?)', (identity, goal_id, goal['revision'], fingerprint))
            self._event(db, goal_id, 'approval.recorded', {'approval_id': identity, 'revision': goal['revision']})
            return self._remember(db, key, 'approve', digest, {'id':identity,'revision':goal['revision'],'fingerprint':fingerprint})

    def stored_reply(self, client_key):
        with self._connection() as db:
            row = db.execute("SELECT result FROM dedupe WHERE key=? AND kind='record'", ('response:' + client_key,)).fetchone()
            return json.loads(row['result']) if row else None

    def operation(self, key):
        """Read-only fate lookup: resolve a lost ACK without guessing or repeating effects."""
        with self._connection() as db:
            row=db.execute('SELECT kind,result FROM dedupe WHERE key=?',(key,)).fetchone()
            return {'status':'accepted','kind':row['kind'],'result':json.loads(row['result'])} if row else {'status':'absent'}
