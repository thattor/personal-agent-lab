"""Independent ordinary-content regression; not part of fixed acceptance20."""
import unittest
import test_tasks_v5 as fixtures

class OrdinaryMarkerContent(unittest.TestCase):
    def test_report_and_release_text_remain_ordinary(self):
        for mode in ('report', 'release'):
            with self.subTest(mode=mode):
                f = fixtures.TaskTests()
                f.setUp()
                try:
                    claim = f.start()
                    marker = 'mock saved draft recovered'
                    if mode == 'report':
                        f.returned(claim)
                        step = f.value(f.begin(claim, {'kind': 'report', 'summary': marker}))
                        f.value(f.finish(claim, step))
                    else:
                        f.value(f.release(claim, reason=marker))
                    result = f.store.get_work({'goal_id': claim['work_ref']['goal_id']})
                    self.assertTrue(result.ok, result.to_json())
                finally:
                    f.doCleanups()
