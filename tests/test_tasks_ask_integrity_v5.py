"""Independent review regression for the new pre-write question-ID callback."""
import unittest
import test_tasks_ask_v5 as fixture


class AskMintIntegrityTests(unittest.TestCase):
    def test_question_id_callback_cannot_move_owned_writes_outside_transaction(self):
        for action in ('COMMIT', 'ROLLBACK', 'COMMIT_BEGIN', 'ROLLBACK_BEGIN', 'WRITE'):
            with self.subTest(action=action):
                f = fixture.TaskAskTests()
                f.setUp()
                try:
                    f.stage()
                    before = f.dump()
                    original = f.tasks._id_factory

                    def mint(prefix):
                        if prefix != 'question':
                            return original(prefix)
                        if action == 'WRITE':
                            f.conn.execute("UPDATE v5_tsk_host SET used=used+1 WHERE kind='model'")
                        else:
                            f.conn.execute(action.split('_')[0])
                            if action.endswith('_BEGIN'):
                                f.conn.execute('BEGIN IMMEDIATE')
                        return 'synthetic-question-id'

                    f.tasks._id_factory = mint
                    f.error(f.tasks.ask(f.request), 'unavailable')
                    self.assertFalse(f.conn.in_transaction)
                    self.assertEqual(f.dump(), before)
                    f.tasks._id_factory = original
                    receipt = f.value(f.tasks.ask(f.request))
                    self.assertEqual(receipt['state'], 'waiting_input')
                finally:
                    f.doCleanups()


if __name__ == '__main__':
    unittest.main()
