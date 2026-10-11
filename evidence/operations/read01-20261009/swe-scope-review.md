ALIGNED

# READ01 scope consultation — SWE seam freeze

Role: implement worker in the controlled pipeline; tools disabled; snapshot-only review. READ01-SCOPE adopts every Opus 5.5 refinement from the C076 milestone review (observed_at as read time via injected clock; fixed dumps/UTF-8 projection with public C08 bindings; "not current" wording; uniform purpose denial; smallest API and a real consumer; the acceptance list). No scope change is needed. What remains is freezing the seams below exactly, then tests, then code. This document implements and activates nothing.

## 1. VER.read — frozen interface

`VerificationStore.read(request, *, purpose)` mirrors `ArtifactStore.read`:

- `self._idle()`; `purpose` must be exactly `model_context|verification|user_view`, else `ValueError` (host bug, not a Result).
- Parse `{ref}`; a Ref whose kind is not `verification` returns `unavailable`, matching the ART/MEM convention (the dispatcher prevents it anyway).
- One short `BEGIN` read transaction: `_stored(ref.id)` → `not_found` when absent, `ContractError` → `unavailable`; `_current_status(stored)` → `'valid'|'invalidated'`; `_Failure` maps to its code; other `Exception` → `unavailable` after rollback; `BaseException` → rollback and re-raise. Interrupt cleanup is identical to `get_verification`.
- `observed_at` = `self._clock()` invoked inside `self._guard` inside the same transaction; the returned value is validated with `_id` (nonempty UTF-8 str). A mutating, committing, raising or malformed clock fails closed to `unavailable` with full rollback; `total_changes` and the DB dump stay unchanged.
- Response keeps the C11 shape: `{ref, content, media_type:'application/json', hash, observed_at, work_ref, source_refs, usable}`.
- `content` = `contracts_v5.dumps(projection)` encoded UTF-8; `hash` = sha256 hex of exactly the returned content. Time and current status are excluded, so content and hash are stable across a clock change and later invalidation.
- usable: `valid` → `true` for all three purposes, including honest unmet/unknown checks. `invalidated` → same body with `usable=false` for `user_view` only; `denied` for `model_context`/`verification`, uniformly covering source stop, epoch supersession and set extension.
- `get_verification`/`inspect` remain C10's typed authority; `read` grants nothing and RUN artifact/verification context re-input stays disabled.

Frozen projection keys (exact set; dumps sorts keys): `work_ref`, `conditions` (id/description/check as stored), `artifact_refs` (ordered), `artifacts` — the per-artifact public C08 binding `{artifact_ref,hash,bytes}` in the same order — `source_refs`, `checks` (condition_id/status/reason/evidence_refs). Excluded: replay key/input, `receipt`, `required_refs`, raw record bodies, internal ART metadata. No schema change, no row mutation, no private cross-owner SQL: only existing `_stored`, `_current_status`, `_guard` and the owner callbacks already injected are reused.

## 2. Host reader — frozen interface

New file `pal/host_read_v5.py`: one class whose constructor requires explicit `memory`, `artifacts`, `verifications` — no registry, no optional owners, no plugin state. `.read({ref}, *, purpose)`:

- malformed request or unknown kind → `invalid_input`;
- `record` → `MemoryStore.read`, `artifact` → `ArtifactStore.read`, `verification` → `VerificationStore.read`, passing the supplied purpose verbatim;
- `note`, `source`, `receipt` → `unavailable` (no current owner), never a fallback to another owner.

## 3. Consumer — frozen shape

New file `pal/read_consumer_v5.py`, plus a stdlib demo on temporary SQLite wiring real owners (MEM record → TSK intake → mock compose → ART save → VER verify → complete → C14). One function `inspect_session(...)` returns a structured inspection; `render(inspection)` returns plain text. Demo and tests drive this same function — it is not an unused abstraction.

- Page `get_events({session_id, after_event_id?})` with bounded page_size and bounded page count (`max_pages`, e.g. 64, then `truncated:true`). Advance on `next_cursor` even when a page selects nothing; stop on an empty page or a cursor that stops moving.
- Select `kind:'result'` events and the completed-history notice by its exact frozen text. Dispatch every event `refs` entry by `Ref.kind`, never by position, through the host reader with `purpose='user_view'` only. Preserve event order and per-event ref order.
- TSK state via `get_work({goal_id, revision?})` — the exact C02 request shape.
- Structured result: `{work:{goal_id,revision,state}, artifacts:[{ref, body|error}], verifications:[{ref, observed_at, usable, checks, artifact_bindings, validity:'current'|'not current'|'source stopped'}], errors:[{ref,code}]}`.
- Cause rule: `source stopped` only when a notice for the same goal names a ref present in that verification's `source_refs`; otherwise `not current`. Plain `invalidated` never infers a cause.
- Per-ref failures (not_found/denied/unavailable) stay in `errors` and render as lines; refs are never dropped or replaced with invented success.
- render() carries `mock model`, `structural verification` and `read at <ts>` labels; TSK state, historical checks and current usability are separate labeled fields. Stopped history stays visible and is never completion authority.
- Each owner read is its own snapshot; the consumer never claims one atomic snapshot across owners and never issues a model_context call.

## 4. Split, tests, review

- VER side: `read` + optional `clock` in `pal/verification_v5.py`; tests in a new `test_verification_read_v5.py` covering projection bytes/hash stable under clock change and later invalidation, per-purpose usable/denied, not_found, corrupt→unavailable, clock write/commit/raise/malformed→unavailable with rollback and unchanged `total_changes`/dump, interrupt cleanup, reopen, wrong kind.
- Reader/consumer side: separate files and `test_read_consumer_v5.py` covering dispatch and no-fallback kinds, pagination past page_size including pages with no selected events, result discovery after a committed-but-lost response, per-ref error visibility, notice correlation versus plain invalidated, user_view-only proof via a purpose spy, mock/structural/read-at labels, unchanged dump and `total_changes`.
- Different authors and independent reviewers for the two files; approved test files are immutable — behavior changes need new tests, not edits.
- Non-goals unchanged: no schema/migration, live DB, service/UI/provider, model_context activation, auth/cost, retry of unknown calls, owner gates or broad redesign.

## Plan step (instructions <1000B)

```text
Freeze seams; tests before code. VER: read({ref},*,purpose)+optional clock; one
BEGIN..rollback via _stored/_current_status/_guard; content=dumps({work_ref,
conditions,artifact_refs,artifacts:[{artifact_ref,hash,bytes}],source_refs,
checks}); hash=sha256(content UTF-8); observed_at=clock inside txn, outside
content; valid→usable=true; invalidated→usable=false user_view only, denied
otherwise; not_found/unavailable as scoped. pal/host_read_v5.py(memory,artifacts,
verifications): kind dispatch; note/source/receipt→unavailable; bad→invalid_input;
pass purpose. pal/read_consumer_v5.py: bounded get_events{session_id,
after_event_id?}; result+exact notice; kind-dispatch user_view only;
get_work{goal_id,revision?}; structured+render, mock/structural/read-at labels;
keep per-ref errors. Immutable tests; split authors, independent reviewers.
```
