"""Run a trusted-host correction and late-result demonstration in a fresh DB."""
import argparse
import json
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


def value(result):
    if not result.ok:
        raise RuntimeError('local owner returned ' + result.error.code.value)
    return result.value.to_json()


def run_demo():
    with tempfile.TemporaryDirectory(prefix='pal-change-') as directory:
        conn = sqlite3.connect(Path(directory) / 'demo.sqlite', isolation_level=None)
        try:
            memory = artifacts = verifications = None
            grant = Grant((), ('demo',), Limits(0, 6, 6))
            tasks = TaskStore(conn, host_limits=Limits(0, 20, 20), host_grant=grant,
                expert_id='mock-expert', source_gate=lambda c, refs: memory.source_gate(c, refs),
                artifact_inspect=lambda c, request: artifacts.inspect(c, request),
                verification_inspect=lambda c, request: verifications.inspect(c, request))
            memory = MemoryStore(conn, sanitize_text=lambda text: text,
                append_event=tasks.append_event, invalidate_by_refs=tasks.invalidate_by_refs)
            artifacts = ArtifactStore(conn, authorize_save=tasks.authorize_artifact_save,
                                      source_gate=memory.source_gate)
            verifications = VerificationStore(conn, context=tasks.verification_context,
                artifact_inspect=artifacts.inspect, source_gate=memory.source_gate)
            session = 'change-demo'
            def record(key, text):
                return value(memory.append({'client_key': key, 'session_id': session,
                    'role': 'user', 'text': text}))['record_ref']
            def brief(purpose):
                return {'purpose': purpose,
                    'target': {'repository': 'demo', 'issue_numbers': [], 'files': []},
                    'constraints': ['送信しない'], 'context_refs': [],
                    'conditions': [{'description': '下書きが保存されている', 'check': 'artifact_saved'}]}
            origin = record('request', '打合せの案内を月曜日の予定で下書きにする。送信しない。')
            created = value(tasks.create({'key': 'create', 'session_id': session,
                'origin_record_ref': origin, 'brief': brief('月曜日の案内を保存する')},
                request_scope=grant))
            original = value(tasks.get_work({'goal_id': created['work_ref']['goal_id']}))
            # The saved correction is self-contained; this trusted fixture derives
            # no content from the earlier record. PRI interpretation is deferred.
            correction = record('correction', '訂正：打合せは10月12日午後3時。案内の下書きを保存し、送信しない。')
            runner = MockRunner(tasks, memory, artifacts=artifacts, verifications=verifications)
            inputs, change_requests, changes = [], [], []

            def old_expert(context, **diagnostics):
                inputs.append(context)
                request = {'key': 'change', 'work_ref': context['work_ref'], 'command': {
                    'kind': 'change', 'origin_record_ref': correction,
                    'brief': brief('10月12日午後3時の案内を保存する')}}
                change_requests.append(request)
                changes.append(value(tasks.control(request)))
                assert changes[-1]['control_status'] == 'draining'
                assert conn.execute('SELECT COUNT(*) FROM v5_tsk_lease WHERE active=1').fetchone()[0] == 1
                return {'kind': 'compose', 'content': '旧依頼の遅い結果。保存してはいけない。',
                        'media_type': 'text/plain', 'source_refs': [origin]}

            settled = value(runner.run_once(old_expert))
            assert (settled['status'], settled['state']) == ('released', 'queued')
            assert settled['work_ref'] == changes[0]['work_ref']
            assert conn.execute('SELECT COUNT(*) FROM v5_art_body').fetchone()[0] == 0
            assert conn.execute('SELECT COUNT(*) FROM v5_tsk_step').fetchone()[0] == 0
            assert conn.execute('SELECT COUNT(*) FROM v5_tsk_lease WHERE active=1').fetchone()[0] == 0

            def new_expert(context, **diagnostics):
                inputs.append(context)
                assert context['work_ref']['revision'] == 2
                assert [item['ref'] for item in context['context']] == [correction]
                assert 'pending_inputs' not in context and not context['steps']
                return {'kind': 'compose', 'content': '打合せのご案内（訂正版下書き）\n10月12日 午後3時から開催します。\n送信前に内容をご確認ください。',
                        'media_type': 'text/plain', 'source_refs': [correction]}

            completed = value(runner.run_once(new_expert))
            assert (completed['status'], completed['work_ref']['revision']) == ('completed', 2)
            assert completed['work_ref']['goal_id'] == created['work_ref']['goal_id']
            assert len(inputs) == 2
            assert value(tasks.control(change_requests[0])) == changes[0]
            history = value(tasks.get_work({'goal_id': created['work_ref']['goal_id'], 'revision': 1}))
            current = value(tasks.get_work({'goal_id': created['work_ref']['goal_id']}))
            assert history['state'] == 'superseded' and not history['current_artifact_refs']
            assert current['state'] == 'completed'
            assert not ({condition['id'] for condition in original['brief']['conditions']} &
                        {condition['id'] for condition in current['brief']['conditions']})
            usage = dict(conn.execute('SELECT kind,used FROM v5_tsk_usage WHERE goal=?',
                                     (created['work_ref']['goal_id'],)).fetchall())
            assert usage == {'model': 2, 'step': 1}
            assert conn.execute('SELECT COUNT(DISTINCT goal_id) FROM v5_intake_work').fetchone()[0] == 1
            inspection = value(inspect_session({'session_id': session}, events=EventReader(conn),
                tasks=tasks, reader=HostReader(memory, artifacts, verifications)))
            assert inspection['items'] and inspection['items'][0]['work']['value']['state'] == 'completed'
            return {'mode': 'trusted host / temporary SQLite / mock model / structural checks only',
                'created': created, 'changed': changes[0], 'settled': settled, 'completed': completed,
                'history': history, 'usage': usage, 'inspection': inspection}
        finally:
            conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    demo = run_demo()
    output = ('Local temporary SQLite; trusted-host correction; structural verification only.\n'
              '実行中の依頼を訂正しました。旧結果を保存せず、同じ仕事の新revisionで下書きを完成しました。\n'
              + render(demo['inspection']) + '\n')
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / 'demo.json').write_text(json.dumps(demo, ensure_ascii=False, indent=2) + '\n')
        (args.output_dir / 'demo.log').write_text(output)
    print(output)
