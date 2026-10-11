"""Independent goal-uniqueness probes for PRI01-WIRE exact source."""
import copy
import unittest
import test_primary_wire_v5 as fixed
from pal.contracts_v5 import dumps
from pal.primary_wire_v5 import parse_primary_output,PrimaryProposalError

class PrimaryWireReview(unittest.TestCase):
    def parse(self,candidates):
        return parse_primary_output(dumps({'reply':'通常の返答','proposal':{'kind':'none'}}),current_record_ref=fixed.R,candidates=candidates,allowed_record_refs=[fixed.R,fixed.OLD])
    def test_each_goal_once_across_revision_or_epoch(self):
        for field in ('revision','epoch'):
            with self.subTest(field=field):
                other=copy.deepcopy(fixed.W);other[field]+=1
                candidates=[fixed.candidate(),fixed.candidate(other)]
                before=copy.deepcopy(candidates)
                with self.assertRaises(PrimaryProposalError) as caught:self.parse(candidates)
                self.assertEqual(caught.exception.code,'invalid_input');self.assertIsNone(caught.exception.__context__)
                self.assertEqual(candidates,before)
    def test_distinct_goal_same_revision_epoch_is_legitimate(self):
        other={**fixed.W,'goal_id':'other-goal'}
        self.assertEqual(self.parse([fixed.candidate(),fixed.candidate(other)]),{'reply':'通常の返答','proposal':{'kind':'none'}})
