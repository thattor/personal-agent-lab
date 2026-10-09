# PRI01-TSK/1 implementation

Source base `da321e1`; source ownership is limited to tasks_v5.py. This implements
Root's frozen prerequisites, not Primary inference, semantic routing, provider
qualification or product activation. The later Opus refinement report was not
received and is not claimed as acceptance. Independent tests precede this source.

## Decisions

`list_candidates` validates its closed input, opens one owned read transaction,
selects latest revisions across sessions including terminals, and orders by latest
Goal-bound event sequence then Goal ID. It validates Brief/Grant, required and
registered record dependencies and existing question invariants. Summary/question
prefixes preserve UTF-8 codepoints; IDs and dependencies never truncate. Full
registered dependencies are gated on the same connection. Ordinary source refusal
withholds all text; exceptions, protocol errors, writes and transaction replacement
fail closed. The dedicated guard distinguishes these outcomes, which the older
shared source helper intentionally collapses. Caller transactions are not taken
over; BaseException cleans the owned transaction and propagates.

`get_create_by_key` and `get_control_by_key` read the actual C03.create/control
namespaces without gate or current authority checks. They validate canonical
input, strict successful output and immutable owner evidence. Create matches
revision1/session/origin/Expert/Grant and original draft descriptions/checks to
minted Conditions. Change matches the next revision and narrowed saved Grant;
answer matches immutable question/answer linkage; complete matches the saved TSK
result event and artifact set, without private VER SQL or current VER eligibility.
Historical human input epoch is not treated as the resulting epoch. Neither method
commits, rolls back or refreshes caller/configuration state.

Workless `{key,kind:model,role:primary}` requires the real registered ready HOST.
It spends only the existing shared host model counter; Step zero is permitted and
no Goal usage or lease is fabricated. One TSK table binds reservation to session
and original reserve key. Replay and consume validate the full nullable row shape,
original reserve receipt, original session and any saved consume binding before
returning success. Same binding replays; another binding conflicts; foreign session
is denied. Premint precedes writes. No refunds or inference entry follow from a
reservation receipt.

## Test provenance and limits

The initial fixed test hash was
`9f7ca8f982cb7fe23d66a529ff6368ce6755b65b90cc09647637cf4a54b22b24`.
One fixture queried the nonexistent namespace `create` rather than actual
`C03.create`, producing None before exercising assertions. Independent test owner
corrected only those three SQL strings at `2d4a374`; revised hash is
`1819ea49af005acfe414e1c98f11357ee2bd0efb1629776daaa60cace17bf1a9`.
Original 23 PASS / 1 fixture error is retained in `/private/tmp/pri-tsk-first.log`.
The corrected fixed24 passed. No author test edits or weakened assertions.

The first related195 run retained one old unavailable expectation for workless
Expert. The adopted strict workless branch and fixed24 require invalid_input;
this mismatch was reported to the test owner, not worked around in source.
Final results are recorded below once independent input corrections are applied.

Trusted collaborators are not sandboxed. A collaborator's committed external
writes cannot be undone by a savepoint. No live DB migration, Primary callback,
full flow, provider call, independent review or whole-product acceptance is claimed.
Root owns independent integration/full regression; a separate context reviews
these exact source bytes.

## Final candidate verification

Independent legacy-test correction `ff4bbb64504bcb88c241019aa3bf90caace8993c`
changes only the obsolete workless Expert expected error, preserving all other
assertions. Both test-owner corrections are dependency commits, not author edits.

- `/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_tasks_primary_v5.py -v`:
  24 PASS, exit 0; log `/private/tmp/pri-tsk-final24.log`.
- Same Python runtime, `unittest.TestLoader.discover` for all `test_task*_v5.py`
  and `test_recovery*probe*.py`: 195 PASS, 3.303s, exit 0;
  log `/private/tmp/pri-tsk-final195.log`. This includes fixed24 and prior recovery,
  completion, ASK, CHANGE, artifact binding and execution rights regressions.
- `git diff --check`: exit 0.

Final source SHA256:
`226eab3ad2e92a6a056efef537b5f4e88f8a485aff598cb9da49d233ae4a6957`.
The separate reviewer owns additional complete-receipt, SQL-fault and typed binding
corruption probes. Candidate test success does not stand in for that review.
