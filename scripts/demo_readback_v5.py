"""Inspect one structural mock completion before and after a source stop."""
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits
from pal.events_v5 import EventReader
from pal.host_read_v5 import HostReader
from pal.memory_v5 import MemoryStore
from pal.mock_runner_v5 import MockRunner
from pal.read_consumer_v5 import inspect_session, render
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore


def _value(result):
    if not result.ok:
        raise RuntimeError('local demo owner returned ' + result.error.code.value)
    return result.value.to_json()


def run_demo():
    with tempfile.TemporaryDirectory(prefix='pal-readback-') as directory:
        connection = sqlite3.connect(Path(directory) / 'demo.sqlite', isolation_level=None)
        try:
            memory = artifacts = verifications = None
            grant = Grant((), ('demo',), Limits(0, 4, 4))
            tasks = TaskStore(connection, host_limits=Limits(0, 20, 20), host_grant=grant,
                expert_id='mock-expert', source_gate=lambda c, refs: memory.source_gate(c, refs),
                artifact_inspect=lambda c, request: artifacts.inspect(c, request),
                verification_inspect=lambda c, request: verifications.inspect(c, request))
            memory = MemoryStore(connection, sanitize_text=lambda text: text,
                append_event=tasks.append_event, invalidate_by_refs=tasks.invalidate_by_refs)
            artifacts = ArtifactStore(connection, authorize_save=tasks.authorize_artifact_save,
                                      source_gate=memory.source_gate)
            verifications = VerificationStore(connection, context=tasks.verification_context,
                artifact_inspect=artifacts.inspect, source_gate=memory.source_gate)
            refs = []
            for key, text in [('request', '社内打合せ案内の下書きを保存する。'),
                              ('details', '日時・場所は未確定。送信しない。')]:
                refs.append(_value(memory.append({'client_key': key, 'session_id': 'demo-session',
                    'role': 'user', 'text': text}))['record_ref'])
            _value(tasks.create({'key': 'create', 'session_id': 'demo-session',
                'origin_record_ref': refs[0], 'brief': {
                    'purpose': 'ローカル下書きの保存と読返しを確認する',
                    'target': {'repository': 'demo', 'issue_numbers': [], 'files': []},
                    'constraints': ['送信しない', '日時・場所を補わない'],
                    'conditions': [{'description': 'ローカル下書きが保存されている',
                                    'check': 'artifact_saved'}], 'context_refs': [refs[1]]}},
                request_scope=grant))

            def mock_expert(context, **diagnostics):
                return {'kind': 'compose', 'media_type': 'text/plain',
                    'content': '打合せのご案内（下書き）\n日時・場所は未確定です。\n送信前にご確認ください。',
                    'source_refs': [item['ref'] for item in context['context']]}

            runner = MockRunner(tasks, memory, artifacts=artifacts, verifications=verifications)
            completed = _value(runner.run_once(mock_expert))
            if completed['status'] != 'completed':
                raise RuntimeError('local mock did not complete the storage condition')
            reader = HostReader(memory, artifacts, verifications)
            events = EventReader(connection, page_size=2)
            request = {'session_id': 'demo-session'}
            before = _value(inspect_session(request, events=events, tasks=tasks, reader=reader))
            _value(memory.stop_reference({'key': 'stop-details', 'source_ref': refs[1]},
                                         session_id='demo-control'))
            after = _value(inspect_session(request, events=events, tasks=tasks, reader=reader))
            return {'before': before, 'after': after}
        finally:
            connection.close()


if __name__ == '__main__':
    inspection = run_demo()
    print('Local temporary SQLite demo; mock model and structural verification only.\n')
    print('Before source stop\n' + render(inspection['before']))
    print('\nAfter source stop\n' + render(inspection['after']))
