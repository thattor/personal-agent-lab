# RECOVERY01/1 proposal — managed local mock restart

Status: NOT ADOPTED. Astra design candidate for Root/Opus; no code, tests or
recovery acceptance. Input commit: `175cdc6db5d9948379335f638e957a6a29e16204`.

## 1. Scope and evidence

Read current canonical docs, RECOVERY01-PREPARATION, C13 and v5 owners only.
Only this proposal changes. Independent tail analysis consulted directly:
`RECOVERY01-TAILS-REVIEW.md`, commit `96e1560971e32fa1375184d6247ba73607ad545a`.

C13 lines135–143 requires startup proof, reconciliation/fencing, latest controls,
no repeated completed operation and fresh VER. C07 line101 excludes child
cessation proof from lock acquisition.

Current seams: TSK `pal/tasks_v5.py:85–92,114,238` owns lease/call/Step,
transactions/replay and latest-only claim. Matching runner text is not proof.
`:413,448` only accepts returned/raised/not_entered and begins from returned.
`:1037,1164,1240` validates old bindings and preserves latest controls/source-stop.
RUN `pal/mock_runner_v5.py:31–79` has only a thread lock; `:449–472` holds
unfinished work and finalizes attached compose. ART `artifacts_v5.py:219` and
VER `verification_v5.py:328` expose historical get_by_key, not current authority.

## 2. Recommended bounded choice

Include **managed in-process mock interruption**, not only known-ended cleanup.
An admitted row after process death otherwise blocks the main inference path
forever. Add internal call outcome `interrupted`: old callback execution has
ceased under the managed lifetime guarantee, but entry, return and result are
unknown. It is not a successful model result, an exception receipt or proof of
non-entry. Only startup recovery can create it; `end_call` accepts its existing
three outcomes unchanged. `get_call` reports it with `may_enter=false`.

Ended-only cleanup is smaller but leaves admitted crashes blocked. Prefer it
only if lifetime-lock acceptance cannot pass. This slice permits only trusted
synchronous in-process mock callbacks, no spawned work, fork, remote/provider,
external effects or escaped threads. The host constructs this bounded adapter;
a caller boolean cannot qualify arbitrary callbacks. This is a trusted host
invariant, not runtime code-behavior detection or a hostile Python sandbox.

## 3. Host guard and durable ownership

Host owns OS lock/opaque session; TSK owns registration, recovery and C14;
RUN uses managed invoker. ART/VER retain body/receipt ownership.

`MockHostSession.open(database_path)` acquires a nonblocking exclusive OS lock
before opening owners. The returned context object is not JSON or a user token.
It stores a fresh unpredictable session nonce, creator PID (fork detection only),
canonical DB path and filesystem identity, open lock FD and private lifecycle
phase. Proposed first platform: POSIX local file DB, standard-library flock;
no memory DB, network filesystem, URI alias or cross-platform lock promise.

Use one canonical permanent sidecar, never unlink on cleanup. Reject symlink
lock files, multiple hardlinks, path/inode replacement and connection mismatch.
Resolve DB real path; bind device/inode, actual SQLite filename and persistent
DB UUID. First initialization creates DB under lock before assigning UUID.
Copies/restores/replacements are unsupported; UUID alone is insufficient.
Same-process registry prevents second guard. PID/time/text is never proof.
These checks address accidental aliases, not hostile filesystem replacement.

FD is non-inheritable; fork/subprocess use unsupported. Hold lock through all
callbacks/owner operations/cleanup. Invoker holds a guard activity permit from
before admission until callback cessation and end-record attempt. Close refuses
while activity exists, including exception cleanup in another thread. Process
death ends in-process callbacks; no forced unlock/kill. Uncertain lock blocks.

Minimal durable additions, owned by TSK:

- singleton DB UUID and managed-profile version;
- append-only session registration `(nonce, db_uuid, runner_id, profile)`;
- lease-to-session binding written atomically with every managed claim.

Existing call→lease links transitively bind calls; do not duplicate a second
call ledger. Enrolling a DB never assigns an existing lease a new session. A
legacy active lease, missing registration, wrong profile or mismatched identity
remains unavailable. Once enrolled, execution/admission APIs require the active
managed guard; separate connections may still issue C10/MEM controls. Legacy stores remain ineligible.

## 4. Proposed exact host API and startup ordering

- `TaskStore(..., startup_guard=session)` adds the optional trusted seam.
- `tasks.register_host()` → Result `{session_id, runner_id, orphan_lease_id}`;
  orphan is null or the sole prior active lease. TSK checks guard and connection,
  atomically registers a fresh session and binds a startup snapshot. No claim or
  callback is allowed yet. No orphan does not mean corruption can be ignored.
- `tasks.recover({key, lease_id})` → Result `{work_ref, state,
  control_status:"none", recovered_lease_id, interrupted_call_ids}`.
  Closed input, nonempty strings. Caller cannot supply old status, source proof,
  nonce, desired state or cessation boolean. Expected lease must match startup
  snapshot and belong to a prior registered managed session, never current one.
- `tasks.finish_startup()` checks no occupied unresolved lease and activates the
  guard for normal RUN. Once ready, new recovery is rejected. A receipt replay
  can be read during a later valid startup; it never reopens dispatch authority.

BEGIN IMMEDIATE; idle connection; bounded errors. Same-key/same-input replay
precedes live state checks but requires valid startup guard/DB identity. Changed
input or closed-lease new key: conflict. Missing: not_found. Bad input:
invalid_input. Stored corruption/unsupported proof: unavailable. Lock conflict
precedes owner initialization. Empty startup changes no work/events. Failure
blocks startup; no fallback claim or timeout escape.

