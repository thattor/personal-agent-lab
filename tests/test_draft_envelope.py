import json
import unittest
from pal.draft_envelope import decode_draft, EnvelopeRejected


class DraftEnvelopeTests(unittest.TestCase):
    def decode(self, payload, bound=80):
        return decode_draft(json.dumps(payload, ensure_ascii=False), bound)

    def test_three_proposals_are_data_not_completion(self):
        for payload in [
            {"kind":"complete", "content":"こんにちは", "citations":[]},
            {"kind":"needs_input", "question":"日時を教えてください", "citations":[]},
            {"kind":"incomplete_preview", "content":"日時：[未定]", "missing":"日時", "citations":[]},
        ]:
            self.assertEqual(self.decode(payload), payload)

    def test_unknown_authority_fields_and_wrong_types_rejected(self):
        base={"kind":"complete", "content":"draft", "citations":[]}
        for payload in [dict(base, goal_id="other"), dict(base, status="pass"),
                        dict(base, kind="tool_call"), dict(base, content=7),
                        dict(base, citations={}), {"kind":"complete","content":"draft"},
                        dict(base, content=" "), []]:
            with self.subTest(payload=payload), self.assertRaises(EnvelopeRejected):
                self.decode(payload)

    def test_utf8_bound_and_invalid_unicode(self):
        self.decode({"kind":"complete","content":"あ"*3,"citations":[]}, 9)
        with self.assertRaises(EnvelopeRejected):
            self.decode({"kind":"complete","content":"あ"*3,"citations":[]}, 8)
        with self.assertRaises(EnvelopeRejected):
            decode_draft('{"kind":"complete","content":"\\ud800","citations":[]}',80)
        for content in ["x\x00y", "\ufeffdraft"]:
            with self.assertRaises(EnvelopeRejected):
                self.decode({"kind":"complete","content":content,"citations":[]})

    def test_json_ambiguity_and_non_json_rejected(self):
        for raw in ['{"kind":"complete","kind":"needs_input","content":"x","citations":[]}',
                    '{"kind":"complete","content":NaN,"citations":[]}',
                    '```json\n{}\n```', '{} trailing', 'null', '"done"']:
            with self.subTest(raw=raw), self.assertRaises(EnvelopeRejected):
                decode_draft(raw,80)

    def test_citations_syntax_only_and_not_canonical_tokens(self):
        payload={"kind":"complete","content":"draft","citations":[{"source_id":"r1","quote":"日時"}]}
        self.assertEqual(self.decode(payload),payload)
        for cite in [{"source_id":"r1","quote":"日時","usable":True},
                     {"source_id":"","quote":"x"},{"source_id":"r1","quote":False}]:
            with self.assertRaises(EnvelopeRejected):
                self.decode(dict(payload,citations=[cite]))
        with self.assertRaises(EnvelopeRejected):
            self.decode(dict(payload,citations=payload['citations']*51))

    def test_question_and_preview_limits(self):
        for payload in [{"kind":"needs_input","question":" ","citations":[]},
                        {"kind":"needs_input","question":"x"*2001,"citations":[]},
                        {"kind":"incomplete_preview","content":"draft","missing":"","citations":[]}]:
            with self.assertRaises(EnvelopeRejected): self.decode(payload)
        with self.assertRaises(EnvelopeRejected): decode_draft(' '*40001,80)
        for bound in [True,0,-1,"80"]:
            with self.assertRaises(ValueError): decode_draft('{}',bound)

if __name__ == '__main__': unittest.main()
