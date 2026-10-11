REFINE — ART01-bind/1 is implementable on current TSK/RUN; nine corrections required. Two close defects in existing code (R1, R2) that the binding doc must state explicitly.

Scope reviewed: ART01-BINDING.md against tasks_v5.py (TSK02/1), mock_runner_v5.py (RUN01/2), intake_v5.py, memory_v5.py, contracts_v5.py, ART01-SCOPE.md, PAL-contracts-v5.md, RUN01-RELIABILITY.md. The in-progress storage implementation was not consulted.

## Aligned (keep as written)

- Same-TX read-only `inspect(connection, {'ref': ...})` matches the existing collaborator pattern (`_require_transaction`, savepoint, `total_changes` in `_check_sources`/`_callback`). ART owns no BEGIN/COMMIT and writes nothing.
- Retry only idempotent local save/get_by_key/finish on `unavailable`, bounded (3 attempts, existing `persist` helper), never the callable — matches RUN01/2. `finish_step` replay is already keyed by `step_id`, and `_transaction` replays before authority rechecks, so a committed-but-lost finish returns its stored result without duplicate effects.
- Control fencing before save and between save/finish holds: `_authority` maps pause/drain to `conflict` and cancel/epoch advance to `stale` inside both `authorize_artifact_save` and `finish_step`.
- `release` marks every started step `abandoned` in one transaction; abandoned steps can neither re-save (`authorize_artifact_save` requires `started` → `conflict`) nor finish post-release (`stale`/`denied`), so a committed save degrades to history exactly as specified.
- Re-input stays closed with no changes: MEM `source_gate`/`read` return `unavailable` for non-record kinds, so artifact refs in Brief.context_refs or register_sources already fail.

## Required corrections

R1 — step_sources must tolerate the artifact ref (blocking). `get_execution_context` currently requires `call sources ∪ result_refs ⊆ v5_intake_source`; a finished compose Step carries `result_refs=[A]` and A is never registered, so every later run fails `unavailable` — a permanent wedge, not transient. Doc must state: the subset check applies to non-artifact refs only — `unavailable` iff any ref outside the registered set has kind ≠ `artifact`; `required ⊆ refs` unchanged. Keep A inside reported `step_sources` so the runner's `sources <= available` filter still conservatively omits that Step. Do NOT register A in `v5_intake_source`: it would surface in `optional_refs`, `memory.read(A)` → `unavailable`, the run fails, and closed re-input is violated. Mapping: unregistered record/non-artifact → `unavailable`; artifact → permitted. Test: compose finish → yield → new claim; `get_execution_context` ok, `excluded_step_ids` contains the compose step, a following report step completes.

R2 — get_work projection (blocking). `IntakeStore.get_work` hardcodes `current_artifact_refs: []`. Add TSK-owned append-only `v5_tsk_artifact_set(goal_id, revision, seq, artifact_id)` written inside the finish TX; `TaskStore.get_work` selects refs ordered by seq for the returned (goal, revision); absent rows → `[]` (earlier work). Corrupt stored row → `unavailable`, never silently dropped. Test: finish compose → get_work returns exactly `[artifact_ref]`; an untouched revision → `[]`.

R3 — inspect invocation guard. The doc requires a same active connection and forbids writes/transaction control but not the enforcement. State that TSK wraps the callback exactly like the source gate: `_require_transaction`, `SAVEPOINT`, call, assert still `in_transaction`, `RELEASE`, `total_changes` unchanged, strict six-key Result shape. Ended transaction / mutation / exception / bad shape → `unavailable` with full attachment rollback. Test: fake inspect performing an INSERT → finish `unavailable`; no set row, event, or step change.

R4 — begin_step compose fencing. `begin_step` admits `compose` even with no `artifact_inspect` configured, creating a Step that can never finish. Doc must state TSK rejects compose at begin_step when the callback is absent → `unavailable` (consistent with the existing kind gate), and MockRunner rejects a compose proposal without an ART owner before begin_step → `unavailable`, routing the returned call to yield/retain. Test: begin compose without callback → `unavailable`, no `v5_tsk_step` row; runner without owner → no step created, lease retained.

R5 — dependency equality. "Exactly cover" is ambiguous; require set equality: `inspect.source_refs` (deduped) == the producing call's stored `sources` (deduped) — `authorize_artifact_save` already returns exactly that union. Also verify `call['step'] == step_id`. Any mismatch → `unavailable` (corrupt provenance). Then recheck `_check_sources(deps)`: denied → `denied`, not_found → `not_found`, gate failure → `unavailable`. Test: artifact whose stored deps drop one call source → finish `unavailable`; Step stays `started`; zero writes.

R6 — compose-branch input fencing. result_refs length ≠ 1, kind ≠ artifact, `error` present, `truncated`, or `excluded_refs` nonempty → `invalid_input`, Step untouched. `inspect.artifact_ref` ≠ requested ref → `unavailable`; `inspect.step_id` ≠ step_id → `conflict`; `inspect.work_ref` ≠ request → `stale`; missing artifact → `not_found`; non-returned call → `conflict`, lease mismatch → `denied`, missing call → `unavailable`, mirroring `authorize_artifact_save`. Test matrix: each variant → mapped code, `v5_tsk_step.wire` unchanged, no event.

R7 — get_by_key is receipt recovery only. On save `conflict`/`invalid_input` do NOT consult get_by_key (the stored receipt encodes different input); only `unavailable`×3 triggers bounded get_by_key, and a returned receipt is used verbatim for finish — it never re-authorizes (finish re-fences authority and gate). Test: commit-then-lost save → get_by_key returns the original receipt → finish attaches; exactly one artifact row exists.

R8 — enumerate the atomic write set inside `_transaction('finish_step', step_id, …)`: Step wire `finished` with `result_refs=[A]`, one `v5_tsk_artifact_set` row, `INSERT OR IGNORE` of the record deps into `v5_intake_source` (deps only — never A), one C14 `progress` event with `refs=[A]`, replay row. Any later failure rolls back all. Test: fault injected after the set INSERT → no step/set/event/replay visible; finish retry reproduces the full attach exactly once.

R9 — replay-after-release. A committed finish replayed post-release must return the stored result (replay precedes `_authority` — current behavior, keep). An uncommitted finish retried after abandon → `stale`/`denied`; after `pause` with the same lease → `conflict`. Test: save commit → finish commit-lost → pause → retry returns stored success; vs. save commit → release → retry → `stale`/`denied`, artifact readable only as history.

## Limits

- Attachment is history/projection only: the artifact never enters model context; compose Steps are always excluded from eligible `steps` while re-input stays closed.
- An `unavailable` wedge persists until control/release; no restart adoption, same-call recomputation, or new-epoch re-attach in this slice.
- Single active lease enforced; cross-process safety unchanged.
- get_by_key/read grant no authority; artifact `read` is kind-dispatched readback, not VER.
- Bounded retries are same-process; a crash between save-commit and finish leaves a started step for release/abandon — receipt recovery does not resurrect it.

Excluded per scope: VER/complete invalidation, provider/MOD, general recovery, UI, recursive resolver, extra approval.

Implement step: apply R1–R6/R8 in tasks_v5.py incl. get_work override + set table; R4/R7 runner wiring with optional artifacts owner; consumer tests per mappings; return diff and results.