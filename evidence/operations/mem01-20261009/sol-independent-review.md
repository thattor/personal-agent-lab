# Independent Sol6.1 review

APPROVE — exact head013bf52c5a8ec079614071f251109a9413b08a60,
base7a12a111ff1a21b796269a9e2f28bd04a535146d. Native gpt-6.1-sol in separate
`/root/int00_sol_review`, not a code author. Read-only; no file changes.

No blocking code defects found against frozen MEM01/1. Verified actual
append→search→intake→stop composition; atomic queued epoch increments and events;
fresh-intake/current-read denial; unchanged historical create receipt; complete
origin/context indexing; unsupported-state rejection; sanitized replay without an
unsanitized ledger; strict callback results; rollback across both stores; structured
replay namespaces.

Independently executed with /opt/homebrew/bin/python3.13 -E -s -B -m unittest
discover -s tests -p PATTERN -v in fresh temporary databases:
test_memory_v5.py19 PASS; test_intake_transactions_v5.py7 PASS;
test_memory_intake_pipeline_v5.py5 PASS; test_intake_v5.py14 PASS.

Reviewer-reported additional probe (no artifact saved): two distinct source stops
increment a dependent Goal epoch once each; duplicate dependencies deduplicate;
opaque keys replay without extra events; original intake receipt keeps epoch0.

Limits: callbacks are trusted host code; premature COMMIT cannot be retroactively
rolled back. Other-state invalidation, notes, verification dependencies, real
runtime and full CT-20/product acceptance remain unmet. Root owns full regression.
