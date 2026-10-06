# STATE.md

## Goal
Reach Stable-0 as defined in ACCEPTANCE.md.

## Current phase
Bootstrap / Slice S1: canonical store and core state machine.

## Last green commit
Repository bootstrap only. Product code not yet implemented.

## Next actions
1. Create minimal Python project and deterministic test harness.
2. Before choosing persistence/transaction details, consult Devin SWE-2 High and record the conclusion in DECISIONS.md.
3. Implement canonical Record/Goal/Attempt/Receipt/Event-Outbox store and transition tests.
4. Continue through S0 acceptance rows without waiting for additional UX discussion.

## Blockers
None currently known.

## Deferred until after Stable-0
PublicSearch live, time wake, topic proactive suggestions, differential dreaming, multi-Expert, vector DB, automatic procedure updates, local inference, external push delivery.

## User-interruption triggers
Only new auth/permission, extra cost, external/public exposure, or a required contradiction of accepted product behavior.
