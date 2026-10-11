"""UI02 admission faults with in-process fixtures; no server or real provider."""
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from pal.contracts_v5 import ErrorCode, Grant, Limits, Result
from pal.native_http_v5 import LocalNativeApp
from pal.primary_host_v5 import NativePrimaryHost
import native_http_fixtures_v5 as fixtures


class NativeAdmissionTests(unittest.TestCase):
    def start(self, provider=None):
        provider = provider if provider is not None else fixtures.Provider()
        app = LocalNativeApp(provider=provider,
                             request_scope=Grant((), ('demo',), Limits(0, 6, 6)),
                             host_limits=Limits(0, 20, 20))
        self.addCleanup(app.close, timeout=.25)
        return app, provider

    def retained_pending(self, app, turn_id):
        with app.owners() as (_, tasks, memory, artifacts, verifier, host):
            observed = host.get_turn({'turn_id': turn_id})
            self.assertTrue(observed.ok)
            self.assertEqual(observed.value.to_json()['status'], 'pending')

    def test_malformed_saved_admission_holds_without_dispatch_or_lost_input(self):
        changes = {
            'extra': lambda v: {**v, 'unexpected': True},
            'missing_id': lambda v: {'status': v['status']},
            'missing_status': lambda v: {'turn_id': v['turn_id']},
            'empty_id': lambda v: {**v, 'turn_id': ''},
            'nontext_id': lambda v: {**v, 'turn_id': ['not-an-id']},
            'unknown_status': lambda v: {**v, 'status': 'queued'},
            'nontext_status': lambda v: {**v, 'status': True},
            'nonobject': lambda v: 'pending',
        }
        original = NativePrimaryHost.submit
        for label, change in changes.items():
            with self.subTest(fault=label):
                app, provider = self.start()
                saved = []

                def malformed(host, request):
                    admitted = original(host, request)
                    self.assertTrue(admitted.ok)
                    value = admitted.value.to_json()
                    saved.append(value['turn_id'])
                    return Result.success(change(value))

                with patch.object(NativePrimaryHost, 'submit', malformed):
                    response, code = app.submit({'client_key': 'fault', 'text': 'synthetic saved input'})
                self.assertTrue(app.wait_idle(timeout=2))
                self.assertEqual(provider.requests, [], 'Malformed admission must authorize no dispatch')
                self.assertEqual(code, 503)
                self.assertFalse(response['ok'])
                self.assertEqual(response['error']['code'], 'unavailable')
                self.assertEqual(app.status()['worker_status'], 'held')
                self.retained_pending(app, saved[0])
                self.assertEqual(app.submit({'client_key': 'later', 'text': 'synthetic'})[1], 503)
                self.assertEqual(provider.preflights, 0)
                path = Path(app.database_path)
                self.assertTrue(app.close(timeout=.25), 'Refused admission must not retain an admission slot')
                self.assertTrue(path.is_file())

    def test_owner_exception_after_admission_keeps_input_and_allows_bounded_close(self):
        app, provider = self.start()
        original = NativePrimaryHost.submit
        saved = []

        def interrupted_reply(host, request):
            value = original(host, request).value.to_json()
            saved.append(value['turn_id'])
            raise RuntimeError('SYNTHETIC_PRIVATE_OWNER_ERROR')

        with patch.object(NativePrimaryHost, 'submit', interrupted_reply):
            response, code = app.submit({'client_key': 'exception', 'text': 'synthetic saved input'})
        self.assertEqual(code, 503)
        self.assertNotIn('SYNTHETIC_PRIVATE_OWNER_ERROR', json.dumps(response))
        self.assertEqual(app.status()['worker_status'], 'held')
        self.assertEqual(provider.requests, [])
        self.assertEqual(provider.preflights, 0)
        self.retained_pending(app, saved[0])
        self.assertTrue(app.close(timeout=.25))
        self.assertTrue(Path(app.database_path).is_file())

    def test_valid_pending_and_committed_replay_do_not_duplicate_fixture_calls(self):
        entered, release = threading.Event(), threading.Event()

        def respond(request):
            entered.set()
            self.assertTrue(release.wait(2))
            return fixtures.primary(request)

        provider = fixtures.Provider(respond)
        app, _ = self.start(provider)
        self.addCleanup(release.set)
        request = {'client_key': 'valid', 'text': 'synthetic input'}
        first, code = app.submit(request)
        self.assertEqual(code, 200)
        self.assertEqual(set(first['value']), {'turn_id', 'status'})
        self.assertEqual(first['value']['status'], 'pending')
        self.assertTrue(entered.wait(2))
        self.assertEqual(app.submit(request), (first, 200))
        release.set()
        self.assertTrue(app.wait_idle(timeout=2))
        replay, code = app.submit(request)
        self.assertEqual(code, 200)
        self.assertEqual(replay['value'], {'turn_id': first['value']['turn_id'], 'status': 'committed'})
        self.assertTrue(app.wait_idle(timeout=2))
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(app.status()['worker_status'], 'idle')
        self.assertTrue(app.close(timeout=.25))

    def test_valid_owner_errors_preserve_conflict_and_hold_unavailable(self):
        for error, state in ((ErrorCode.CONFLICT, 'idle'), (ErrorCode.UNAVAILABLE, 'held')):
            with self.subTest(error=error):
                app, provider = self.start()
                result = Result.failure(error, 'synthetic refusal')
                with patch.object(NativePrimaryHost, 'submit', return_value=result):
                    response, code = app.submit({'client_key': 'refused', 'text': 'synthetic input'})
                self.assertEqual((response, code), (result.to_json(), 200))
                self.assertEqual(app.status()['worker_status'], state)
                self.assertEqual(provider.requests, [])
                self.assertEqual(provider.preflights, 0)
                self.assertTrue(app.close(timeout=.25))
