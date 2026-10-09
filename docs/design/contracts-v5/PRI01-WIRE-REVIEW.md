# PRI01-WIRE independent review

REQUEST_CHANGES against exact CO SWE-2 High source SHA256 `135fcafafd89697637a8f8a3e6b067ca926688e45b4f41c476955429473342d6` (8625bytes), completed task7df39c9c22664ba6b1265a68f9200f27. Separate native Sol reviewer, neither source author nor fixed25 author. Rootbasec7f6f51; source is an unchanged uncommitted readonly dependency. No CO state/model/network operations.

P2 — candidate uniqueness checks full WorkRef instead of Goal identity (`primary_wire_v5.py:145–148`). Two plain valid candidates for the same Goal with different revision, or different epoch, both pass even with `{kind:none}`. Frozen trusted input says each Goal appears once. Expected invalid_input; actual normalized success. Distinct Goals with equal revision/epoch remain legitimate. Independent probe freezes both negative cases and this positive control; candidates are not mutated.

Independent commands under `/opt/homebrew/bin/python3.13 -E -s -B`:

- `-m unittest discover -s tests -p test_primary_wire_v5.py -q`: unchanged fixed25 PASS0.007s.
- `-m unittest discover -s tests -p test_primary_wire_review_v5.py -v`:2 methods, duplicate2subcases FAIL, distinctGoal positive PASS,exit1,0.001s. Log `/private/tmp/pri01-wire-independent-red.log`.

Static review inspected every source function against the frozen grammar: trusted exact Ref/plain candidate shapes, question revision and withholding, strict public DraftBrief context membership/duplicates, exact snapshot target, current record for answer/change, future-tag unavailable dispositions, UTF8/raw/reply size checks, duplicate/nonfinite/deep JSON via shared loads, normalized copying, and source-free errors raised after ContractError handlers. No additional concrete blocker found. No owner authority/source usability/intent/freshness is inferred from parsing. These remain host obligations; fixed25 and source review are not Primary activation, provider proof or whole product acceptance. Final narrow approval awaits exact repaired source and unchanged independent negative/positive probes. Only probe and this note are committed; fixed25/source/shared docs are not edited.
