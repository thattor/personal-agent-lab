"""INT00/1 wire acceptance; none of these tests exercise PAL services."""
import copy
from dataclasses import FrozenInstanceError
from decimal import Decimal
import doctest
import json
import math
from pathlib import Path
import sys
import unittest

import pal.contracts_v5 as c


class ContractsV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = c.loads(Path(__file__).with_name('fixtures').joinpath('contracts_v5.json').read_bytes())

    def assertSameJSON(self, left, right):
        self.assertIs(type(left), type(right))
        if type(left) is dict:
            self.assertEqual(set(left), set(right))
            for key in left:
                self.assertSameJSON(left[key], right[key])
        elif type(left) is list:
            self.assertEqual(len(left), len(right))
            for a, b in zip(left, right):
                self.assertSameJSON(a, b)
        elif type(left) is float:
            self.assertEqual(left.hex(), right.hex())
        else:
            self.assertEqual(left, right)

    def parse_case(self, case, data=None):
        target = case['target']
        raw = case.get('input_raw') if data is None else None
        if data is None and raw is None:
            data = copy.deepcopy(case['input'])
        if target.startswith('Model'):
            allowed = [c.Ref.from_json(ref) for ref in case['allowed_refs']]
            parser = c.parse_model_action if target == 'ModelAction' else c.parse_model_draft_brief
            return parser(raw if raw is not None else c.dumps(data), allowed_refs=allowed)
        if raw is not None:
            data = c.loads(raw)
        if target == 'Action':
            return c.action_from_json(data)
        return getattr(c, target).from_json(data)

    def test_shared_fixture_acceptance_and_lossless_roundtrip(self):
        self.assertEqual(self.fixture['contract_id'], 'PAL-v5-common-wire')
        self.assertEqual(self.fixture['contract_version'], 'INT00/1')
        for case in self.fixture['cases']:
            with self.subTest(case=case['id']):
                self.assertTrue(case['contract'])
                if case['expect'] == 'rejected':
                    with self.assertRaises(c.ContractError) as caught:
                        self.parse_case(case)
                    self.assertEqual(caught.exception.code, 'invalid_input')
                else:
                    parsed = self.parse_case(case)
                    original = case['input'] if 'input' in case else c.loads(case['input_raw'])
                    self.assertSameJSON(parsed.to_json(), original)
                    roundtrip = self.parse_case(case, c.loads(c.dumps(parsed)))
                    self.assertEqual(parsed, roundtrip)
                    self.assertSameJSON(roundtrip.to_json(), original)

    def test_shared_fixture_covers_closed_vocabularies_and_boundary_cases(self):
        accepted = [case for case in self.fixture['cases'] if case['expect'] == 'accepted']
        self.assertEqual({x['input']['kind'] for x in accepted if x['target'] == 'Ref'},
                         {'record', 'note', 'source', 'receipt', 'artifact', 'verification'})
        self.assertEqual({x['input']['kind'] for x in accepted if x['target'] == 'Action'},
                         {'lookup', 'operate', 'ask', 'compose', 'verify', 'report'})
        self.assertEqual({x['input']['error']['code'] for x in accepted
                          if x['target'] == 'Result' and not x['input']['ok']},
                         {'invalid_input', 'not_found', 'ambiguous', 'stale', 'denied',
                          'unavailable', 'limit', 'conflict'})
        rejected = [x for x in self.fixture['cases'] if x['expect'] == 'rejected']
        self.assertTrue(any('CT-24' in x['contract'] for x in rejected))
        self.assertTrue(any('unprovided' in x['id'] for x in rejected))

    def test_values_and_nested_arguments_are_immutable_snapshots(self):
        original = {'kind': 'operate', 'capability': 'read', 'arguments': {'array': [{'x': 1}]},
                    'source_refs': [{'kind': 'source', 'id': 's'}]}
        action = c.action_from_json(original)
        original['arguments']['array'][0]['x'] = 9
        original['source_refs'][0]['id'] = 'different'
        self.assertEqual(action.arguments.to_json(), {'array': [{'x': 1}]})
        self.assertEqual(action.source_refs, (c.Ref('source', 's'),))
        with self.assertRaises(FrozenInstanceError):
            action.capability = 'write'
        with self.assertRaises(FrozenInstanceError):
            action.source_refs[0].id = 'different'
        with self.assertRaises(TypeError):
            action.arguments.data['array'][0]['x'] = 2
        with self.assertRaises(FrozenInstanceError):
            action.arguments._text = '{}'
        result = action.to_json()
        result['arguments']['array'].append('changed')
        self.assertEqual(action.arguments.to_json(), {'array': [{'x': 1}]})
        items = ['x']
        grant = c.Grant(items, [], c.Limits(0, 0, 0))
        items.append('y')
        self.assertEqual(grant.capabilities, ('x',))

    def test_numbers_keep_json_type_and_sign(self):
        values = [1, 1.0, True, -0.0, 0.0, 0, False]
        wrapped = [c.JsonValue({'n': x}) for x in values]
        self.assertEqual(len(set(wrapped)), len(values))
        results = [c.Result.success(x) for x in values]
        self.assertEqual(len(set(results)), len(values))
        actions = [c.OperateAction('', {'n': x}, []) for x in values]
        self.assertEqual(len(set(actions)), len(values))
        for result, value in zip(results, values):
            self.assertSameJSON(c.loads(c.dumps(result))['value'], value)
        self.assertEqual(math.copysign(1, c.loads(c.dumps(-0.0))), -1)

    def test_optional_lookup_refs_absent_is_not_empty_or_null(self):
        absent = c.parse_model_action('{"kind":"lookup","query":""}', allowed_refs=[])
        empty = c.parse_model_action('{"kind":"lookup","query":"","source_refs":[]}', allowed_refs=[])
        self.assertNotEqual(absent, empty)
        self.assertNotIn('source_refs', absent.to_json())
        self.assertEqual(empty.to_json()['source_refs'], [])
        with self.assertRaises(c.ContractError):
            c.action_from_json({'kind': 'lookup', 'query': '', 'source_refs': None})

    def test_model_entrypoints_require_allowed_refs(self):
        with self.assertRaises(TypeError):
            c.parse_model_action('{"kind":"report","summary":""}')
        with self.assertRaises(TypeError):
            c.parse_model_draft_brief('{}')
        with self.assertRaises(TypeError):
            c.parse_model_action('{"kind":"report","summary":""}', allowed_refs=[{'kind': 'source', 'id': 's'}])
        source = c.Ref('source', 's')
        parsed = c.parse_model_action('{"kind":"verify","artifact_refs":[{"kind":"source","id":"s"}]}',
                                      allowed_refs=(x for x in [source]))
        self.assertEqual(parsed.artifact_refs, (source,))

    def test_raw_boundary_rejects_invalid_utf8_and_surrogates_everywhere(self):
        for raw in [b'"\xff"', b'\xff', '"\ud800"', '"\\udfff"', '{"\\ud800":0}', '\ufeff{}']:
            with self.subTest(raw=repr(raw)):
                with self.assertRaises(c.ContractError):
                    c.loads(raw)
        self.assertEqual(c.loads('"\\ud83d\\ude00"'), '😀')
        self.assertEqual(c.loads('"日本語"'.encode()), '日本語')

    def test_raw_boundary_rejects_duplicates_after_escape_decoding(self):
        for raw in ['{"a":1,"\\u0061":2}', '{"x":[{"a":1,"a":2}]}']:
            with self.assertRaises(c.ContractError):
                c.loads(raw)

    def test_python_non_json_values_are_rejected_at_decoded_and_serialization_boundaries(self):
        class HostileStr(str):
            def __str__(self):
                raise AssertionError('must not call arbitrary conversion')
        class HostileDict(dict):
            def items(self):
                raise AssertionError('must not call subclass items')
        class IntSubclass(int):
            pass
        for value in [(1,), {1}, Decimal('1.0'), b'x', float('nan'), float('inf'),
                      {1: 'x'}, {'x': '\ud800'}, {'\ud800': 0}, HostileStr('x'),
                      HostileDict(x=1), IntSubclass(1)]:
            with self.subTest(value_type=type(value).__name__):
                for operation in (c.JsonValue, c.dumps, c.Result.success):
                    with self.assertRaises(c.ContractError):
                        operation(value)
                with self.assertRaises(c.ContractError):
                    c.Result.from_json({'ok': True, 'value': value})
        for raw in [bytearray(b'{}'), memoryview(b'{}'), {}, None, HostileStr('{}')]:
            with self.assertRaises(c.ContractError):
                c.loads(raw)

    def test_closed_keys_for_every_wire_shape(self):
        targets = set()
        for case in self.fixture['cases']:
            if case['expect'] != 'accepted' or case['target'].startswith('Model'):
                continue
            target = case['target']
            value = case.get('input')
            if type(value) is not dict:
                continue
            identity = (target, value.get('kind'), value.get('ok'))
            if identity in targets:
                continue
            targets.add(identity)
            for key in value:
                # source_refs is optional only on lookup.
                if target == 'Action' and value.get('kind') == 'lookup' and key == 'source_refs':
                    continue
                changed = copy.deepcopy(value)
                del changed[key]
                with self.subTest(target=identity, missing=key):
                    with self.assertRaises(c.ContractError):
                        self.parse_case(case, changed)
            changed = {**value, 'malicious-unexpected-key': 0}
            with self.subTest(target=identity, extra=True):
                with self.assertRaises(c.ContractError):
                    self.parse_case(case, changed)

    def test_direct_constructors_enforce_the_same_types(self):
        failures = [
            lambda: c.WorkRef('', 1, 0), lambda: c.WorkRef('g', True, 0),
            lambda: c.WorkRef('g', 1, -1), lambda: c.Ref('SOURCE', 's'),
            lambda: c.Condition('', '', 'semantic'), lambda: c.DraftCondition('', 'other'),
            lambda: c.TargetFile('', None), lambda: c.Target('', [True], []),
            lambda: c.Target('', [], [{}]), lambda: c.Limits(0, -1, 0),
            lambda: c.Grant([], [], {}), lambda: c.ErrorInfo('other', '', []),
            lambda: c.Result(True), lambda: c.Result(1, None),
            lambda: c.Result(False, value=None, error=c.ErrorInfo('stale', '', [])),
            lambda: c.Result(True, value=0, error=c.ErrorInfo('stale', '', [])),
            lambda: c.LookupAction('', [1]), lambda: c.OperateAction('', [], []),
            lambda: c.AskAction('', None, []), lambda: c.ComposeAction('', 'other', []),
            lambda: c.VerifyAction([{}]), lambda: c.ReportAction(None),
            lambda: c.DraftBrief('', c.Target('', [], []), [], [], []),
            lambda: c.Brief('', c.Target('', [], []), [], [c.DraftCondition('', 'semantic')], []),
        ]
        for i, create in enumerate(failures):
            with self.subTest(constructor=i):
                with self.assertRaises(c.ContractError):
                    create()
        self.assertEqual(c.Result.success(None).to_json(), {'ok': True, 'value': None})
        self.assertEqual(c.Result.failure('not_found', '').to_json(),
                         {'ok': False, 'error': {'code': 'not_found', 'message': '', 'refs': []}})
        self.assertEqual(c.ReportAction.from_json({'kind': 'report', 'summary': ''}), c.ReportAction(''))
        with self.assertRaises(c.ContractError):
            c.ReportAction.from_json({'kind': 'lookup', 'query': ''})

    def test_typed_result_decoder_preserves_value_and_rejects_mutable_or_lossy_output(self):
        data = {'ok': True, 'value': {'goal_id': 'g', 'revision': 1, 'epoch': 0}}
        result = c.Result.from_json(data, value_decoder=c.WorkRef.from_json)
        self.assertEqual(result.value, c.WorkRef('g', 1, 0))
        self.assertSameJSON(result.to_json(), data)
        self.assertEqual(c.Result.from_json(c.loads(c.dumps(result)), value_decoder=c.WorkRef.from_json), result)
        for decoder in [lambda data: data, lambda data: c.WorkRef('different', 1, 0), None]:
            if decoder is None:
                continue
            with self.assertRaises(c.ContractError):
                c.Result.from_json(data, value_decoder=decoder)
        def broken_decoder(data):
            raise RuntimeError('SENTINEL-secret-provider-error')
        self.assertCleanError(lambda: c.Result.from_json(data, value_decoder=broken_decoder))

    def assertCleanError(self, operation):
        try:
            operation()
        except c.ContractError as error:
            self.assertEqual(error.code, 'invalid_input')
            self.assertLessEqual(len(str(error)), 200)
            self.assertNotIn('SENTINEL', str(error))
            self.assertNotIn('SENTINEL', repr(error.__dict__))
            self.assertIsNone(error.__context__)
            self.assertIsNone(error.__cause__)
        else:
            self.fail('expected ContractError')

    def test_error_does_not_chain_decoder_exception_or_echo_malicious_input(self):
        operations = [
            lambda: c.loads('{"SENTINEL-secret":'),
            lambda: c.loads('{"SENTINEL-secret":1,"SENTINEL-secret":2}'),
            lambda: c.loads('"\\ud800-SENTINEL-secret"'),
            lambda: c.loads(b'"SENTINEL-secret-\xff"'),
            lambda: c.WorkRef.from_json({'goal_id': 'SENTINEL', 'revision': 1, 'epoch': 0, 'SENTINEL-secret': 0}),
            lambda: c.parse_model_action('{"kind":"verify","artifact_refs":[{"kind":"artifact","id":"SENTINEL"}]}', allowed_refs=[]),
        ]
        for operation in operations:
            self.assertCleanError(operation)
        self.assertNotIn('SENTINEL', str(c.ContractError('SENTINEL' * 1000)))

    def test_depth_cycles_and_platform_integer_limit_fail_boundedly(self):
        cyclic = []
        cyclic.append(cyclic)
        self.assertCleanError(lambda: c.dumps(cyclic))
        self.assertCleanError(lambda: c.loads('[' * 2000 + '0' + ']' * 2000))
        if sys.get_int_max_str_digits():
            digits = sys.get_int_max_str_digits() + 1
            self.assertCleanError(lambda: c.loads('1' * digits))
            huge = 10 ** digits
            self.assertCleanError(lambda: c.WorkRef('g', huge, 0))
            self.assertCleanError(lambda: c.JsonValue(huge))

    def test_examples(self):
        result = doctest.testmod(c, verbose=False)
        self.assertEqual(result.failed, 0)
        self.assertGreater(result.attempted, 0)


if __name__ == '__main__':
    unittest.main()
