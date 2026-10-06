# DESIGN.md — Stable-0 architecture

Status: accepted baseline. Design changes require Opus review before adoption.

## Architecture
PAL uses 2 operational bots / 4 logical responsibilities:
- Primary Bot = Primary + Responder
- Expert Bot = Expert + Executor

The separation is logical and capability-based, not a requirement for four daemons or four LLM calls.

### Primary
Deterministic control plane where possible. Owns ingress/egress, canonical state transitions, routing decision, approval binding, idempotency, and outbox.

### Responder
Builds conversational output from Context Builder and may emit a structured handoff/control proposal. It cannot directly mutate routing or Goal state.

### Expert
Thin durable outcome controller. Owns Goal, fixed Acceptance Criteria, Attempt history references, result gate, and next action. It should not duplicate Executor planning.

### Executor
Receives a WorkOrder containing Goal/revision/epoch, scope, allowed capabilities, relevant context, criteria, and budget. It plans/acts/retries locally within that envelope and returns structured result/evidence/error.

## Canonical state
Minimum entities:
- Record
- MemoryNote
- Goal
- AcceptanceCriteria, embedded initially only if immutable/versioned
- Attempt
- Receipt/Evidence
- Event/Outbox

Avoid Job/DAG abstraction until a real need appears. Run and Attempt are one concept: Attempt.

## State ownership
Models/Executors do not receive canonical DB write capability. They return structured proposals/results. Host code validates and writes.

SQLite has no GRANT/REVOKE isolation. Do not pretend an SQLite role secures an arbitrary-code Executor. Stable-0 therefore uses host-mediated capabilities and does not expose arbitrary shell/filesystem/native search to the product Executor.

## Evidence and finish
Acceptance Criteria are fixed before an Attempt and versioned with the Goal. Executor cannot change them.

Evidence authority:
- host observation/receipt;
- artifact bytes/hash/structure read back by host;
- limited semantic check when a criterion is semantic.

Check results are pass, fail, or unverified. Unverified never becomes pass automatically.

## Memory and context
- Raw records remain source evidence.
- MemoryNote/index is derived and regenerable.
- Context Builder selects current conversation/Goal, small relevant notes, and source excerpts.
- Important negation, condition, correction, or conflict causes source re-read.
- Forget marks source references unavailable for AI use; raw history remains.
- A shared read boundary enforces reference-stop for context and derived memory.
- Audit receipts remain retained but are not automatically fed back as memory.

## Conversation while working
Conversation and task execution are separate runtime lanes. A slow task must not hold a global lock or DB transaction.

A new user message is persisted and can receive a Responder answer while an Attempt is blocked. Control commands affecting a Goal are committed immediately. A new unrelated Goal may queue behind the single task slot.

## Approval and irreversibility
Host policy classifies capability/action classes:
- read-only;
- reversible local preparation;
- irreversible/external/high-impact.

Executor self-report is not authoritative classification.

Stable-0 uses a local draft as the representative reversible action. Real irreversible operations are not required for the happy path. If an irreversible operation is ever exposed, explicit approval must bind to action fingerprint plus Goal revision.

## Recovery
Use idempotency keys and revisions/epochs:
- duplicate ingress/result => no duplicate effect;
- cancel/correct/reference-stop => update relevant revision/epoch;
- stale result => never apply to current Goal;
- crash after commit => replay outbox safely;
- crash with ambiguous external effect => unknown and reconcile before retry.

## Learning
Record successes/failures/corrections as evidence. Formal procedure/workflow/playbook changes require human approval. Automatic procedure promotion is outside Stable-0.

## Stable scope review
Opus review on 2026-10-06 concluded that minimum stable should exclude external-dependency/polish items from the broader M1 roadmap. Stable-0 therefore keeps restart/dedupe/stale-result defense, cancellation, correction/reference-stop, conversation during work, input/result resume, one no-extra-charge provider smoke, automated tests, and a 72-hour soak. PublicSearch and time wake move to post-Stable-0.

## Design review rule
If implementation pressure suggests changing any semantic above, pause that change, obtain an Opus review, record the decision in DECISIONS.md, then continue.
