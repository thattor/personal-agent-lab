### pal/store.py:232 _dedupe
```python
    def _dedupe(self, db, key, kind, payload):
        self._validate_key(key)
        digest = hashlib.sha256(encode(sanitize(payload)).encode()).hexdigest()
        if db.execute("SELECT 1 FROM primary_turns WHERE client_key=? AND status='pending'", (key,)).fetchone():
            raise Conflict('idempotency key reserved by pending Primary turn')
        old = db.execute('SELECT * FROM dedupe WHERE key=?', (key,)).fetchone()
        if old:
            if old['kind'] != kind or old['hash'] != digest:
                raise Conflict('idempotency key payload conflict')
            return digest, json.loads(old['result'])
        return digest, None
```

### pal/store.py:262 _usable
```python
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
```

### pal/store.py:1092 prepare_primary
```python
    def prepare_primary(self, key, text):
        """Persist a normal user turn before inference; no model/effect in this transaction."""
        self._validate_key(key)
        if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 65536:
            raise ValueError('invalid Primary input')
        content = sanitize(text)
        digest = hashlib.sha256(encode(content).encode()).hexdigest()
        with self._tx('primary_prepare') as db:
            old = db.execute('SELECT * FROM primary_turns WHERE client_key=?', (key,)).fetchone()
            if old:
                if old['request_hash'] != digest:
                    raise Conflict('idempotency key payload conflict')
                return (json.loads(old['outcome']) if old['outcome'] else
                        {'record_id': old['record_id'], 'goal': None, 'intent': 'conversation', 'primary_status': 'pending'})
            _, previous = self._dedupe(db, key, 'primary', content)
            if previous is not None:
                raise Conflict('Primary admission missing')
            record_id = uid()
            db.execute("INSERT INTO records(id,role,content) VALUES (?,'user',?)", (record_id, content))
            context = self._context(db)
            goals = [dict(r) for r in db.execute("SELECT id,state,revision,epoch,question_id FROM goals WHERE state NOT IN ('completed','cancelled','unknown') ORDER BY seq DESC LIMIT 11")]
            overflow = len(goals) > 10
            goals = [] if overflow else goals
            visible_goals, questions = [], []
            recent_work = []
            manifest = list(context['manifest'])
            for goal in goals:
                revision = db.execute('SELECT sources FROM revisions WHERE goal_id=? AND revision=?', (goal['id'], goal['revision'])).fetchone()
                sources = json.loads(revision['sources'])
                if not self._usable(db, sources):
                    continue
                visible_goals.append(goal)
                manifest.extend(sources)
                if goal['state'] == 'waiting_input' and goal['question_id']:
                    question = db.execute("SELECT * FROM questions WHERE id=? AND status='open'", (goal['question_id'],)).fetchone()
                    if question and question['revision'] == goal['revision'] and question['epoch'] == goal['epoch']:
                        issued = db.execute('SELECT manifest FROM attempts WHERE id=?', (question['attempt_id'],)).fetchone()
                        issued_sources = json.loads(issued['manifest'])
                        if self._usable(db, issued_sources):
                            questions.append({field: question[field] for field in ('id','goal_id','revision','epoch','round')})
                            manifest.extend(issued_sources)
            for goal in db.execute('SELECT id,state,revision,epoch FROM goals ORDER BY seq DESC LIMIT 5'):
                revision = db.execute('SELECT sources FROM revisions WHERE goal_id=? AND revision=?', (goal['id'], goal['revision'])).fetchone()
                sources = json.loads(revision['sources'])
                if self._usable(db, sources):
                    recent_work.append(dict(goal))
                    manifest.extend(sources)
            snapshot = {'manifest': list(dict.fromkeys(manifest)), 'goals': visible_goals,
                        'questions': questions, 'goals_overflow': overflow, 'recent_work':recent_work}
            db.execute("INSERT INTO primary_turns VALUES (?,?,?,'pending',?,NULL)",
                       (key, digest, record_id, encode(snapshot)))
            return {'record_id': record_id, 'goal': None, 'intent': 'conversation', 'primary_status': 'pending'}
```

