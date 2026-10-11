"""Demonstrate durable question/answer continuation using temporary local owners."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits, dumps
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
    with tempfile.TemporaryDirectory(prefix='pal-ask-') as directory:
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
            session = 'ask-demo'
            origin = value(memory.append({'client_key': 'request', 'session_id': session,
                'role': 'user', 'text': '打合せ案内の下書きを作成する。日時は確認してから書く。送信しない。'}))['record_ref']
            created = value(tasks.create({'key': 'create', 'session_id': session,
                'origin_record_ref': origin, 'brief': {
                    'purpose': '確認した日時を使って案内の下書きを保存する',
                    'target': {'repository': 'demo', 'issue_numbers': [], 'files': []},
                    'constraints': ['送信しない', '日時を推測しない'],
                    'conditions': [{'description': '下書きが保存されている', 'check': 'artifact_saved'}],
                    'context_refs': []}}, request_scope=grant))
            runner = MockRunner(tasks, memory, artifacts=artifacts, verifications=verifications)
            model_inputs = []

            def ask(context, **diagnostics):
                model_inputs.append(context)
                return {'kind': 'ask', 'question': '打合せの日時を教えてください。',
                    'missing_fact': '打合せ日時', 'source_refs': [origin]}

            waiting = value(runner.run_once(ask))
            assert waiting['status'] == 'waiting' and waiting['state'] == 'waiting_input'
            current = value(tasks.get_work({'goal_id': created['work_ref']['goal_id']}))
            assert current['open_questions'] == [{'id': waiting['question_id'],
                'text': '打合せの日時を教えてください。', 'revision': 1}]
            assert conn.execute('SELECT COUNT(*) FROM v5_tsk_lease WHERE active=1').fetchone()[0] == 0
            answer = value(memory.append({'client_key': 'answer', 'session_id': session,
                'role': 'user', 'text': '10月12日の午後2時です。'}))['record_ref']
            request = {'key': dumps(['C10.answer', current['work_ref']['goal_id'], 1,
                        waiting['question_id'], answer]), 'work_ref': current['work_ref'],
                'command': {'kind': 'answer', 'question_id': waiting['question_id'],
                            'answer_record_ref': answer}}
            answered = value(tasks.control(request))
            assert answered['state'] == 'queued'
            association = {'question_id': waiting['question_id'], 'step_id': waiting['step_id'],
                           'answer_record_ref': answer}

            def compose(context, **diagnostics):
                model_inputs.append(context)
                assert context['pending_inputs'] == [association]
                bodies = {dumps(item['ref']): item['content'] for item in context['context']}
                assert bodies[dumps(answer)] == '10月12日の午後2時です。'
                return {'kind': 'compose', 'media_type': 'text/plain',
                    'content': '打合せのご案内（下書き）\n10月12日 午後2時から開催します。\n送信前に内容をご確認ください。',
                    'source_refs': [item['ref'] for item in context['context']]}

            completed = value(runner.run_once(compose))
            assert completed['status'] == 'completed' and len(model_inputs) == 2
            assert value(tasks.control(request)) == answered
            assert value(tasks.get_work({'goal_id': created['work_ref']['goal_id']}))['open_questions'] == []
            usage = dict(conn.execute('SELECT kind,used FROM v5_tsk_usage WHERE goal=?',
                                     (created['work_ref']['goal_id'],)).fetchall())
            assert usage == {'model': 2, 'step': 2}
            inspection = value(inspect_session({'session_id': session}, events=EventReader(conn),
                tasks=tasks, reader=HostReader(memory, artifacts, verifications)))
            assert inspection['items'] and inspection['items'][0]['work']['value']['state'] == 'completed'
            return {'mode': 'temporary SQLite / mock model / structural checks only',
                'question': current['open_questions'][0], 'waiting': waiting, 'answered': answered,
                'association': association, 'completed': completed, 'usage': usage,
                'inspection': inspection}
        finally:
            conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    demo = run_demo()
    output = ('Local temporary SQLite; mock question/answer; structural verification only.\n'
              + demo['question']['text'] + '\n回答保存後、同じ仕事を再開しました。\n'
              + render(demo['inspection']) + '\n')
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / 'demo.json').write_text(json.dumps(demo, ensure_ascii=False, indent=2) + '\n')
        (args.output_dir / 'demo.log').write_text(output)
    print(output)
