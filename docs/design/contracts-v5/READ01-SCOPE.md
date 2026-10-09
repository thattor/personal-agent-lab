# READ01/1 — saved-result inspection consumer design

Design direction ADOPTED after exact Opus5.5 taskd2abb079 (C076 ALIGNED,
READ01 REFINE) and Root dispositions below. C076 sourcebdce832 has full711 and
independent review approval. Exact implementation seams remain pending SWE
consultation; no implementation dispatch before that freeze.

Value: a local consumer can follow the result event and inspect the saved draft,
the immutable fixed-condition checks and whether those results remain usable.
C11 plumbing alone is not completion of this slice: a small local consumer/demo
must actually traverse C14 result refs through the owners and show the distinction.
This is bounded mock preparation under D038, not product PRI/UI activation.

Only Python stdlib. No new schema/persistence engine, live DB/migration, services,
auth/payment, real model, model-context activation, arbitrary file/network tool,
question/change feature, broad registry or retry of prior unknown calls.

## Owner APIs and adopted design refinements

VER adds `read({ref}, *, purpose)` and optional injected `clock` like MEM/ART.
Purpose is host-only
model_context|verification|user_view, never model-controlled. Ref must be
verification. Typed C09 get_verification/inspect remain C10's authority; C10 never
parses this display JSON. Same idle autocommit connection and one short read
transaction: validate the stored record, derive current status through existing
owner callbacks, and form the response from that consistent snapshot.

C11 response retains `{ref,content,media_type,hash,observed_at,work_ref,source_refs,usable}`.
Content uses contracts_v5.dumps, encoded as UTF-8, for a fixed historical projection:
saved WorkRef, fixed Conditions (IDs/descriptions/check kinds), ordered artifact
refs, original checks and record dependencies. Also expose only the public C08
binding for each artifact, in order: `{artifact_ref,hash,bytes}`. Exclude replay
keys, remaining internal ART metadata and raw record bodies. media_type is
application/json; SHA-256 covers exactly returned UTF-8 content.
Current status is not in content, so subsequent invalidation leaves content/hash
unchanged. `usable` means this saved verification is currently valid, never that
its checks are all MET or that the work is currently running/completed.

VER stores no creation timestamp. observed_at is the current read snapshot
observation time in UTC, obtained from the guarded injected clock inside the read
transaction and labelled read-at by the consumer. It is not verification creation
time. MEM/ART retain their existing stored observation times; document the per-kind
meaning. No schema change, old row mutation or guessed time. Keep read time out of
content/hash. A mutating/committing/raising or malformed clock fails closed with
the same trusted-callback rollback limits as existing VER guards.

Valid returns usable=true for each purpose, including honest unknown/unmet checks.
Invalidated returns the same body with usable=false only for user_view. Adopt the
conservative supplement: model_context/verification reject all invalidation with
denied, including later epoch/set changes, not just stopped source. This does not
enable RUN artifact/verification context re-input. Missing Ref is not_found;
malformed/corrupt/uncertain owners remain unavailable, not a fabricated history.
No Goal/lease/budget/event/receipt mutation and no private owner SQL.

One small host reader dispatches exact closed `{ref}` to MEM for record, ART for
artifact and VER for verification, preserving the supplied host purpose. Valid
note/source/receipt have no current owner and return unavailable; unknown kind or
malformed input is invalid_input. Wrong input never falls back to another owner.
Constructor requires these explicit owners; no extensible plugin registry/state.

## Required concrete consumer and acceptance

Create a local stdlib demo/consumer on temporary SQLite with the real owners:
MEM record -> TSK intake -> mock compose -> saved ART -> VER -> complete -> C14
result refs -> host reader -> human-readable result inspection. Show saved draft,
fixed Condition descriptions/checks and present usability separately. Stop one
dependency and reread: completion stays historical, content/hash stay identical,
current usability becomes false. Label the model as mock and verification as
structural; do not imply semantic quality. Keep the demo separate from service/UI
activation and do not accept arbitrary DB paths by default.

The consumer follows C14 pages, selecting result events and the exact frozen
completed-history notice. Dispatch by Ref kind, not position; preserve event/ref
order and read TSK state through C02 `{goal_id,revision?}`. Return a structured
inspection and a plain-text rendering. State, historical checks and current
usability are separate fields/labels. Say not-current for invalidation; say source
stopped only when a notice names the Ref. C14 pagination must remain bounded and
retain its cursor, including pages with no selected events. Missing body/owner
errors must remain visible rather than dropping refs or inventing success.
Each owner read has its own snapshot; this consumer does not promise one atomic
snapshot across separate public owners, and never grants completion authority.

Add explicit acceptance for changed clock with unchanged content/hash; epoch-only
invalidation of non-MET history; completed+valid versus completed+stopped display;
multi-artifact order; result discovery after committed/lost response; pagination
past page_size; unsupported kinds with no fallback; structural/mock labels; only
user_view calls from the consumer; and unchanged total_changes plus DB dump.

Tests before implementation must cover all three Ref owners, Unicode/exact hashes,
fixed projection/no private keys, unknown checks, source stop/epoch/set invalidation,
per-purpose denial, missing/corrupt/transient owner outcomes, same-snapshot reads,
callback failure/interruption cleanup, reopen, closed inputs/purpose propagation,
and no changes to owner snapshots. Real consumer evidence is separate from
protocol doubles and full regression. Preserve current saved receipts and prior
acceptance; a read is not authority to complete or dispatch another model call.

Root owns this proposal, consumer composition, connected tests and canonical
records. VER implementation and a small independent reader can be isolated by file
once their seam is frozen. Reviewers differ from authors; no blanket dual review.
SWE consultation must freeze exact projection/consumer shape and bounded
pagination/error rules before those independent assignments. C076's nonblocking
RUN verify-authority note is retained for the next RUN change, not a new task or
claim that all owner failures prove a TSK fence.
