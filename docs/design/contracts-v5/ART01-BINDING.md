# ART01-bind/1 — connect saved drafts to current work

PROPOSED technical continuation under D038, after ART01-store/1 and RUN01/2.
This is the mock compose -> saved and attached draft milestone recommended by
Opus task6bd433a2799a49d2b27d5c5bc9708e7d. No VER/complete, real provider/UI,
general recovery, new permission/cost/service or live database activation.

SOL owns TSK/RUN/ART integration and common records. SWE consultation precedes
substantial connection changes; separate Sol reviews the exact integrated source.
Do not begin code against an unavailable ART implementation; consultation can use
the frozen owner boundary while that independent implementation completes.

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
