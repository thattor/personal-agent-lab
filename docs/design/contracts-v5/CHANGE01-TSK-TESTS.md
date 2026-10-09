# CHANGE01/1 fixed TSK acceptance tests

Native Sol6.1 test author `int00_sol_review`, independent of native Astra source
implementation. Frozen base `e0fbdc23602e2a0cf6dc8f2c0590aaae459619a8`;
unchanged source baseline `c49bb005ab9fe18b53e27934a537934325dd26a7`.
CHANGE01-SCOPE SHA256:
`fdd1fe51f1d8931bb900f21f4dd4b097c1e17ea5cab838b905553b22cbfaf62c`.

`tests/test_tasks_change_v5.py` has **28 methods / 97 explicitly executed
subcases** on the baseline. It composes `test_tasks_ask_v5` through a module import,
so the existing TestCase is not separately discovered. Each fixture creates actual
temporary SQLite MEM/TSK, with no old/live DB or provider. A labeled deterministic
trusted host binds the saved correction to the supplied DraftBrief; this does not
prove natural-language Primary or issue/path authorization.

Coverage follows the frozen owner seam rather than a new implementation:

- Closed C10 command, strict shared parser cases, repository rejection, same-key
  canonical replay before current authority, changed epoch/input conflict, missing
  Goal, stale revision, epoch-tolerant fresh control, terminal rejection and origin
  reuse. Same text with new origin can advance. Origin/Condition freshness is
  Goal-local; an unrelated Goal does not create a global registry restriction.
- Queued/waiting/paused/running transitions, exact receipts, new revision/epoch,
  unchanged Goal/session/expert, formal Condition IDs and exact new Brief, required
  source index, historical superseded readback and empty new execution/link sets.
  One state event binds the new WorkRef and origin to the stored work session.
- Prior-ordered grant intersection under narrowing then host expansion, zero and
  below-consumed headroom, unchanged Goal/host counters and no allowance reset.
- Open/answered/closed question history, only-open supersession, immutable C04/
  answer replay and no link transfer. Latest superseded/malformed waiting/question
  rows fail closed.
- Real source stop before/after correction: independent old-only replacement,
  explicit reused/new dependencies, terminal required-source failure, shared/new
  invalidation. Same-connection source gate outcomes preserve not_found/denied/
  unavailable with unchanged DB/key.
- Admitted call holds slot across multiple changes, pause/cancel/source-stop;
  returned/raised/not_entered may settle without Step after fencing. Latest intent
  wins even for old failed outcome. Old started Step abandonment, old release
  immutable replay, strict lease identity, latest-only claim and stale old
  admission/reservation/Step authority.
- Cross-revision call/reservation/Step corruption (status, WorkRef, bounded index,
  role/binding, missing reservation, SQL versus wire/call association, bool wire
  index, future epoch and malformed Step fields) retains slot and all DB rows.
- Condition/event prewrite mint transaction loss, reopened TX, writes, ordinary
  exceptions and BaseException; within-new/prior/history Condition collisions;
  revision/epoch overflow before mint. First-owned-write, event and replay
  post-write faults roll back while TX ownership remains intact, with normal retry.

## Executed evidence and limits

Command:

```sh
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_tasks_change_v5.py -v
```

**RED, exit1: 28 methods, 109 assertion failures, 0 errors.** Scope and test hashes,
counts and the exact command are in `tsk-tests-sol-summary.json`; the original
verbose bytes are retained in `tsk-tests-sol-red.raw.log.gz`; the readable
`tsk-tests-sol-red.log` normalizes trailing whitespace only. The public summary and readable log are under
`evidence/operations/change01-20261009/`; the exact gzip remains locally retained.
Public log paths are normalized to `<repo>`; original hashes remain in verification. A second identical-pattern loader with a
counting TestResult confirmed the 97 subcases, with no duplicate fixture discovery.
AST parse and staged whitespace validation pass separately from behavioral RED.

The baseline parser lacks C10.change and rejects otherwise valid requests as
invalid_input. Negative shared-parser/no-write checks execute before their same-key
valid retry fails. Positive change setup fails before the later cross-revision,
mint and post-write assertions are reachable. The fault tests explicitly require
that the injection actually triggered; an unrelated early rejection cannot pass as
rollback proof. Zero test errors supports fixture construction but is not a claim
that every later assertion has executed or that the source is implemented.

A preliminary parser test incorrectly treated a generic artifact Ref in
DraftBrief.context_refs as invalid syntax. Inspection showed shared DraftBrief
permits generic Refs; the case was corrected to an actual invalid Ref enum before
freeze. Unsupported owner kinds remain a source-gate outcome, not an invented
parser/permission rule. This test-author correction is not a product defect.

Root owns actual MEM/TSK/RUN/ART/VER/C14 integration, ordered two-connection races,
retained RUN tails, historical ART/VER reader proof, executable demo and full
regression. Separate Sol owns RUN fixed tests. No actual model, live DB migration,
recovery or whole-product acceptance is claimed. Source author receives exact
immutable test bytes and must not weaken expectations; a demonstrated fixture or
contract issue must return to Root for disposition. Existing branches/work were
preserved; only this test, note and uniquely named test evidence were added.
