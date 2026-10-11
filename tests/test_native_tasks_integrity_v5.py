"""PRI03 native admission provenance survives partial storage downgrade.

Actual fresh owners; typed fixture endings do not prove native transport.
"""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_expert_fixtures_v5 import NativeFixture


class NativeAdmissionIntegrityTests(unittest.TestCase):
    def test_retained_native_admission_prevents_mock_downgrade_and_action_replacement(self):
        n = NativeFixture(self)
        for result in (n.admit(), n.enter(), n.end()):
            self.assertTrue(result.ok, result.to_json())
        n.f.conn.execute("UPDATE v5_tsk_call SET native='mock',native_hash=NULL WHERE id=?", (n.call_id,))
        n.f.conn.execute('DELETE FROM v5_tsk_native WHERE call_id=?', (n.call_id,))
        self.assertEqual(n.f.conn.execute("SELECT COUNT(*) FROM v5_intake_replay WHERE command='admit_native_call' AND key=?",
                                         (n.call_id,)).fetchone()[0], 1)
        before = n.f.snapshot()
        operations = (
            ('get_call', lambda: n.t.get_call({'call_id': n.call_id})),
            ('begin_step', lambda: n.begin({'kind': 'report', 'summary': 'different from original native bytes'})),
            ('get_native_output', n.output),
        )
        for name, operation in operations:
            with self.subTest(operation=name):
                result = operation()
                self.assertFalse(result.ok, result.to_json())
                self.assertEqual(result.error.code.value, 'unavailable')
                self.assertEqual(n.f.snapshot(), before)
                self.assertFalse(n.f.conn.in_transaction)


if __name__ == '__main__':
    unittest.main()
