# STATE.md

## Goal
Reach Stable-0 as defined in ACCEPTANCE.md. Stable-0 is **incomplete**.

## Current phase
S1–S5 host core integrated; independent conversation/task lanes and negative capability tests green. Live adapter/UI and remaining evidence next; not soak-ready.

## Working checkout
`/private/tmp/personal-agent-lab-stable0-20261006`, same private GitHub repository, remote `origin`. Initial supplied workspace had no HEAD/remote or required new documents; preserved unchanged. No old implementation was reused.

## Last green increment
S1: canonical SQLite store, immutable acceptance versions/revisions, host-issued bounded blob receipts, global task slot, controls/reference manifest gates, transactional outbox. 33 tests PASS including 21 transaction SIGKILL subcases and worker death-before-apply: [log](evidence/tests/s2-runtime.txt), [versions](evidence/tests/s1-version.json). Commit is the commit containing this entry.

## Next actions
1. Implement reviewed tool-free official native provider adapter and test timeout/output/group cleanup.
2. Add loopback conversation/read-only inspect UI, language/control and browser smoke.
3. Complete live no-extra-charge provider path, inspect/UI evidence, then start 72-hour soak only after S0-01–12 PASS.

## Acceptance status
S0-02/04/05/06/08/09/11 PASS with automated evidence. S0-01/03/07/10/12/13 incomplete. No live provider or browser evidence claimed.

## Blockers
None currently requiring user action. Reviewer routes verified and used: D-011/D-012. No new auth/payment/public exposure.

## Deferred
PublicSearch, time wake, proactive topics, Dreaming, multi-Expert, vectors, local inference, automatic procedure updates, external push.
