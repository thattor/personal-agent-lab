REQUEST_CHANGES — independent native gpt-6.1-sol /root/int00_sol_review.
Reviewed exact f90da30427d4c9641890b7ad4945cfcc80c882d9, Root-owned TSK save hook only.
P2 tasks_v5.py420-429: stored Step.index=False passed index0 comparison (False==0)
and authorized a save despite corrupt internal metadata; expected unavailable.
P2 tasks_v5.py408-410,439: action.content=1 returned conflict instead of invalid_input;
input keys/refs were validated but content/media_type were not.
Independent targeted36 PASS did not cover those probes. Read-only temporary-DB
probes confirmed both, rolled back. No additional blocker for connection/TX ownership,
lease/control/source checks, conservative call dependencies or compose finish refusal.
ART module/connection/full acceptance not covered.

Root reproduced both in hook-review-before.log. Root now validates the user action
with the existing shared C12 parser, and strictly validates saved Step metadata
before equality checks. Expanded malformed content/media/index/status/result/error
cases pass36 in hook-review-after.log. Independent rereview APPROVE at exact 1be000aca0e169805f182d9e13bb019cb5740b0e.
Original independent probes now return unavailable and invalid_input respectively;
36 targeted tests PASS0.183s. No additional blocker. ART body/connection remain outside
that review. Root full543 PASS23.484s/exit0 at the same source.
