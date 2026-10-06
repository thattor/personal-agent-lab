# STATE.md

## Goal
Reach Stable-0 as defined in ACCEPTANCE.md. Stable-0 is **incomplete**.

## Current phase
S1 core + S4 controls/memory + S5 transaction crash tests green; runtime integration is next, not soak-ready.

## Working checkout
`/private/tmp/personal-agent-lab-stable0-20261006`, same private GitHub repository, remote `origin`. Initial supplied workspace had no HEAD/remote or required new documents; preserved unchanged. No old implementation was reused.

## Last green increment
S1: canonical SQLite store, immutable acceptance versions/revisions, host-issued bounded blob receipts, global task slot, controls/reference manifest gates, transactional outbox. 20 tests PASS including 18 SIGKILL boundary subcases: [log](evidence/tests/s1-controls-crash.txt), [versions](evidence/tests/s1-version.json). Commit is the commit containing this entry.

## Next actions
1. Integrate SWE-2 runtime review (in flight), then add deterministic concurrency and capability tests.
2. Consult SWE-2 High on concrete two-lane worker/provider contracts before implementing runtime.
3. Implement independent conversation/task lanes and bounded product Executor capabilities.
4. Complete live no-extra-charge provider path, inspect/UI evidence, then start 72-hour soak only after S0-01–12 PASS.

## Acceptance status
No full acceptance row PASS yet. S0-04–09 have partial core evidence only; live, UI, fault and full integration gates remain.

## Blockers
None currently requiring user action. Reviewer routes verified and used: D-011/D-012. No new auth/payment/public exposure.

## Deferred
PublicSearch, time wake, proactive topics, Dreaming, multi-Expert, vectors, local inference, automatic procedure updates, external push.
