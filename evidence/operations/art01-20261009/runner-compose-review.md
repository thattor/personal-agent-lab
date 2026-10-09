Independent native Sol6.1 preliminary review of uncommitted Root RUN patch found P2:
save unavailable x3, then get_by_key not_found produced state=failed/calls1/finishes0.
Root independently added a failing regression: 8 tests, 1 failure at assertFalse(result.ok).
Cause: routing a receipt-recovery error through permanent save-input failure handling.
Corrected only post-unavailable recovery failure to yield_or_retain, preserving latest
control and ended-output occupancy. No get_by_key on input conflict, no model retry.
Next check: missing as well as unavailable receipt, same runner reentry calls=1.
Formal exact-commit independent rereview and actual ART connection remain pending.
