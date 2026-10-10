"""Independent PRI phase/intent integrity: actual committed owner effect survives corruption."""
import unittest
import test_primary_host_v5 as fixtures


class PrimaryPhaseReview(unittest.TestCase):
    def test_applying_intent_cannot_be_downgraded_into_interruption(self):
        for phase in ('pending', 'preparing', 'admitted', 'returned'):
            with self.subTest(phase=phase):
                f = fixtures.PrimaryHostTests()
                f.setUp()
                try:
                    f.proposal = {'kind': 'new_work', 'brief': f.draft()}
                    create = f.tasks.create
                    committed = []

                    def lost_response(*args, **kwargs):
                        committed.append(f.ok(create(*args, **kwargs)))
                        raise RuntimeError('owner response lost after commit')

                    f.tasks.create = lost_response
                    turn = f.submit()
                    f.run_turn(turn, 'pending')
                    self.assertEqual(len(committed), 1)
                    self.assertEqual(f.conn.execute(
                        'SELECT phase FROM v5_pri_turn WHERE id=?', (turn,)).fetchone(), ('applying',))
                    f.conn.execute('UPDATE v5_pri_turn SET phase=? WHERE id=?', (phase, turn))
                    f.restart()
                    lookups = []
                    lookup = f.tasks.get_create_by_key

                    def observed(request):
                        lookups.append(request)
                        return lookup(request)

                    f.tasks.get_create_by_key = observed
                    before, used = f.snapshot(), f.used()
                    outcome = f.ok(f.host.recover_turns())
                    self.assertEqual(outcome, {'interrupted_turn_ids': [],
                        'committed_turn_ids': [], 'held_turn_ids': [turn]})
                    self.assertEqual(f.snapshot(), before)
                    self.assertEqual(f.used(), used)
                    self.assertEqual(lookups, [])
                    self.assertEqual(len(f.calls), 1)
                    self.assertEqual(f.current(committed[0]['work_ref'])['state'], 'queued')
                finally:
                    f.doCleanups()
