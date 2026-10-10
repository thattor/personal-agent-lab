# ART01-bind/1 — connect saved drafts to current work

ADOPTED technical continuation under D038/C073 after SWE consultation f4cba212.
RUN01/2 is accepted; ART01-store/1 has an unknown CO implementation outcome.
This is the mock compose -> saved and attached draft milestone recommended by
Opus task6bd433a2799a49d2b27d5c5bc9708e7d. No VER/complete, real provider/UI,
general recovery, new permission/cost/service or live database activation.

SOL owns TSK/RUN/ART integration and common records. SWE consultation precedes
substantial connection changes; separate Sol reviews the exact integrated source.
The TSK consumer and RUN coordinator may be prepared against this frozen callback
contract in isolated files with explicit test doubles. Do not consume or reimplement
the unknown ART task. Actual storage integration waits for a safely obtained owner
implementation and independent review; component tests do not satisfy that dependency.

## Minimal boundary

Add a read-only ART callback, with a real supplied same active connection:

    ArtifactStore.inspect(connection, {'ref': artifact_ref}) -> Result[{
      'artifact_ref': Ref, 'work_ref': WorkRef, 'step_id': str,
      'hash': str, 'bytes': int, 'source_refs': [record Ref]
    }]

ART validates immutable stored bytes/hash/length, metadata and current record
availability. No text parsing by TSK and no TSK access to ART SQL. Missing artifact
is not_found, stopped source denied, corrupt/missing provenance or owner failure
unavailable. No writes or transaction control; unknown source kinds are unavailable.

TaskStore receives optional artifact_inspect host callback. Without that callable,
compose attachment remains unavailable. finish_step's compose branch requires
exactly one artifact Ref, no lookup truncated/excluded metadata and no error field.
It confirms current running WorkRef/lease/no control/started Step/returned call,
then inspects the artifact in the same TSK transaction. Saved WorkRef and step_id
must exactly match; dependency records must exactly cover the producing call's
supplied refs under ART01-store/1. Recheck source usability. A missing/stopped draft
fails attachment; never silently filter a compose result into successful emptiness.

Atomically persist Step finished, append the artifact to a TSK-owned current set
for the same Goal/revision, record its record dependencies and one C14 progress
event, and save finish replay. Every distinct compose Step can add one artifact;
do not infer replacement semantics or change prior immutable bytes. Existing
get_work's closed C02 shape projects this actual set, with [] for earlier work.
No VER rows exist yet; invalidating saved verification is a prerequisite for later
C09/complete. Failure after any write rolls back the entire attachment transaction.

## Keep unsupported artifact re-input closed

This minimal slice saves, attaches and exposes drafts for trusted owner readback.
It does not add artifact refs to the model context or register them as available
input sources. MEM's record-only source gate remains for create/register/admission.
Artifact in Brief.context_refs, lookup.source_refs or registered model input stays
unavailable. finish registers the artifact's record dependencies, not the artifact
as a model-context source. Existing historical-Step filtering conservatively omits
compose Steps whose artifact result is not in available C11 model context.

This restriction prevents the specific missed-invalidation case: another Goal
references artifact A derived from record R, but its index contains only A, so
stopping R would be missed. Before later artifact re-input, add one-level kind
dispatch plus common create/register/finish dependency registration of both A and
its verified record dependencies. ART remains record-only; no recursive resolver
or alternate task engine is needed. Stored dependent records are invalidation
coverage, not proof that their bodies were read into a model call.

## RUN composition and interruption

MockRunner accepts optional ART owner. Existing report/lookup-only construction
keeps its behavior; a compose proposal without the owner is explicitly unavailable
before creating a compose Step. With ART, use canonical
dumps(['C08.save', work_ref, step_id]), save the exact validated compose action,
then finish with the returned artifact_ref. TSK's save authorizer conservatively
includes all actual call input records, including model-unselected sources.

Repeat only idempotent local save/get_by_key/finish on unavailable with bounded
attempts, never the callable. A lost save response recovers the original receipt;
receipt recovery does not authorize attachment after a control/source change.
After persistent local failure, RUN01/2 asks TSK whether latest control can release
the ended output; otherwise retains occupancy. No general restart adoption or
same-call recomputation is introduced. Missing/invalid body and latest controls
remain explicit Result outcomes. Goal is queued or controlled at bounded release,
not completed by a save or model report.

## Required connected evidence

