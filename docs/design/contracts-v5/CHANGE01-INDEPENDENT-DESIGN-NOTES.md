# CHANGE01 independent design-pool notes — not adopted

Read-only native Sol critique, source pinned to
`a7562f82192e478d5184947ebb38daa4ff3b38b1` through `git show`. Root checkout had
advanced to `8fb2ad9`; these source anchors refer only to the pinned commit.
Read CHANGE01-SEAMS-PROPOSAL.md at that commit (SHA256
`8a328e7a558e54d4d844a72a830b19ff7492b8cf17bd1f4435f1753e35e9a309`).
This is preparation for the required Opus consultation, not its replacement,
implementation approval or a freeze. No tests, provider calls or DB writes ran.

## Concrete gaps to settle before freeze

1. **Old waiting history cannot simply keep its state under present ASK invariants.**
   Counterexample: rev1 waiting_input/open question → change rev2 queued, rev1
   question superseded. Even after admitting that new question status,
   `_questions` rejects waiting_input without an open question
   (`tasks_v5.py:832,845–852`). Both historical C02 and C04 key lookup call this
   reader (`:305–316,916–937`). Thus “old immutable readback” and historical ask
   receipt replay break if only the question status changes. Opus must explicitly
   scope live waiting/open invariants to the current revision, or choose another
   precise historical projection. Preserve strict shape/link validation for all
   revisions. Do not label genuine current waiting corruption as ordinary history.
   Also freeze whether only unresolved old questions become superseded; previously
   answered links should remain historical answers, not be silently erased.

2. **Old-slot cleanup needs an explicit strict ended-call condition.**
   Existing release only tests `status == admitted` (`tasks_v5.py:1034–1044`);
   an unknown/corrupt status can otherwise pass. In a multi-change chain the
   cleanup must inspect old lease/revision rows, validate recognized statuses,
   exact bound WorkRef/index/Step linkage, and refuse uncertain/unended calls.
   A changed latest revision must not turn arbitrary old call rows into ended
   evidence. Minimal adversarial sequence: rev1 call owned → change rev2 → pause
   → change rev3 → call row has unknown status → release rev1. The proposal's
   “admitted calls forbid release” alone does not close this uncertainty.
   When legitimately ended, rev1 started Steps are abandoned while rev3's newest
   pause/cancel/drain state decides the destination. Old `failed` must not fail
   rev3. No external cancellation or process cessation is inferred.

3. **Trusted scope proves a ceiling, not the correction's meaning or origin.**
   Intersecting previous grant/current host/request scope is mechanically sound
   (`intake_v5.py:102–110,330–332`; contract `:45–46,118`). Explicitly choose
   previous-revision ceiling versus original-Goal ceiling: after rev2 narrows a
   limit to zero, rev3 scope asking for the original allowance must stay zero if
   “change never expands” is sequential, as proposed. Typed scope and repository
   membership do not bind changed issue/path/purpose to the correction record.
   Freeze the trusted host obligation and demonstrate it without claiming PRI.
   Decide whether unavailable/stopped *old* origin blocks interpreting a correction
   or stored prior Brief/grant plus a fresh authenticated correction suffices.
   The latter fits old-only source stops not fencing replacement, but is a
   deliberate authority choice; do not invent a mandatory old-source gate or
   silently pretend the new-origin gate proves original-request authorization.

## Agreements that need exact acceptance examples, not more machinery

- Replay identity must include full request plus trusted change scope, before
  current authority; epoch tolerance applies to fresh authority, not canonical
  input equality (`PAL-contracts-v5.md:49,51`). Same key after another change or
  stop returns its original receipt. Refreshing epoch under that same key changes
  input and conflicts. A fresh key on a stale revision is stale. New key on the
  current revision can intentionally create another correction even if text
  matches; freeze that distinction.
- Latest-only claim selection is necessary (`tasks_v5.py:248`), independently
  of old-row history state. Retained old lease may return old diagnostics but
  `_authority` cannot execute under it (`:149–158`). Existing RUN sends the old
  WorkRef back on release (`mock_runner_v5.py:150–152,475–479`); support that
  request rather than requiring RUN to guess the newest revision. C13 release
  receipt should describe latest state/WorkRef; its immutable replay must not
  later rewrite a newer revision.
- Multiple changes must carry latest pause intent even when represented as
  running+drain, and cancel remains terminal. Example to freeze: rev1 admitted →
  change rev2 → pause rev2 → change rev3 → shared-source stop → returned rev1 →
  release. Expected latest paused/terminal intent wins, epoch advances exactly
  for adopted invalidations, slot closes once; no rev1 or rev2 is reclaimed.
- Goal-wide usage already survives revisions (`tasks_v5.py:185–206`); new limits
  below used produce zero headroom. New revision starts with no artifact set,
  Steps, pending links or implicit old-source registration. Current-only stop
  selection exists (`:1074–1100`): old-only stop does not fence replacement;
  shared/new stop does. Historical owner read gates still control reuse.
- New condition IDs are host-issued and immutable in their Brief. Define collision
  handling at the actual revision construction boundary; no global cross-Goal
  registry or new authority framework is warranted by this slice.

Limits: no complete alternative design, implementation or adoption was produced.
Opus must resolve these choices before Root freezes scope. The blocked external
payload had no started call; this local note neither retries it nor grants egress
permission. Root owns canonical decisions, integration and eventual acceptance.