## 5. Atomic recovery decision

Inside one transaction, before owned writes:

1. Validate guard/snapshot/session/DB identity, lease identity and latest Goal
   revision. Strictly validate all owned calls, reservation kind/role/binding,
   canonical `dumps(["C15.call", lease_id, index])`, nonempty IDs, strict bounded
   integer SQL/wire indexes, call WorkRef and matching Step WorkRef/index/ID,
   reverse links and full `required(old) <= call.sources <= registered(old)`.
   Never accept mutually consistent malformed IDs. Exact lease claim epoch
   should be persisted in the new lease binding, so all calls can match it;
   current row epoch may legitimately have advanced through source-stop/control.
2. Validate current flags, questions and bidirectional artifact set. No unknown
   status is an implicit interruption. Recognized admitted becomes eligible for
   interrupted only through the old managed session proof. Finished Steps are
   immutable; historical leases/Steps from earlier epochs remain valid history.
3. Classify tail below. Unresolved/corrupt receipt means no settlement writes.
   Source availability is not needed to prove cessation or release old occupancy.
   New use/adoption is a separate same-TX source gate; never gate only selected
   Action refs instead of full producing-call provenance.
4. Premint bounded event identity under transaction-preserving host guard before
   writes. Mark eligible admitted interrupted; abandon only safe unfinished old
   Steps. Fence latest nonterminal WorkRef once (overflow unavailable), close old
   lease, clear drain/pause flags after applying intent, emit one state event,
   save replay and commit. Do not rewrite call/Step WorkRefs or budget rows.

Terminal state/epoch stays unchanged. Otherwise paused/flag wins, then valid
open question means waiting_input, else queued. Superseded never revives. Keep
source-stop question closure; unrelated optional stop cannot discard a question
or answer. Paused may lack question. Queued grants no source permission: fresh
RUN context/admission gates still reject unavailable required sources.

Replay cannot add epoch/event/budget. No refunds. New inference uses fresh
lease/call/reservation under the same Goal ceilings and finite RUN limits. Saved
completion/question/artifact receipts never permit repeating the operation.
SQLite failure and BaseException roll back all owned mutations; BaseException
propagates. Guard/owner callbacks are trusted; no promise to undo their COMMIT.

## 6. Tail boundary and examples

| Orphan tail | Proposed first-slice result |
|---|---|
| admitted, no Step | interrupted, fence/close; fresh bounded inference permitted |
| returned, no Step | preserve returned; lost unsaved output, fence/close; no redispatch of old call |
| raised/not_entered, no Step | preserve fact, fence/close; fresh bounded attempt allowed |
| returned + finished Step | preserve Step/event/result; fence/close |
| started report/lookup, no durable result | abandon; no false finished/result event; fresh inference allowed |
| started ask | validate atomic question linkage: saved question implies finished Step; inconsistent half-state unavailable; otherwise abandon |
| started compose | hold in first slice; receipt lookup/eligibility/adoption is not implemented by ordinary finish_step |
| missing/unknown/corrupt/unmanaged ownership | unavailable; no mutations or dispatch |

Example: ART save committed before compose finish. Keep receipt/lease pending;
never save again. Future adoption must inspect receipt, recheck full sources and
current purpose, then atomically attach with recovery provenance. Even not_found
is not old dispatch authority. This remaining C13 blocker is explicit.

Attached compose may use RUN retained-tail logic; new epoch needs fresh VER
for the exact ordered current set. Missing historical VER keys cannot be guessed
from a changed latest set; a future tail needs saved operation identity.

## 7. Fixed acceptance before source

- Real two-process fixture: old managed callback blocks on barrier; second host
  cannot register/claim/recover. Kill first process; only then restart succeeds,
  records interrupted, preserves charge and invokes a new call once. No provider.
- Guard close during callback, second same-process guard, forked use, wrong DB,
  aliases/replaced inode and unmanaged old lease all refuse without state writes.
- Crash at register/claim/admission/returned/begin/finish boundaries; exact dumps
  prove atomic rollback, replay and no duplicated events/receipts/model call IDs.
- Mutually forged empty IDs, reservation links, bool/negative indexes, bad Ref,
  call.sources object, missing required/unregistered source and orphan Step refuse.
- Recovery versus cancel/pause/change/source-stop using two DB connections:
  serialized latest intent, old revision stays superseded, unrelated optional
  stop preserves question/answer, completed history never reopens.
- Zero/exhausted budget: recovery itself succeeds without refund; subsequent
  claim/reservation still respects limits. Fresh call is not old-call retry.
- Finished compose survives; new VER is required; persistent returned-no-Step
  becomes recoverable; started compose receipt/no-receipt/unavailable all hold
  without save; corrupt atomic ask half-state fails closed.
- Event/replay write abort and BaseException restore full pre-state; lost response
  returns identical receipt after restart, with one epoch increment/event only.

## 8. Root/Opus choices before freeze

Recommend interrupted plus explicit compose hold; not full C13 recovery.
If all compose crash points must be included now, add a separately specified
ART recovery-adoption callback/TSK atomic binding and fixed tail tests first;
do not disguise ordinary finish replay as new-epoch adoption. Lock platform,
internal status and API need Root adoption.
No PRI/UI/provider/EXE, migration, semantic or whole-product claim.
