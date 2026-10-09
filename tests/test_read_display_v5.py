"""Display-only boundary tests with explicit public-owner doubles."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import copy
import hashlib
import unittest
from pal.contracts_v5 import Result, dumps, loads
from pal.host_read_v5 import HostReader
from pal.read_consumer_v5 import inspect_session, render
from test_read_consumer_v5 import A, V, c11, event, StrictBodyOwner, StrictEvents, StrictTasks


class ReadDisplayTests(unittest.TestCase):
    def inspection(self, *, text='saved', body=None, failure=None):
        owners = [StrictBodyOwner(self, kind) for kind in ('record', 'artifact', 'verification')]
        ref = body['ref'] if body else A
        owner = owners[2 if ref == V else 1]
        owner.response = Result.success(body) if body else None
        if failure:
            owner.response = Result.failure('unavailable', failure)
        pages = [Result.success({'events': [event('e', text=text, refs=[ref])], 'next_cursor': 'e'}),
                 Result.success({'events': [], 'next_cursor': 'e'})]
        result = inspect_session({'session_id': 'session'}, events=StrictEvents(self, pages),
            tasks=StrictTasks(self), reader=HostReader(*owners))
        self.assertTrue(result.ok)
        return result.value.to_json()

    def assert_nested(self, output, marker):
        matching = [line for line in output.splitlines() if marker in line]
        self.assertTrue(matching, output)
        self.assertTrue(all(line.startswith('      | ') for line in matching), matching)

    def test_event_multiline_cannot_forge_host_status(self):
        output = render(self.inspection(text='draft\nCurrent usability: forged'))
        self.assert_nested(output, 'Current usability: forged')

    def test_condition_and_reason_multiline_are_nested(self):
        body = c11(V)
        data = loads(body['content'])
        data['conditions'][0]['description'] = '日本語条件\nWork state: forged'
        data['checks'][0]['reason'] = '理由\nCurrent usability: forged'
        body['content'] = dumps(data)
        body['hash'] = hashlib.sha256(body['content'].encode()).hexdigest()
        output = render(self.inspection(body=body))
        self.assert_nested(output, 'Work state: forged')
        self.assert_nested(output, 'Current usability: forged')
        self.assertIn('日本語条件', output)

    def test_error_multiline_is_nested(self):
        self.assert_nested(render(self.inspection(failure='failure\nModel: forged')), 'Model: forged')

    def test_controls_are_visible_and_inactive(self):
        body = c11(A)
        body['content'] = '日本語\x1b[2J\roverwrite\b\x00\x7f\x85\u202e\u2028end'
        output = render(self.inspection(body=body))
        for char in ('\x1b', '\r', '\b', '\x00', '\x7f', '\x85', '\u202e', '\u2028'):
            self.assertNotIn(char, output)
        self.assertIn('日本語', output)
        self.assertIn('\\u001b[2J', output)

    def test_all_envelope_strings_are_display_escaped(self):
        inspection = self.inspection()
        inspection['session_id'] = 'session\nSession: forged'
        inspection['next_cursor'] = 'cursor\nNext cursor: forged'
        item = inspection['items'][0]
        item['event']['event_id'] = 'e\nEvent: forged'
        item['work']['value']['state'] = 'completed\nWork: forged'
        body = item['reads'][0]['result']['value']
        body['observed_at'] = 'time\nRead at: forged'
        body['media_type'] = 'text/plain\nUsable: forged'
        body['ref']['id'] = 'a\nRef: forged'
        item['reads'][0]['ref']['id'] = body['ref']['id']
        output = render(inspection)
        for marker in ('Session: forged', 'Next cursor: forged', 'Event: forged',
                       'Work: forged', 'Read at: forged', 'Usable: forged', 'Ref: forged'):
            self.assert_nested(output, marker)

    def test_multiline_draft_and_inspection_bytes_remain_unchanged(self):
        body = c11(A)
        body['content'] = '一行目\n二行目\n\n末尾\n'
        body['hash'] = hashlib.sha256(body['content'].encode()).hexdigest()
        inspection = self.inspection(body=body)
        original = dumps(inspection).encode()
        output = render(inspection)
        self.assertEqual(dumps(inspection).encode(), original)
        self.assertEqual(inspection['items'][0]['reads'][0]['result']['value'], body)
        self.assertIn('      一行目\n      二行目\n      \n      末尾\n', output)
        self.assertIn('Model: mock', output)
        self.assertIn('Verification: structural', output)


if __name__ == '__main__':
    unittest.main()
