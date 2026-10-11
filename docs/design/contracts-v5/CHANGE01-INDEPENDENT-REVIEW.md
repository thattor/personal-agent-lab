# CHANGE01/1 independent source review

Verdict for author source `076d4d20c170638b46f2e06f697e985e4476514b`: **REQUEST_CHANGES**. Native Sol reviewer authored the previously frozen TSK tests, but did not author this implementation. Astra authored source; Root owns connected fixtures and full regression. Frozen scope SHA256 is `fdd1fe51f1d8931bb900f21f4dd4b097c1e17ea5cab838b905553b22cbfaf62c`; reviewed tasks source SHA256 is `60e7ccb02279a374e3283297c8bce3fe23c7a0b42cd04ccba08a4ad6777d68d5`. Independent isolated integration HEAD is `a0b268da2a7a3390af66a73dd32217a62806f844`.

## Blocking finding independently reproduced

P1 — `pal/tasks_v5.py:1050` and `:1057`: cross-revision cessation validation compares linked reservation and Step identities without requiring their existing nonempty ID shape. A returned call with report Step, followed by change, then consistent replacement of SQL Step ID, wire step_id and call.step with empty strings is accepted by release. Similarly, a returned call without Step followed by change, then consistently blank reservation.id and call.reservation, is accepted. Actual result is success/queued and database mutation/slot release; expected is unavailable and unchanged database. Equality between malformed stored identifiers does not establish valid cessation evidence. The temporary-DB reproduction is retained in `evidence/operations/change01-20261009/tsk-review-linked-id-probe.py`; it touches no persistent application DB.

Root separately reported call ID/canonical identity and stored sources defects at the same validation boundary. Those reports support withholding approval, but this reviewer does not claim their execution as independent evidence. Repair and a fixed exact-source rereview remain outstanding.

## Independently executed verification

All commands used `/opt/homebrew/bin/python3.13 -E -s -B` from the isolated test worktree:

- `-m unittest discover -s tests -p test_tasks_change_v5.py -v`: 28 PASS, 0.769s.
- `-m unittest discover -s tests -p 'test_*change*_v5.py' -q`: 50 PASS, 1.001s.
- `-m unittest discover -s tests -p 'test_task*.py' -q`: 121 PASS, 1.567s.
- `evidence/operations/change01-20261009/tsk-review-linked-id-probe.py`: exit 0; both malformed-ID cases printed success and mutation, reproducing the blocker.

Reviewed exact production diff and frozen scope, including canonical replay before current authority, prior-grant narrowing, fresh origin/Condition identity, historical questions, latest-only claim, control inheritance, old lease/call/reservation/Step validation, pre-mint ownership guards, and unchanged same-revision release branch. Fixed tests exercise actual temporary SQLite owners and negative/rollback paths; they are not the sole approval criterion.

No full regression, real provider, semantic Primary authority, migration, live DB, operational adoption, or whole-product completion is claimed. Author full-suite results remain author evidence. Root owns final connected/demo/full-suite verification. Source, fixed tests and canonical documents were not edited by this review.

## Fixed exact-source limited rereview

**APPROVE** for author repair `b4baae24f226ccd4396cf723d8f31d03ef1e67b3`, source SHA256 `498b06ca6033c980bfdfe24b54195f247dbc7a46d267c67a1a54b0028f5c3e8f`. Local source integration HEAD before this note is `f2e080050ac608196cfba94665e1836667293c8b`. The original failing verdict and reproduction above remain retained.

Inspected the nine-line production repair against the original source: old call/reservation/optional Step IDs now pass the shared nonempty ID parser; call ID must equal its original C15 lease/index canonical identity; stored call sources parse as valid Refs and satisfy old required sources ⊆ call sources ⊆ old registered sources. These checks run before cleanup writes. The repair adds no current MEM gate, new admission, RUN change or transaction callback. Existing ended-status, latest pause/cancel/drain and admitted-call conflict behavior is preserved.

Independently reran using `/opt/homebrew/bin/python3.13 -E -s -B`:

- `-m unittest discover -s tests -p 'test_*change*_v5.py' -q`: **51 PASS**, 1.026s, including Root's one-method/nine-subcase integrity regression (SHA256 `717cf1f445b9590df3797e6a1f1289e251d24591f139b63babf1c7e36597ffa2`) and the unchanged fixed50.
- `-m unittest discover -s tests -p 'test_task*.py' -q`: **122 PASS**, 1.604s; covers important existing same-revision, control, ASK and completion paths.
- Original independent linked-ID probe: both cases now return bounded `unavailable`, with `mutated=False`. Thus each original independently observed blocker has a verified negative disposition, beyond the supplied tests.

No remaining blocker established in this limited repair review. Original scope review plus this exact repair review support approval of the preparation unit only. Full regression and final connected/demo evidence remain Root-owned and were not executed here. No live/provider/semantic-authority/product-activation claim follows. Fixed test/source files were only obtained through the authorized commits and were not edited by this reviewer.
