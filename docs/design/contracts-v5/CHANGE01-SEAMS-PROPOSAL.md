# CHANGE01/1 seams proposal — not adopted

Source reviewed: `b844706eb303f759f14cbd7857dcf86b44f3de99`, including `AFTER-ASK01-PROPOSAL.md`. Anchors below refer to that commit, not this branch. This note proposes the next bounded correction connection; it authorizes no implementation or activation.

## Closed command and authority

Keep C10's public request exactly `{key,work_ref,command:{kind:"change",brief:DraftBrief,origin_record_ref:Ref}}`; reject extra keys, non-record origin and invalid DraftBrief. As a human control, compare Goal/revision and tolerate epoch advancement; same-key replay precedes current authority checks, while a new key targeting an older revision is stale. Terminal work requires a new Goal. These are existing obligations: `PAL-contracts-v5.md:46–51,115–118,157–177`.

Recommended host seam: `control(request, *, request_scope=None)`, with a typed `Grant` mandatory only for change and forbidden for other commands. No grant is accepted inside model JSON. Derive the new immutable grant by intersecting the previous revision's stored grant, current host grant and trusted request scope; canonical replay identity includes the supplied scope, as create already does. Never widen capabilities, repositories or limits. Preserve zero budgets and cumulative usage. Whether this explicit scope argument is necessary, versus preserving the prior grant exactly, is an **Opus adoption decision**; the explicit seam reuses intake's existing distinction between host scope and model proposal (`intake_v5.py:102–110,322–350`).

Repository membership is enforceable now; natural-language authorization of a changed purpose, issue or path is not proved by that check. The host must bind the proposed difference to the saved correction record before invoking change. A mock host can supply this binding, but must not claim a Primary interpreter or an issue/path authorization engine. Freeze this host obligation rather than adding a generic validator framework.

## Immutable revision ownership and transaction

TSK remains sole owner. Reuse `v5_intake_work`'s `(goal_id,revision)` primary key and revision-scoped source index (`intake_v5.py:29–44`). In one `BEGIN IMMEDIATE`: replay check; latest target/nonterminal/grant validation; same-connection gate for new origin and explicit context; fresh unique Condition IDs; insert new Brief/grant/origin with preserved Goal/session/expert; supersede old open question; register new dependencies; save one state event and result receipt. Increment revision and epoch with overflow refusal. Mint callbacks need the same transaction/savepoint guard learned from ASK; exceptions, interruptions and event failure must leave no partial revision or burned key.

Reuse strict parsers, `_intersect`, source gate, event/replay helpers; extract only a small Brief/Condition construction helper if duplication warrants it. Do not call create and discard its new Goal. No new owner or alternate ledger is needed. Old Brief, grant, source and Step data remain history. New current artifacts, Steps, questions and pending-answer links start empty; explicit available old record context may be selected, but no automatic carry-forward. C10 requires `superseded` questions: adopt that one status deliberately, rather than disguising supersession as answered. Old get_work remains historical (`tasks_v5.py:265–316,813–848`).

## Execution and latest control

A revision insert exposes two concrete hazards: claim selects every queued row, including historical revisions (`tasks_v5.py:248`); release rejects any nonlatest revision through `_current` (`1030–1032`). Fixing only change would strand or rerun work.

Proposed minimal state representation: running change publishes the new revision as running with drain set and carries pause intent, while the occupied lease remains bound to its old revision. No new authority is granted: `_authority` requires latest WorkRef AND lease revision (`130–158`). An ended old-owned lease may release against its stored Goal/revision; examine calls/abandon started Steps on that old revision, but select destination state and flags from the latest revision. Admitted calls still forbid release. Newest cancel/pause outranks draining; old failure must not fail the replacement. Clear latest drain only when closing the occupied slot. Additional changes can advance the latest revision without replacing the old lease. Claim without a lease must select only latest queued revisions; retained-lease claim may return old diagnostics, never permit inference under stale authority (`221–263,1019–1058`).

Without a lease, queued/waiting changes become queued; paused remains paused. The exact externally visible running/draining projection, including pause-request precedence, needs Opus confirmation against C10/C13. Do not introduce a new state enum or a pending-change engine merely to avoid this decision.

## Budgets, history and stopped sources

Usage is already Goal-wide and host-wide (`tasks_v5.py:185–206`): revision creation neither refunds reservations nor resets consumption. Narrowing limits below used yields zero headroom. Old receipts replay their original result, not today's state. A new key on the current revision means a new requested correction even if brief text matches; freeze this explicitly. Late ART/VER/Step acceptance is stale; historical ART/VER bodies remain governed by their own public readers, never direct SQL rewriting.

Stop invalidation already scans only the latest revision (`1061–1104`). Retain this current-work rule: stopping an exclusively old dependency must not invalidate an unrelated replacement, while shared/new dependencies fence the latest work. Old lease remains fenced by revision even if its old source stops. Historical bodies must still fail model/verification reuse through owner gates. Completed-history behavior remains unchanged. Do not restore any stopped source through a correction, answer carry-forward or replay.

## Essential acceptance before adoption is implemented

- Real MEM→TSK correction: queued, waiting/open, paused, running and terminal; exact new Brief/IDs/origin/grant, old immutable readback and empty new artifact/answer sets.
- Replay after release/stop/another change; changed scope/input conflict; new-key stale target; strict types, negative/zero limits, overflow and failed source gates.
- Two-connection change versus call admission, finish, ART save, VER save and complete: commit order decides; no late result adopts the old revision.
- Old admitted call keeps slot; ended old lease closes across one or multiple revisions; latest pause/cancel/source-stop wins; different lease denied; historical queued row never reclaimed.
- Budget usage persists, including failed reservations; no fresh allowance per revision. Event/revision/question/source/receipt rollback on injected failures and BaseException; callback transaction-loss detection without claiming rollback of a hostile COMMIT.
- Old-only versus shared stopped sources; old answer/question never silently enters new C12; current artifact/verification history cannot complete replacement.

No tests were rerun: this is source-backed preparation only. PRI routing, C03 attachment, MEM correction, recovery, operation/provider execution, UI and product activation remain outside this proposal. Root owns adoption and a later exact scope.
