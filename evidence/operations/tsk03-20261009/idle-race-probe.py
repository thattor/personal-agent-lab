"""Deterministic stale-idle diagnostic; fresh DB and in-process mock only."""
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from pal.store import Store
from pal.runtime import Runtime
from tests.helpers import settled, work_settled
from tests.test_runtime_envelope import ScriptedProvider

old_idle_ready = threading.Event()
allow_old_idle = threading.Event()
second_context = threading.Event()
allow_work = threading.Event()
original_deliver = Store.deliver
original_context = Store.context
worker_context_calls = 0
held = False


def deliver(self, *args, **kwargs):
    global held
    if threading.current_thread().name == 'pal-task' and not held:
        held = True
        old_idle_ready.set()
        assert allow_old_idle.wait(3), 'old idle barrier timed out'
    return original_deliver(self, *args, **kwargs)


def context(self, *args, **kwargs):
    global worker_context_calls
    if threading.current_thread().name == 'pal-task':
        worker_context_calls += 1
        if worker_context_calls == 2:
            second_context.set()
            assert allow_work.wait(3), 'work barrier timed out'
    return original_context(self, *args, **kwargs)


with tempfile.TemporaryDirectory() as directory, patch.object(Store, 'deliver', deliver), patch.object(Store, 'context', context):
    runtime = Runtime(Path(directory) / 'state.db', provider=ScriptedProvider([
        {'kind': 'incomplete_preview', 'content': 'Date {{date}}',
         'missing': '{{date}}', 'citations': []},
    ]))
    try:
        assert old_idle_ready.wait(3), 'initial empty-work pass not reached'
        goal_id = settled(runtime, 'g', 'Make a draft blank template with {{date}}')['goal']['id']
        assert not runtime.idle.is_set()
        allow_old_idle.set()
        assert second_context.wait(3), 'second worker pass not reached'
        assert runtime.idle.wait(0.1)
        goal = runtime.store.get_goal(goal_id)
        receipts = runtime.store.inspect()['receipts']
        assert goal['state'] == 'queued'
        assert receipts == []
        print('STALE IDLE REPRODUCED: queued receipts=0')
        allow_work.set()
        outcome = work_settled(runtime, goal_id)
        assert outcome['state'] == 'failed'
        assert outcome['reason'] == 'incomplete_template'
        receipts = runtime.store.inspect()['receipts']
        assert len(receipts) == 1
        assert receipts[0]['role'] == 'preview'
        print('CANONICAL OUTCOME: failed incomplete_template preview_receipts=1')
    finally:
        allow_old_idle.set()
        allow_work.set()
        runtime.close()
