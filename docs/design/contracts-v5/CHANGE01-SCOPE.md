# CHANGE01/1 — frozen local mock implementation scope

Root/Sol freezes C079 after actual Opus review the ASK01 final design review (ASK ALIGNED / CHANGE READY_TO_FREEZE) and separate Astra actual-source reconciliation `04f08d48653b23bd4cb2fde878bafccfbebc2e3e`. Source baseline `c49bb005ab9fe18b53e27934a537934325dd26a7`; code is unchanged by the freeze. Contract ID/version **CHANGE01/1**, shared wire **PAL-contracts-v5**, affected **C02/C10/C13/C14**, fixed examples below. Candidate notes remain history; this file is operative for this slice. Opus reports connection-test truncation and unsupplied RUN/ART/VER/MEM sources; it executed no tests. Actual-source reconciliation closes the specified reader/RUN questions only.

## Closed API and authority

`TaskStore.control(request)` remains unchanged. Exact request `{key,work_ref,command:{kind:"change",brief:DraftBrief,origin_record_ref:Ref}}`. Existing strict DraftBrief/create context rules; origin must be record. Extra grant/scope/limits/authority fields give invalid_input. Receipt exactly `{work_ref:<new>,state:queued|paused|running,control_status:none|pause_requested|draining}`. No new public method or model wire type.

Trusted caller saves correction via MEM append, binds origin to that saved correction, and lists **every reused/derived record** in Brief.context_refs, including old origin/answers when their content contributed. TSK does no meaning inference: it validates stored target/revision, strict shape, repository grant and same-transaction source availability. This is the existing trusted-host obligation, demonstrated by a labeled deterministic host fixture; neither arbitrary model JSON nor Grant intersection proves semantic authority. PRI/issue/path authorization remains unimplemented.

`new_grant = _intersect(current_host_grant, latest_prior_grant)`: preserve prior ordering, intersect capabilities/repositories, minimum of each limit (`intake_v5.py:102–110`). Never substitute original revision grant: prior narrowing must persist even when host ceiling rises. Target repository outside result → denied. No request-scoped new narrowing mechanism. Existing Goal/host usage persists, no refund/reset; consumed amounts above reduced limits produce zero headroom (`tasks_v5.py:185–206`).

## Ordered transaction and replay

Use current `control` replay namespace and normalized **entire request**, including epoch (`tasks_v5.py:114–128,957–1016`). Parse first; identical replay before authority returns its immutable original receipt; altered input same key → conflict. Fresh key: missing Goal → not_found; old revision → stale; epoch alone ignored. Latest completed/cancelled/failed → conflict. New origin equal to any stored origin of this Goal → conflict; new origin with identical Brief can deliberately create another revision. Suggested host key `dumps(['C10.change',goal_id,revision,origin_record_ref])` is a host convention, not a new field.

After replay/current/terminal checks: validate latest state in queued/waiting_input/paused/running, strict question integrity and lease/control consistency. Running requires active lease of same Goal; active lease for this Goal requires running; older lease revision requires drain=1. Corrupt data → unavailable. Then origin-reuse, grant/target, gate new origin+explicit context, integer overflow checks, guarded Condition mints in that order. Within new Brief IDs must be unique; mint new IDs for all conditions, even unchanged text. Default UUIDs plus rejection of collision with existing same-Goal Condition IDs gives freshness without global registry.

One transaction inserts new revision=prior+1, epoch=prior+1, preserved Goal/session/expert, immutable new Brief/grant/origin and new required source index. New state: queued from queued/waiting; paused from paused; running from running. Mark old row `superseded`, clear old control flags, supersede only open old questions (answered/closed remain historical), set new running flags `(carried_pause,drain=1)` else `(0,0)`. Append one C14 state event `work changed`, new WorkRef, refs `[origin]`, then save receipt. No Step/artifact/check/question/answer/pending-link transfer and no ART/VER writes. Overflow, failures and interruptions while the owned transaction remains open roll back all changes/key.

**Frozen Root choice:** mint every Condition ID and the single change event ID before the first owned write. Each callback has the ASK-style savepoint/transaction-ownership and total_changes guard. Reject duplicate new Condition IDs and IDs already used by any revision of this Goal. TSK appends the state event using that pre-minted ID in its own local writer; do not edit IntakeStore or add a shared framework. Validation, rollback and source checks remain in the same owned transaction. A callback exception, mutation or COMMIT/ROLLBACK before owned writes must cause no TSK effect or replay key. This is not a hostile-host sandbox and cannot undo arbitrary trusted callback writes/commits. Ordinary Exception/BaseException after owned writes, while that transaction remains intact, must roll back the whole change. Existing unrelated event-mint paths retain their trusted-host boundary; do not claim global hardening.

## History-only state: exact shared contract delta

