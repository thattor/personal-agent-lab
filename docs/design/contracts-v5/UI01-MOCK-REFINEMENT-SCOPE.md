# UI01/2 — apply the C088 Opus design findings before acceptance

Root freeze,2026-10-10. Supersedes the specific lifecycle/queue points in UI01/1;
all current owner/HTTP/stdlib/mock-only/no-old-code limits otherwise continue.
The base contains C088 current-only deletion and full930:69c6 ->0e5cdf0 ->fff19cc
->01ae956. Initial source prototypes are not accepted integration. Baseline full
is930 plus new model/UI cases, with original current cases unchanged.

Opus's exact document review is C088-NEXT-SCOPES-OPUS.md. Root adopts U1-U6 with
concrete below. The already pinned demo grant0operations/6steps/6models and shared
host20/20 clarify its earlier supplied scope, without adding external authority.

1. Use private mkdtemp and explicit removal only after close(timeout) returns true.
   No implicit TemporaryDirectory finalizer. Worker is owned daemon; an unresolved
   callback leaves DB/guard held. Expose readonly database_path for disposable
   fixture verification only, never HTTP. Demo exits nonzero with a pathless hold
   notice if close cannot finish; no forced model/unknown cleanup.
2. Bound active+queued progression reservations to16. Reserve before Primary.submit
   could store a new record/turn; preadmission full returns HTTP503/unavailable
   without owner mutation. Release reservation for replay/conflict/owner refusal,
   exception and ended worker. Reserve before a progression control too. Pause,
   cancel/source-stop have no progression-slot dependency and stay responsive.
   Same-key replay/conflict never dispatches duplicate inference. A preadmission
   capacity refusal is transient and must not pretend to be a stored owner result.
3. Closed triggers: a newly accepted turn (including C01 bound-answer text), or a
   successful C10 resume/structured answer. Each schedules at most one existing
   run_turn/run_once, never a loop. Poll/inspection/reference-stop/pause/cancel do
   not schedule. Browser answers remain plain C01 turns; the mock Primary uses its
   exact snapshot.record_ref and only a single disclosed question, never body-match
   heuristics/private SQL/new receipt APIs or guessed latest work.
4. All responses add nosniff,no-store,no-referrer and CSP default-src/script-src
   self,frame-ancestors/base-uri/object-src none. Data uses textContent. UI displays
   plain Japanese state/reply/question/result and controls, not internal JSON as
   the main flow; mock/provenance/availability notices remain useful and visible.
5. Owner Result outcomes, including owner refusal, return HTTP200 with their actual
   envelope; transport/route refusals return4xx, bounded capacity admission503.
6. Distinct-context independent tests and independent source review are required
   before integration. Source author never edits those tests. Current C05/TSK
   invalidation after in-flight reference stop advances epoch/drains to queued;
   preserve actual owner state and fence late output. The mistaken failed-state
   fixture is corrected independently with original failure retained, not by
   rewriting owner status or weakening late-result checks.

Independent additions must prove held DB/guard retained then cleanup after exit,
queue saturation with no new stored input, and response headers. Root final full
and browser check follow separate source approval. This remains local mock/UI
preparation, not real native/model/semantic/human usefulness or whole-goal PASS.
