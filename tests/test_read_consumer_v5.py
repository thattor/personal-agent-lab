"""READ01 strict public C02/C11/C14 doubles; not actual owner integration."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import hashlib
import unittest
from pal.contracts_v5 import Result, dumps

NOTICE = 'a source registered for this completed work was stopped; completion is historical'
R = {'kind': 'record', 'id': 'r'}
A = {'kind': 'artifact', 'id': 'a'}
V = {'kind': 'verification', 'id': 'v'}
WORK = {'goal_id': 'g', 'revision': 1, 'epoch': 0}


def c11(ref, *, usable=True):
    projection = {'work_ref': WORK, 'conditions': [{'id': 'c', 'description': '条件を確認', 'check': 'semantic'}],
        'artifact_refs': [A], 'artifacts': [{'artifact_ref': A, 'hash': 'a' * 64, 'bytes': 6}],
        'source_refs': [R], 'checks': [{'condition_id': 'c', 'status': 'unknown', 'reason': 'no evaluator', 'evidence_refs': []}]}
    content = dumps(projection) if ref['kind'] == 'verification' else '保存本文\n'
    return {'ref': ref, 'content': content,
        'media_type': 'application/json' if ref['kind'] == 'verification' else 'text/plain',
        'hash': hashlib.sha256(content.encode()).hexdigest(), 'observed_at': '2026-10-09T01:00:00Z',
        'work_ref': WORK, 'source_refs': [R], 'usable': usable}


def event(identity, *, kind='result', work=WORK, refs=None, text='saved result'):
    item = {'event_id': identity, 'kind': kind, 'text': text, 'refs': [A, V] if refs is None else refs}
    if work is not None:
        item['work_ref'] = work
    return item


class StrictBodyOwner:
    def __init__(self, test, kind):
        self.test, self.kind, self.calls = test, kind, []
        self.response, self.failure, self.interrupt = None, None, None
        self.usable = True

    def read(self, request, *, purpose):
        self.test.assertEqual(set(request), {'ref'})
        self.test.assertEqual(request['ref']['kind'], self.kind)
        self.test.assertIn(purpose, ('user_view', 'verification', 'model_context'))
        self.calls.append((copy.deepcopy(request), purpose))
        if self.interrupt:
            raise self.interrupt('private owner diagnostic')
        if self.failure:
            return Result.failure(self.failure, 'owner unavailable')
        return self.response if self.response is not None else Result.success(c11(request['ref'], usable=self.usable))


class StrictEvents:
    def __init__(self, test, pages, initial_cursor=None):
        self.test, self.pages, self.calls = test, pages, []
        self.initial_cursor = initial_cursor

    def get_events(self, request):
        expected = {'session_id': 'session'}
        if self.initial_cursor is not None:
            expected['after_event_id'] = self.initial_cursor
        if self.calls:
            expected['after_event_id'] = self.pages[len(self.calls) - 1].value.to_json()['next_cursor']
        self.test.assertEqual(request, expected)
        self.calls.append(copy.deepcopy(request))
        return self.pages[len(self.calls) - 1]


class StrictTasks:
    def __init__(self, test):
        self.test, self.calls = test, []
        self.failures, self.states = {}, {'g': 'completed', 'other': 'paused'}

    def get_work(self, request):
        self.test.assertEqual(set(request), {'goal_id', 'revision'})
        self.test.assertIs(type(request['goal_id']), str)
        self.test.assertIs(type(request['revision']), int)
        self.calls.append(copy.deepcopy(request))
        if request['goal_id'] in self.failures:
            return Result.failure(self.failures[request['goal_id']], 'work unavailable')
        return Result.success({'work_ref': {**WORK, **request}, 'brief': {'purpose': 'draft', 'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
                'constraints': [], 'conditions': [{'id': 'c', 'description': 'saved', 'check': 'artifact_saved'}], 'context_refs': []},
            'grant': {'capabilities': [], 'repositories': ['repo'], 'limits': {'max_operations': 0, 'max_steps': 1, 'max_model_calls': 1}},
            'state': self.states[request['goal_id']], 'current_artifact_refs': [A], 'open_questions': []})


class ReadConsumerTests(unittest.TestCase):
    def setUp(self):
        from pal.host_read_v5 import HostReader
        from pal.read_consumer_v5 import inspect_session, render
        self.inspect_session, self.render = inspect_session, render
        self.owners = [StrictBodyOwner(self, k) for k in ('record', 'artifact', 'verification')]
        self.reader = HostReader(*self.owners)
        self.tasks = StrictTasks(self)

    def error(self, result, code):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, code)

    def inspect(self, pages, **kwargs):
        self.events = StrictEvents(self, pages)
        result = self.inspect_session({'session_id': 'session'}, events=self.events,
            tasks=self.tasks, reader=self.reader, **kwargs)
        self.assertTrue(result.ok, result.to_json())
        self.assertTrue(all(purpose == 'user_view' for owner in self.owners for request, purpose in owner.calls))
        return result.value.to_json()

    @staticmethod
    def page(items, cursor):
        return Result.success({'events': items, 'next_cursor': cursor})

    def test_host_dispatches_all_kinds_exact_request_and_keyword_purpose(self):
        for ref, owner in zip((R, A, V), self.owners):
            for purpose in ('user_view', 'verification', 'model_context'):
                request = {'ref': ref}
                response = self.reader.read(request, purpose=purpose)
                self.assertEqual(response.value.to_json(), c11(ref))
                self.assertEqual(owner.calls[-1], (request, purpose))
            self.assertEqual(len(owner.calls), 3)

    def test_bad_host_input_or_unowned_kind_never_falls_back(self):
        for request in ({}, {'ref': R, 'extra': 1}, {'ref': {'kind': 'alien', 'id': 'r'}}, {'ref': {'kind': 'record', 'id': ''}}):
            self.error(self.reader.read(request, purpose='user_view'), 'invalid_input')
        for kind in ('note', 'source', 'receipt'):
            self.error(self.reader.read({'ref': {'kind': kind, 'id': 'x'}}, purpose='user_view'), 'unavailable')
        for purpose in ('wrong', True, None):
            with self.assertRaises(ValueError):
                self.reader.read({'ref': R}, purpose=purpose)
        self.assertTrue(all(not owner.calls for owner in self.owners))

    def test_owner_exceptions_malformed_results_and_interrupts(self):
        owner = self.owners[0]
        owner.interrupt = RuntimeError
        self.error(self.reader.read({'ref': R}, purpose='user_view'), 'unavailable')
        for failure in (KeyboardInterrupt, SystemExit):
            owner.interrupt = failure
            with self.assertRaises(failure):
                self.reader.read({'ref': R}, purpose='user_view')
        owner.interrupt = None
        for response in ('not Result', Result.success({})):
            owner.response = response
            self.error(self.reader.read({'ref': R}, purpose='user_view'), 'unavailable')

    def test_pages_advance_unselected_events_and_preserve_multiwork_ref_order(self):
        selected = [event('e2', refs=[V, R, A]), event('e3', work={**WORK, 'goal_id': 'other'})]
        out = self.inspect([self.page([event('e1', kind='accepted', refs=[])], 'e1'),
            self.page(selected, 'e3'), self.page([], 'e3')])
        self.assertEqual(set(out), {'session_id', 'items', 'next_cursor', 'truncated'})
        self.assertEqual(out['session_id'], 'session')
        self.assertEqual((out['next_cursor'], out['truncated']), ('e3', False))
        self.assertEqual([i['event'] for i in out['items']], selected)
        self.assertEqual([r['ref'] for r in out['items'][0]['reads']], [V, R, A])
        self.assertEqual([i['work']['value']['state'] for i in out['items']], ['completed', 'paused'])
        self.assertEqual(self.tasks.calls, [{'goal_id': 'g', 'revision': 1}, {'goal_id': 'other', 'revision': 1}])
        self.assertTrue(all(purpose == 'user_view' for owner in self.owners for request, purpose in owner.calls))
        self.assertEqual(out['items'][0]['reads'][0]['validity'], 'current')
        self.assertIsNone(out['items'][0]['reads'][1]['validity'])

    def test_stop_cause_requires_exact_notice_goal_revision_and_dependency_intersection(self):
        self.owners[2].usable = False
        notices = [event('notice', kind='progress', text=NOTICE, refs=[R]),
            event('notice', kind='progress', text=NOTICE, refs=[R], work={**WORK, 'goal_id': 'other'}),
            event('notice', kind='progress', text=NOTICE, refs=[R], work={**WORK, 'revision': 2}),
            event('notice', kind='progress', text=NOTICE, refs=[{'kind': 'record', 'id': 'unrelated'}]),
            event('notice', kind='progress', text=NOTICE + '?', refs=[R])]
        for index, notice in enumerate(notices):
            out = self.inspect([self.page([event('result'), notice], 'notice'), self.page([], 'notice')])
            reading = out['items'][0]['reads'][1]
            self.assertEqual(reading['validity'], 'source stopped' if index == 0 else 'not current')
            self.assertEqual(set(reading), {'ref', 'result', 'validity'})
        self.owners[2].usable = True
        out = self.inspect([self.page([event('result'), notices[0]], 'notice'), self.page([], 'notice')])
        self.assertEqual(out['items'][0]['reads'][1]['validity'], 'current')

    def test_missing_work_and_per_work_per_ref_errors_stay_visible(self):
        self.tasks.failures['g'] = 'not_found'
        self.owners[0].failure = 'denied'
        out = self.inspect([self.page([event('e1', refs=[R, V]), event('e2', work=None, refs=[A])], 'e2'), self.page([], 'e2')])
        self.assertEqual(out['items'][0]['work']['error']['code'], 'not_found')
        self.assertEqual(out['items'][0]['reads'][0]['result']['error']['code'], 'denied')
        self.assertIsNone(out['items'][0]['reads'][0]['validity'])
        self.assertEqual(out['items'][1]['work']['error']['code'], 'unavailable')
        self.assertEqual(self.tasks.calls, [{'goal_id': 'g', 'revision': 1}])
        rendered = self.render(out).lower()
        self.assertIn('not_found', rendered)
        self.assertIn('denied', rendered)
        self.assertIn('unavailable', rendered)

    def test_bounded_pages_cursor_and_visible_truncation(self):
        out = self.inspect([self.page([event('e1')], 'e1')], max_pages=1)
        self.assertTrue(out['truncated'])
        self.assertEqual(out['next_cursor'], 'e1')
        self.assertIn('truncat', self.render(out).lower())

    def test_stalled_cursor_malformed_page_and_page_error_are_failures(self):
        for pages in ([self.page([event('e1')], None)], [Result.success({'events': [], 'extra': 1})],
                      [self.page([event('e1')], 'e1'), self.page([event('e2')], 'e1')],
                      [Result.failure('unavailable', 'page unavailable')]):
            events = StrictEvents(self, pages)
            result = self.inspect_session({'session_id': 'session'}, events=events, tasks=self.tasks, reader=self.reader)
            self.error(result, 'unavailable')

    def test_initial_cursor_is_forwarded_without_new_state_or_guess(self):
        events = StrictEvents(self, [self.page([], 'resume-here')], initial_cursor='resume-here')
        result = self.inspect_session({'session_id': 'session', 'after_event_id': 'resume-here'},
            events=events, tasks=self.tasks, reader=self.reader)
        self.assertTrue(result.ok, result.to_json())
        self.assertEqual(result.value.to_json()['next_cursor'], 'resume-here')
        self.assertEqual(result.value.to_json()['items'], [])

    def test_closed_consumer_requests_and_host_page_bounds(self):
        events = StrictEvents(self, [])
        for request in ({}, {'session_id': ''}, {'session_id': 'session', 'extra': 1}, {'session_id': 'session', 'after_event_id': True}):
            self.error(self.inspect_session(request, events=events, tasks=self.tasks, reader=self.reader), 'invalid_input')
        for maximum in (0, 65, True):
            try:
                result = self.inspect_session({'session_id': 'session'}, events=events, tasks=self.tasks, reader=self.reader, max_pages=maximum)
            except ValueError:
                continue
            self.error(result, 'invalid_input')
        self.assertEqual(events.calls, [])

    def test_renderer_separates_state_current_usability_fixed_checks_and_read_time(self):
        out = self.inspect([self.page([event('e1')], 'e1'), self.page([], 'e1')])
        text = self.render(out)
        self.assertIs(type(text), str)
        for label in ('mock', 'structural', 'read at', 'completed', 'current', 'unknown'):
            self.assertIn(label, text.lower())
        self.assertIn('保存本文', text)
        self.assertIn('条件を確認', text)
        self.assertIn('2026-10-09T01:00:00Z', text)
        self.owners[2].usable = False
        out = self.inspect([self.page([event('e1')], 'e1'), self.page([], 'e1')])
        text = self.render(out).lower()
        self.assertIn('not current', text)
        self.assertNotIn('source stopped', text)


if __name__ == '__main__':
    unittest.main()