Add `superseded` solely to **historical C02 work state** and question status. Current seven-state work domain stays unchanged. Older rows must be superseded; latest row may never be superseded. C02 old revision returns historical Brief/grant/artifacts, state superseded, open_questions empty. C02 current/default continues latest. C04 key lookup and ask/answer replay return their original receipts, including old waiting state, as historical facts.

Source feasibility: `IntakeStore.get_work` emits raw row state (`intake_v5.py:194–218`), TaskStore overlays artifacts/questions (`tasks_v5.py:302–313`), and READ display uses that string (`read_consumer_v5.py:293`); no seven-state parser or `_row_wire` exists in these current paths. `contracts_v5.py` has no WorkState/get_work value class. Thus no Python shared-type widening is needed. The shared PAL-contracts-v5 C02/C10/C13/section5 addenda are part of this freeze; no Python shared type is widened.

`_questions` must accept superseded status, reject open on historical/superseded work, preserve answer-null/status equality and all bidirectional Step/call/source integrity (`813–844`). Latest waiting/open/no-active-lease rules remain intact (`845–852`); historical superseded naturally needs no waiting question. Validate latest-versus-history explicitly so a corrupt latest superseded row cannot pass as readable history. Old finished ask retains its original epoch. New-key answer with old revision is stale. No answered link is erased or carried into new C12.

## Old lease release and strict cessation evidence

No-lease claim selects latest queued rows only. Retained claim returns old lease row diagnostics; `_authority` rejects old revision (`130–158`). New admissions/reservations/Steps/save/ask/complete using old WorkRef remain stale; get_call.may_enter=false (`432–442`).

Keep release request `{lease_id,work_ref,outcome,reason}` and lease_id replay key. Missing lease → not_found; inactive fresh invocation → denied; supplied Goal/revision not owned → stale. Epoch remains tolerant. Load owned old row and latest row separately. If same revision, preserve existing release behavior. Across revisions, require old superseded, latest running+drain or cancelled; outcome paused requires latest pause intent. Latest cancel wins, else pause→paused, else queued, even for old failed outcome. Abandon only old started Steps; close slot, clear latest flags, append latest-state event, return latest WorkRef. Immutable replay never changes subsequent state; changed release request same key conflicts.

**Necessary strengthening beyond Opus's status-only wording:** before any writes, validate owned calls' recognized statuses, strict WorkRef Goal/revision, nonnegative integer index (bool rejected), model reservation lease/work/index and binding-to-call identity; if Step exists require Step ID, SQL goal/revision/index/call and wire WorkRef/index equality to that call. Supplied old release epoch need not equal call epoch; call WorkRef must agree with its immutable admission reservation and cannot exceed owned row's preserved epoch. Duplicate/inconsistent call/Step associations or malformed stored values → unavailable. Admitted → conflict; returned/raised/not_entered alone are eligible ended statuses. A valid returned call with no Step is allowed to be discarded after revision fencing; it does not require successful output adoption. Do not reuse `_ready_to_close` unchanged: it requires current WorkRef and successful Step completion (`717–746`). The existing unknown-status fix (`1035–1038`) is necessary but not sufficient for corruption-safe cross-revision cleanup.

RUN source supports higher-revision release results: `mock_runner_v5.py:150–164` forwards TSK result without comparing reply WorkRef to the captured old one. Authority loss takes release(yield) (`475–479`); retained started/call paths also use safe release (`425–458`). **No unconditional RUN change is needed.** Root connected tests must additionally cover retained compose/ask paths before the ordinary authority check, since those may reach ART/VER/C04 prior to release; if a specific path fails to settle, change only that demonstrated path. No new inference or provider retry is permitted.

## Source-stop ordering correction

Opus §8's last sentence is too broad: stop-before-change denies **only if new origin or declared context is stopped**. An old-only stopped source omitted from a genuinely independent replacement does not itself fail its gate. The trusted host must not hide reused old content by omitting dependencies.

Distinguish state order: stop invalidates epoch/drains but does not itself always mark failed (`tasks_v5.py:1061–1106`). If RUN has subsequently committed failed on required-source denial, change is now terminal conflict regardless of fresh origin. If latest is still nonterminal, a fresh self-contained correction can replace old stopped origin; explicitly reused stopped dependency denies. After replacement, stopping exclusively old dependencies leaves new revision unchanged; stopping new/shared registered dependencies advances latest epoch, and required-source execution failure remains possible. No correction/replay restores source availability. Completed history keeps terminal fact.

## Fixed tests before implementation (NOT_RUN at freeze)

