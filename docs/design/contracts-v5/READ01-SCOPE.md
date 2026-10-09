# READ01/1 — proposed saved-result inspection consumer

PROPOSED, not adopted or implemented. Next dependency after COMPLETE01 candidate
bdce832, whose full711 and independent reviews pass. Root selected this from native
Astra's exact-source analysis; Opus reviews value and contract semantics before
adoption, then SWE consults the implementation/transaction details before code.

Value: a local consumer can follow the result event and inspect the saved draft,
the immutable fixed-condition checks and whether those results remain usable.
C11 plumbing alone is not completion of this slice: a small local consumer/demo
must actually traverse C14 result refs through the owners and show the distinction.
This is bounded mock preparation under D038, not product PRI/UI activation.

Only Python stdlib. No new schema/persistence engine, live DB/migration, services,
auth/payment, real model, model-context activation, arbitrary file/network tool,
question/change feature, broad registry or retry of prior unknown calls.

## Proposed owner APIs and semantics for review

VER adds `read({ref}, *, purpose)` like MEM/ART. Purpose is host-only
model_context|verification|user_view, never model-controlled. Ref must be
verification. Typed C09 get_verification/inspect remain C10's authority; C10 never
parses this display JSON. Same idle autocommit connection and one short read
transaction: validate the stored record, derive current status through existing
owner callbacks, and form the response from that consistent snapshot.

C11 response retains `{ref,content,media_type,hash,observed_at,work_ref,source_refs,usable}`.
Content is canonical JSON of a fixed historical projection: saved WorkRef, fixed
Conditions (IDs/descriptions/check kinds), ordered artifact refs, original checks
and record dependencies. Exclude replay keys, internal ART metadata and raw record
bodies. media_type=application/json; SHA-256 covers exactly returned UTF-8 content.
Current status is not in content, so subsequent invalidation leaves content/hash
unchanged. `usable` means this saved verification is currently valid, never that
its checks are all MET or that the work is currently running/completed.

VER stores no creation timestamp. Proposed minimum: observed_at is the current
read snapshot observation time in UTC, explicitly labelled observation time by the
consumer; it is not a fabricated verification creation time. No old row mutation or
guessed time. Opus should assess whether this is compatible with C11; if not, name
the smallest honest alternative rather than silently inventing historical dates.

Valid returns usable=true for each purpose, including honest unknown/unmet checks.
Invalidated returns the same body with usable=false only for user_view. Proposed
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
No implementation until the contract supplements above are resolved.