### pal/store.py:1228 _finish_primary_outcome
```python
    def _finish_primary_outcome(self, db, turn, status, goal, reply, manifest, reason=None, kind='none', action=None):
        response_id = uid()
        db.execute("INSERT INTO records(id,role,content,manifest) VALUES (?,'assistant',?,?)",
                   (response_id, sanitize(reply), encode(manifest)))
        intent = {'local_draft':'draft', 'answer':'control', 'control':'control', 'forget':'forget'}.get(kind, 'conversation')
        result = {'record_id':turn['record_id'], 'goal':goal, 'intent':intent,
                  'primary_status':status, 'response_id':response_id}
        if action:
            result['action'] = action
        if reason:
            result['reason'] = reason
        db.execute('UPDATE primary_turns SET status=?,outcome=? WHERE client_key=?', (status, encode(result), turn['client_key']))
        return self._remember(db, turn['client_key'], 'primary', turn['request_hash'], result)
```

### pal/store.py:1286 stored_reply
```python
    def stored_reply(self, client_key):
        with self._connection() as db:
            turn = db.execute('SELECT outcome FROM primary_turns WHERE client_key=?', (client_key,)).fetchone()
            if turn:
                if not turn['outcome']:
                    return None
                outcome = json.loads(turn['outcome'])
                row = db.execute('SELECT id,role,content FROM records WHERE id=?', (outcome['response_id'],)).fetchone()
                if row and self._usable(db, [row['id']]):
                    return dict(row)
                return {'id':outcome['response_id'], 'role':'assistant', 'content':'参照を停止した情報を含むため、この応答は表示できません。 / Reply unavailable after reference stop.'}
            row = db.execute("SELECT result FROM dedupe WHERE key=? AND kind='record'", ('response:' + client_key,)).fetchone()
            if row is None:
                row = db.execute("SELECT result FROM dedupe WHERE key=? AND kind='record'", (reply_key(client_key),)).fetchone()
            return json.loads(row['result']) if row else None
```

### pal/store.py:1302 operation
```python
    def operation(self, key):
        """Read-only fate lookup: resolve a lost ACK without guessing or repeating effects."""
        with self._connection() as db:
            turn = db.execute('SELECT status,record_id FROM primary_turns WHERE client_key=?', (key,)).fetchone()
            if turn and turn['status'] == 'pending':
                return {'status':'pending', 'kind':'primary', 'record_id':turn['record_id']}
            row=db.execute('SELECT kind,result FROM dedupe WHERE key=?',(key,)).fetchone()
            return {'status':'accepted','kind':row['kind'],'result':json.loads(row['result'])} if row else {'status':'absent'}
```

### pal/runtime.py:153 submit
```python
    def submit(self, key, text, goal_id=None, control=None):
        if self._closed.is_set():
            raise RuntimeError('runtime is stopping')
        text = sanitize(text)
        if not isinstance(text, str) or not text.strip() or len(text) > 12000:
            raise ValueError('message exceeds input bound or is empty')
        # Admission and Future publication share a lock; concurrent retries cannot
        # launch duplicate inference. Explicit controls never queue behind a model.
        with self._reply_lock:
            fate = self.store.operation(key) if isinstance(key, str) else {'status':'absent'}
            if fate.get('kind') == 'ingress' and control is None and goal_id is None:
                # Replay the accepted historical request only; do not reclassify
                # it or run a new model against a previously spent client key.
                result = self.store.ingress(key, text, fate['result']['intent'],
                    request={'text':text,'goal_id':None,'control':None})
                response = self._completed_reply(key, result)
            elif control is not None or goal_id is not None:
                if not isinstance(control, dict):
                    raise ValueError('explicit target requires an explicit control')
                intent = 'forget' if set(control) == {'source_id'} and goal_id is None else 'control'
                result = self.store.ingress(key, text, intent, goal_id, control,
                    request={'text':text,'goal_id':goal_id,'control':control})
                response = self._completed_reply(key, result)
                self._wake_after(result)
            else:
                result = self.store.prepare_primary(key, text)
                if result['primary_status'] == 'pending':
                    response = self._responses.get(key)
                    if response is None:
                        response = self._conversation.submit(self._run_primary, key)
                        self._responses[key] = response
                else:
                    response = Future()
                    response.set_result(self.store.stored_reply(key))
            return dict(result, response=response)
```