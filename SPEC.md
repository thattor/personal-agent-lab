# SPEC.md — Personal Agent Lab product scope

## Goal
Overall destination: one personal conversational assistant that remembers relevant context, accepts authorized work naturally, prepares reversible results within explicit limits, survives interruption, verifies outcomes and returns results/blockers/genuine human decisions without requiring the user to manage internal tasks. Stable-0 is the released minimum core, not the whole project.

G-001/D-022 manages that destination through project→milestone→Issue goal/evidence loops. [P-001 v1](docs/plans/P-001-v1.md) proposes the overall phased completion envelope and prospective G-P01–04; human adoption is pending. D-021 Stable-1 remains the independently approved current scope. Future milestone registration is planning, not implementation authority.

Stable-0 is intentionally smaller than the broader M1/M2 roadmap. PublicSearch, scheduled wake, proactive topic suggestions, and memory dreaming remain accepted future work but are not Stable-0 blockers.

## Core user value
The user can naturally say things such as:
- remember this;
- I need to reply to that;
- make a draft, do not send it;
- what happened with the previous thing?;
- stop that;
- forget that.

PAL should preserve the thread, do reversible preparation proactively, and return when there is a result, a real blocker, or a decision that genuinely needs the user.

## Required behavior

### Conversation
- A normal conversation does not automatically become a Goal.
- Conversation remains usable while an execution Attempt is running.
- Control messages for a running Goal are accepted without waiting for the Attempt.
- A new unrelated task may queue if the single task execution slot is busy; conversation still responds.

### Memory
- Store secret-sanitized raw conversation records broadly.
- Maintain lightweight derived notes/index/source references for recall.
- Current Goal/approval/progress state comes from canonical state, not memory summaries.
- Corrections supersede older information.
- Forget means reference stop, not deletion: raw history remains user-viewable but must not be used for model context, proactive preparation, or derived memory.
- Receipts/audit facts are retained but are not conversational memory.

### Task completion
- Work becomes a Goal with fixed Acceptance Criteria before execution.
- Expert is a thin durable outcome controller: Goal, Acceptance, current state, evidence evaluation, next action.
- Executor chooses local method within scope and returns result/evidence/error; it cannot mark Goal complete.
- Goal completes only when host-side checks verify Acceptance Criteria.
- Model self-report is not proof.

### Logical roles
- Primary: canonical control plane, routing/state/approval/dedupe.
- Responder: conversational response and handoff proposal; cannot mutate routing state.
- Expert: durable outcome owner with minimal control logic.
- Executor: execution owner within WorkOrder scope.

Initial physical implementation may colocate responsibilities, but model/Executor capabilities must not include canonical-state mutation.

### Reversible proactive work
- Reversible preparation such as a local draft may proceed without asking.
- Explicit limits such as record only, not yet, or only this far override proactive work.
- Irreversible/external actions are classified by a host-side policy table, not Executor self-report.
- Explicit approval is bound to a concrete action fingerprint and current Goal revision. A later revision invalidates old approval.
- Stable-0 happy path uses local reversible artifacts; real external send/publish/purchase is not required.

### Persistence and recovery
Persist at minimum: Record, MemoryNote/source refs, Goal, fixed Acceptance, Attempt, host Receipt/Evidence, Event/Outbox.

Canonical writes go through one store boundary.
Goal transition plus corresponding outbox event must be transactionally consistent.
Duplicate client messages/results must not create duplicate effects.
Late results from stale revisions/epochs are rejected.
Crash-ambiguous external effects are unknown and are not blindly retried.
Input/result wake resumes the same Goal exactly once.

### Provider
Stable-0 needs one real model-provider smoke path using an already-authorized official connection with no additional charge.
The provider is selected after capability/cost verification.
Mock/provider fixtures remain separate from live evidence.

## Initial implementation direction
Preferred starting stack: Python 3.11+, SQLite, FastAPI/Uvicorn, minimal HTML/JS, pytest.

Start with a single user, single host, one conversation lane and one task execution slot. Do not hold DB transactions while waiting for model output.

## Stable-0 DEFERRED
These are not removed from the project; they are outside Stable-0:
- live PublicSearch;
- time/scheduled wake;
- proactive topic suggestions;
- differential dreaming/background memory consolidation;
- iPhone UX polish beyond existing private access;
- multiple Experts and dynamic multi-agent allocation;
- vector database;
- automatic procedure/workflow updates;
- local llama.cpp/MLX-LM inference;
- guaranteed external push notification delivery;
- arbitrary shell/repo/browser execution by product Executor.

## Non-goals
Stable-0 does not promise perfect recall, perfect secret detection, exactly-once arbitrary external side effects, host-compromise resistance, or automatic deletion from external backups/services.

## Revised completion — D-019
Stable-0 requires functional real-provider UI acceptance for conversation, remember/recall, context-grounded useful draft content, correction, reference-stop and authoritative work/status controls, in addition to canonical/security/recovery protections. Mock remains default; real-provider UI is explicitly selected and bounded by fresh official no-extra-charge proof. Human evaluates usefulness once for the fixed scenario set. Long-term observation is optional; no long-term stability claim follows these finite scenarios.

## Position and next milestone — D-021

The product destination is an assistant that preserves conversational context, takes on authorized work, prepares reversible results, verifies them, and returns only for results, blockers or genuine human judgments. This is a capability direction, not a promise of every possible task or a completion percentage.

| Stage | User-visible outcome | Current authority/status |
|---|---|---|
| Stable-0 | Conversation, remembered context and local drafts with host evidence, control/recovery safeguards and bounded official real-provider proof | Released; required S0/F0 PASS under D-019. Finite personal-use validation, not always-on or long-term reliability proof |
| Stable-1 | Japanese draft requests are distinguished from conversation/deferral; correction/cancel act on the intended work or ask which one | Next scoped milestone adopted in D-021; implementation and acceptance NOT_RUN |
| Stable-1.1 candidate | Ask only for essential missing content and resume from the bound answer | Later design candidate; not part of Stable-1 |
| Later candidates | Better relevant cross-conversation recall and richer reversible preparation, then separately authorized information/action integrations and proactive help | Deferred; each needs concrete value, scope, cost/permission review and acceptance before implementation |

Stable-1 adds no task type beyond a local draft. Combined draft-and-send and send-only requests receive an explicit unsupported-action explanation with no Goal; a subsequent local-only request can create one. Discussion, quotations, hypothetical requests, record-only instructions and negation/deferral must not silently create work. Natural correction/cancel requires unique host-validated targeting; ambiguous references must not mutate an arbitrary latest Goal. Existing single-target English controls remain supported, with fixed criteria and source restrictions preserved. Forget remains explicit and reference-stop semantics remain unchanged.

The existing recent30-record/first20-note context assembly is a known bounded implementation limitation. Stable-1 does not overhaul memory or claim unlimited recall. Official-provider proof freshness, finite invocation budget, mock default and human judgment boundaries remain D-020. No schedule or paused follow-up is restarted by setting this milestone.
