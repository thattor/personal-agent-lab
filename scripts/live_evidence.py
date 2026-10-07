"""Bounded test-run evidence and wall watchdog; never human attestation."""
import hashlib
import json
import math
import os
import stat
import threading
import time
from pathlib import Path

from pal.sanitize import sanitize

_SCOPES = {'scripted', 'live_synthetic'}
_RESERVED = {'sequence','scope','previous_sha256','sha256','recorded_at'}
_MAX_RECORD = 262144
_MAX_JOURNAL = 16 * 1024 * 1024
_GENESIS = '0' * 64


def _encode(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),
                      allow_nan=False).encode('utf-8',errors='strict')


class EvidenceJournal:
    def __init__(self, path, scope):
        if scope not in _SCOPES:
            raise ValueError('test journal cannot attest human participation')
        self.path = Path(path)
        directory = os.open(str(self.path.parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        self._fd = -1
        try:
            self._fd = os.open(self.path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,
                               0o600,dir_fd=directory)
            os.fsync(self._fd)
            os.fsync(directory)
        except BaseException:
            if self._fd != -1: os.close(self._fd)
            raise
        finally:
            os.close(directory)
        self.scope = scope
        self._lock = threading.Lock()
        self._sequence = 0
        self._hash = _GENESIS
        self._bytes = 0
        self._broken = False

    def append(self, event):
        if type(event) is not dict or any(type(key) is not str for key in event):
            raise ValueError('journal event must have string keys')
        if _RESERVED & set(event) or not isinstance(event.get('event'),str) or not event['event']:
            raise ValueError('reserved metadata or missing event')
        with self._lock:
            if self._fd == -1 or self._broken:
                raise ValueError('journal closed or failed')
            record = dict(sanitize(event),sequence=self._sequence+1,scope=self.scope,
                          previous_sha256=self._hash,recorded_at=time.time())
            digest = hashlib.sha256(_encode(record)).hexdigest()
            record['sha256'] = digest
            raw = _encode(record)+b'\n'
            if len(raw) > _MAX_RECORD or self._bytes+len(raw) > _MAX_JOURNAL:
                raise ValueError('journal evidence size bound')
            try:
                view = memoryview(raw)
                while view:
                    written = os.write(self._fd,view)
                    if written <= 0: raise OSError('journal write made no progress')
                    view = view[written:]
                os.fsync(self._fd)
            except BaseException:
                self._broken = True  # Preserve partial evidence, never repair it.
                raise
            self._sequence += 1
            self._hash = digest
            self._bytes += len(raw)
            return digest

    def close(self):
        with self._lock:
            if self._fd != -1:
                os.close(self._fd)
                self._fd = -1

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def verify_journal(path):
    """Read-only chain audit. A valid prefix does not prove a run completed."""
    def pairs(items):
        result = {}
        for key,value in items:
            if key in result: raise ValueError('duplicate journal key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('nonfinite journal value')
    fd = os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_JOURNAL:
            raise ValueError('journal file type or size')
        raw = stream.read(_MAX_JOURNAL+1)
    if len(raw) > _MAX_JOURNAL or (raw and not raw.endswith(b'\n')):
        raise ValueError('journal truncated or oversized')
    records = []; previous = _GENESIS; scope = None
    for index,line in enumerate(raw.splitlines(),1):
        if not line or len(line)+1 > _MAX_RECORD:
            raise ValueError('journal record size')
        record = json.loads(line.decode('utf-8',errors='strict'),object_pairs_hook=pairs,
                            parse_constant=constant)
        if type(record) is not dict or not _RESERVED <= set(record):
            raise ValueError('journal record schema')
        if type(record['sequence']) is not int or record['sequence'] != index:
            raise ValueError('journal sequence mismatch')
        if scope is None: scope = record['scope']
        if scope not in _SCOPES or record['scope'] != scope or record['previous_sha256'] != previous:
            raise ValueError('journal scope or chain mismatch')
        if not isinstance(record.get('event'),str) or not record['event']:
            raise ValueError('missing journal event')
        body = dict(record); digest = body.pop('sha256')
        if hashlib.sha256(_encode(body)).hexdigest() != digest:
            raise ValueError('journal hash mismatch')
        records.append(record); previous = digest
    return records


class RunWatchdog:
    def __init__(self, owner, deadline, clock=time.monotonic):
        if type(deadline) not in (int,float) or not math.isfinite(deadline):
            raise ValueError('invalid deadline')
        self.owner = owner
        self.deadline = deadline
        self.clock = clock
        self._done = threading.Event()
        self._thread = None
        self.expired = threading.Event()
        self.error_type = ''

    def start(self):
        if self._thread is not None or self._done.is_set():
            raise RuntimeError('watchdog already used')
        self._thread = threading.Thread(target=self._watch,name='pal-live-wall-watchdog',daemon=True)
        self._thread.start()

    def _watch(self):
        if self._done.wait(max(0,self.deadline-self.clock())):
            return
        self.expired.set()
        try:
            self.owner.close_run('wall_deadline')
        except BaseException as error:
            self.error_type = type(error).__name__

    def close(self):
        self._done.set()
        if self._thread is not None:
            self._thread.join(6)
            if self._thread.is_alive():
                raise RuntimeError('watchdog teardown exceeded bound')