| ID | Case | Required result |
|---|---|---|
| 1 | Closed command, strict parsers, no kwargs/model grant, wrong repository | invalid_input/denied with no writes/key burn. |
| 2 | queued/waiting/paused/running change | Exact new revision/epoch/state/flags; same Goal/session/expert; old superseded; empty new artifacts/Steps/links. |
| 3 | host narrows→later widens; zero limits; consumed usage | Prior ceiling remains; counters unchanged; no new allowance. |
| 4 | identical replay after stop/release/change/terminal; modified epoch/key/origin | Original receipt; changed-input conflict; fresh old revision stale; same origin fresh key conflict. |
| 5 | historical open/answered/closed questions and C04 lookup | Only open superseded; historical read succeeds; latest malformed waiting/superseded unavailable; answer history intact. |
| 6 | stopped old-only before replacement, explicit reused stop, RUN-failed before change | Nonterminal independent replacement succeeds; reused source denied; terminal failed conflicts. |
| 7 | old admitted→change→pause→change→shared stop→returned→release old | Slot retained until ended, latest pause/epoch wins; latest cancel variant stays cancelled; old failed cannot fail replacement. |
| 8 | NULL/unknown call status; forged old WorkRef/index/reservation/Step; bool index | unavailable/no mutations; valid ended without Step can settle fenced lease. |
| 9 | latest-only claim plus old queued/superseded rows | No historical claim; retained old lease never grants admission. |
| 10 | historical ART/VER + old ask/report/compose/verification retained RUN tails | No current adoption; eventual safe old release, higher-revision reply accepted, zero extra callback/reservation. |
| 11 | two-connection change versus admit/finish/ARTsave/VERsave/complete/answer/stop | Commit order determines acceptance/history/stale; latest controls win. |
| 12 | mint failures/transaction loss; post-write event exceptions/BaseException; overflow/collisions | Guarded prewrite failures cause no TSK write; live-transaction faults roll back; no claim to undo host COMMIT. |

Reuse existing ASK tests `tests/test_tasks_ask_v5.py:157,187–214,296–341` and C13 unknown-status tests `tests/test_tasks_release_integrity_v5.py:11–31`. Independent test author must establish actual red evidence, not treat this table as execution.

## Adopted disposition and ownership

Adopt unchanged control(request), latest-prior grant intersection, trusted-host provenance obligation, origin dedupe, historical superseded, latest-only claim and latest-intent old-lease settlement. Adopt Astra's stricter call/reservation/Step binding before cleanup and conditional source-stop ordering. Reject the candidate v0 new authority keyword and unconditional RUN patch. Event-ID pre-mint is the Root routine choice above. No new owner decision or framework is required; natural-language Primary authority remains unimplemented.

| Owner/context | Write scope | Deliverable and dependency |
|---|---|---|
| Separate native Sol test context | tests/test_tasks_change_v5.py; CHANGE01-TSK-TESTS.md note/evidence | Immutable TSK tests and honest RED result before source. No TaskStore edit. |
| Separate native Sol RUN test context | tests/test_mock_change_v5.py; CHANGE01-RUN-TESTS.md note/evidence | Immutable stale/retained RUN tests before source, zero extra model/reservation proof. No unconditional RUN edit. |
| Native Astra source context | pal/tasks_v5.py only; CHANGE01-IMPLEMENTATION.md note | Wait for fixed test commits, then implement this scope. Return source diff, focused/full evidence, remaining issues. No fixed-test/canonical/other-owner edits. |
| Root/Sol | shared/canonical docs; tests/test_change_connection_v5.py; scripts/demo_change_v5.py | Actual temporary MEM/TSK/RUN/ART/VER/C14 connection, ordered two-connection and necessary fault cases, integration, exact byte checks, whole-suite verification. |
| Independent reviewer separate from source author | note/evidence only | Inspect exact source/contract/tests; reproduce important failure paths. Author self-check is not independent review. |

Native capacity is4 including Root. CO0.4.5/state unchanged; Claude planner was last session-limited until reported22:20 JST, not observed available. SWE-2 High remains preferred when usable without violating D041 role pins; no duplicate of the Astra implementation is launched to fill slots. Existing unknown calls remain untouched. Current code/input is the frozen commit communicated with each assignment; the source baseline above binds unchanged owner modules.

Read inputs: this scope, shared PAL-contracts-v5, actual tasks/intake/contracts/mock_runner/MEM/ART/VER/READ owner modules as needed, ASK fixed tests and C13 release-integrity regression. Writes are isolated in separate existing worktrees; no shared DB, live service or canonical writes by delegates. All experiments create temporary SQLite DBs. Root serializes shared contracts, integration and external project records.

Completion requires fixed targeted tests, old regression preservation, actual-owner connection and executable demo, full local suite, independent exact-source review, and a bounded milestone design review with coverage limits. CO verified would cover only its declared verifier; neither a reviewer opinion nor counts prove the product. No live DB migration, recovery activation, real model/provider/PRI/UI, semantic sufficiency, external operation, new auth/service/cost or whole-PAL completion. Root integrates only reviewed diffs and retains failures and unknowns.

Inspected source at freeze remains unchanged: tasks Git blob `68ac56ae6e7d8a93e1806fe19c22a25fd721e972`; intake `2cc592f49bb286e97fe9b3380332260e802b03e6`; contracts `f112f397440ed3c011ae51e8067834f2f1795a36`. No legacy compatibility or schema migration is required; do not open or modify old/live DBs.
