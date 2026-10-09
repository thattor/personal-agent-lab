# READ01/1 — saved-result inspection consumer design

Design direction ADOPTED after exact Opus5.5 taskd2abb079 (C076 ALIGNED,
READ01 REFINE) and Root dispositions below. C076 sourcebdce832 has full711 and
independent review approval. SWE consultationc2027bf7 is ALIGNED; exact seams are
now frozen with the Root dispositions below. Separate test/code owners may proceed.

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
The following frozen projection/consumer shape and bounded pagination/error rules
apply to the independent assignments. C076's nonblocking
RUN verify-authority note is retained for the next RUN change, not a new task or
claim that all owner failures prove a TSK fence.

## Frozen SWE disposition and examples

Adopt SWE sections1/2 with these corrections: unchanged total_changes applies to
ordinary reads only; SQLite counts even rolled-back injected writes. For mutating
clock faults require rejection and unchanged durable dump where rollback remains
possible. A trusted callback COMMIT cannot be undone; never claim full rollback
after it. The clock must return a nonempty ISO-8601 UTC string (Z or zero offset);
default uses timezone-aware UTC. Validate it and guard its call within the read TX.
Wrong Ref kind at VER.read is unavailable, matching ART/MEM; malformed Ref is
invalid_input. Invalid host purpose raises ValueError before dispatch for all owners.

VER content has exactly work_ref, conditions, artifact_refs, artifacts, source_refs,
checks. Conditions/checks retain their stored fields; artifacts has only ordered
{artifact_ref,hash,bytes}. No creation time, current status or replay key in content.

Freeze the reader class as `HostReader(memory, artifacts, verifications)` in
pal/host_read_v5.py. Method read({ref}, *, purpose) uses the exact owner request
and keyword; unsupported recognized kinds have no fallback. An exception, non-Result
or malformed returned Result is unavailable; BaseException propagates. No DB state.

SWE's single-work consumer example cannot represent a multi-work session. Use
`inspect_session(request, *, events, tasks, reader, max_pages=64)` in
pal/read_consumer_v5.py. Request is closed {session_id,after_event_id?}; max_pages
is a host integer1..64. Return a Result whose success value is exactly
{session_id,items,next_cursor,truncated}. Each item is {event,work,reads}: event is
the original selected C14 event; work is the C02 Result serialized to JSON; reads
preserves every event Ref as {ref,result,validity}. result is the C11 Result JSON;
validity is null for non-verification/error, otherwise current|not current|source
stopped. The renderer parses successful verification display content for fixed
Conditions/checks and public artifact bindings; this never becomes authority.

Exact calls: events.get_events({session_id,after_event_id?}); tasks.get_work(
{goal_id,revision}) from the event WorkRef; reader.read({ref},purpose='user_view').
Select result events and progress events with the exact COMPLETE01 notice text.
Missing event WorkRef produces visible unavailable work, without a guessed ID.
Correlate source-stop notices by Goal+revision and named Ref intersection with the
verification's source_refs. A usable result stays current; an unusable result is
source stopped only with that evidence, otherwise not current. Include all refs
by kind/order; retain per-ref errors rather than dropping or substituting them.

Advance through unselected pages as well. Empty page ends with truncated=false;
reaching max_pages after a nonempty page returns truncated=true and the last scanned
cursor (more data may exist). Nonempty no-progress/repeated cursor or malformed page
is unavailable, not silent completion. An unavailable event page returns failure;
per-work/per-ref failures stay in the successful inspection. No persistent cache.
render(inspection) accepts this success value and returns plain text with mock
model, structural verification and read at labels, TSK state separate from each
body's usable/validity, and all per-work/per-ref failures visible. Page truncation
is visible. A session's different works are never collapsed into one work state.

The real local demo must call this same consumer; a generic dispatcher alone does
not complete READ01. Split immutable VER-read tests and host/consumer tests from
the code authors. Root owns the actual demo/connection evidence and canonical docs.

READ-specific error disposition: only absence of the requested verification Ref is
not_found. Context(status) not_found means current status cannot be established
and maps to unavailable in read. Typed C09 get_verification is unchanged.

C11 host dispatch preserves the existing owner contract: work_ref and version are
optional envelope fields (PAL-contracts-v5 C11). MEM omits work_ref; ART and VER
include it. Allow absent/null/valid WorkRef and absent/string version, reject extra
keys. VER's own exact eight-key response remains as frozen above. The renderer
uses the owner's stored observation time for MEM/ART, current read time for VER.