Actual MEM/TSK/ART/mock/C14: compose saves exact bytes, attaches one current Ref,
and reconnect delivers one progress event while Goal remains unfinished. Test
save commit/lost response, finish commit/lost response and persistent failures
without duplicate artifact/set/event/budget/model call. Order stop/pause/cancel
before save and after save/before finish; retained body may be history but cannot
be attached after losing authority. Wrong WorkRef/step, corrupt inspect metadata,
empty/multiple/non-artifact results, mid-attachment fault and no-ART runner must
fail closed. Prove artifact re-input remains denied rather than claiming full
kind-aware source support. Disk reopen/get_by_key is receipt recovery only.


## SWE consultation disposition and exact binding rules

Adopt R1-R9 from evidence/operations/art01-20261009/swe-binding-review.md with two
clarifications: an unregistered artifact is allowed in execution provenance only
when it is the validated, attached result of that finished compose Step, not merely
because its kind is artifact. Callback guards detect violations; a trusted callback
that commits its caller's transaction cannot be claimed to have been rolled back.

- TSK owns v5_tsk_artifact_set(goal, revision, seq, artifact_id, step_id) or an
  equivalently constrained minimal table. Unique artifact/step within the revision;
  ordered append, never replacement. C02 get_work exposes validated stored refs,
  empty for no rows, corrupt row unavailable. Root owns final schema integration.
- get_execution_context requires all input record provenance to remain registered.
  A finished compose result must match its TSK-owned set/step binding. Include the
  artifact in step_sources, so existing RUN filtering excludes the whole compose
  Step until actual C11 artifact re-input is adopted. Test a later claim/report;
  do not permit unknown arbitrary artifact refs or register them as input sources.
- TSK begin_step compose requires a configured artifact_inspect callable. Without
  it return unavailable before any Step write. Store-stage hook unit tests can
  supply a readonly unused inspect stub; that is not ART integration. RUN also
  rejects no-ART compose before begin_step, retaining the ended call unless a
  newer control permits release. No repeat callable or additional reservation.
- Inspect guard: same active connection, savepoint, callback, still active,
  successful release, unchanged total_changes, strict six-key Result value and
  exact types. Error/mutation/exception/bad shape is unavailable. Normal rollback
  removes all attachment writes; collaborators remain trusted host code.
- Inspect source_refs set must equal the producing call's complete source set,
  record-only/nonempty, and call.step must equal step_id. Require hash/byte metadata
  to be syntactically valid. Recheck current source gate. Corrupt provenance is
  unavailable; gate denied/not_found/unavailable preserves the owner result.
- Compose input: exactly one artifact result, no error, no truncated/excluded
  metadata. Violations invalid_input with unchanged Step. Inspect ref mismatch is
  unavailable; wrong saved step conflict; wrong saved WorkRef stale; absent artifact
  not_found; non-returned call conflict; wrong lease denied; missing call unavailable.
- One finish transaction writes Step finished, one ordered set row, record-only
  dependency registration, one C14 progress event carrying the artifact, and replay.
  Fault after any write rolls all of them back. Replay precedes authority checks;
  a committed finish replay after pause/release returns the original receipt.
  An uncommitted finish after abandonment cannot newly attach historical storage.
- RUN retries identical local save at most three times on unavailable; only then
  retries get_by_key at most three times to recover its original receipt. Never
  get_by_key after conflict/invalid_input or use it as current attachment authority.
  Finish remains bounded/idempotent and refences current controls/sources. Exactly
  one artifact, set row, event, model call and budget unit after response loss.

Ownership: isolated Astra may change tasks_v5.py, its focused tests and a binding
implementation note. SOL owns mock_runner_v5.py, consumer tests and canonical docs.
ART storage files stay owned by the unresolved CO task; no concurrent replacement.
Separate Sol reviews TSK and RUN changes after exact commits, independent of authors.


C073 route clarification after scoped diagnosis: the prior no-duplicate instruction
prohibits a blind CO retry, not the owner's explicit separate native implementation.
Root freshly read actual owner message01a11e03-d444-78c1-9fab-b0e861d29d1d: use
Astra/Sol6.1/AGY while SWE2 cannot implement; direct call allowed without a CO adapter.
Diagnosis found no local process, no assistant/tool response and no implementation
files for task917989. Remote cessation/cause remain unknown. Preserve that pause and
workspace exactly. A NEW isolated native Sol6.1 workspace implements ART01-store/1
plus the frozen inspect callback; no late CO output auto-adoption, no shared DB or
external effects. This applies existing user authority (which supersedes skill
routing defaults), not a fabricated CO pause decision or new CO engine. AGY's own
unresolved call/rejection stays untouched. Ordinary Codex usage is allowed; no paid
fallback, reset, new authorization or external service is used. Independent Astra
will review ART after its TSK task; separate Sol reviews Root/Astra changes.
