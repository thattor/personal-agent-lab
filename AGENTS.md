# AGENTS.md — Personal Agent Lab v5

## Current owner instruction and development closure — 2026-10-19

This ChatGPT conversation is Controller. Codex CLI, API and agents are prohibited
unless the owner explicitly approves the specific case first, irrespective of
remaining credits. This supersedes historical Codex/40-percent routing text.
No new authentication, service, cost, paid fallback or automatic reload is allowed.
Use only an existing route whose current connectivity and no-extra-cost conditions
have actually been checked. An offline or unqualified route is not an invocation.

A closed loop is one bounded design -> implementation -> independent review ->
verification -> repair -> reverification -> evidence/adoption cycle, not a timer.
Before work, reconcile live head/base/blob identities, current STATE/DECISIONS,
ACCEPTANCE and the latest comments in existing Issue #22 and PR #19/#23.

The work-item exit requires all of the following against the same final source:

1. Fixed functional acceptance criteria and input/output/error/state contracts;
   explicit write ownership, dependency and authorized execution boundaries.
2. The reproduced failure and frozen regression, minimal implementation, and an
   exact source delta. Existing tests and historical evidence remain intact.
3. Actual independent official Claude review of final bytes and contract effects;
   author/Controller self-checks do not satisfy this gate. Changed source makes an
   earlier review stale. Unavailable review is NOT_RUN, never implicit approval.
4. Supported Python3.13 full unittest and ask/change/readback mock E2E, original
   commands/exits/logs, explicit skip reasons, and repaired-source hosted evidence.
   Failure, timeout, missing output or incomplete evidence cannot count as PASS.
5. Source archive/tree, environment, logs and hashes saved in existing evidence
   and Issue/PR lanes; verify the publication head and artifact bytes by readback.
6. Controller disposition and next dependency recorded in the existing judgment
   records. A blocked item stays open; proceed only with genuinely independent
   authorized work. Do not repeatedly rerun unchanged tests or repackage evidence.

CI proves source/fixture behavior only. CI cannot certify independent review,
qualify a real provider, grant operation authority, accept authentic usefulness or
complete Stable-1/PAL. Missing product evidence keeps those goals NOT_MET.
No PR19 adoption until original EXE01 reconciliation, independent review and exact
source tests all hold; no main mutation, force push, deployment or release.

Parallel work requires disjoint write sets and state owners, fixed shared
contracts and no unresolved duplicate invocation. EXE02 read-leaf work and
connection-test work can be isolated. Controller serializes common contracts,
TaskStore/DB seams and final integration. Preserve the original isolated EXE01
worktree and all UNKNOWN calls; do not retry, overwrite, kill or force-release them.

## Work-item sizing — owner instruction 2026-10-19

Milestones retain their user-visible acceptance promise; do not use a milestone
or umbrella Issue as an implementation assignment. Existing Issue #22 tracks
linked small Issues in the already-active Stable-1 milestone; future PROPOSED
milestones are not activated. Preserve parent acceptance and historical evidence.

Each assigned unit has one behavioral objective, explicit dependencies, fixed
input/output/error/state contracts, one write owner, exact changed paths, a
frozen regression and a separately reported review/test/adoption disposition.
Use an active-work budget of at most 60 minutes as a splitting trigger, not a
promised delivery time. Aim for at most two implementation files and 200 changed
implementation lines, excluding tests/evidence. Split earlier when it crosses
owners/contracts; split oversized work before dispatch rather than weakening
acceptance. A unit can have multiple assertions for its one behavior.

Apply a known minimal remedy after reproducing it; do not keep reporting the same
solvable finding or ask the owner routine technical questions. A blocked provider
or original-source dependency blocks only dependent units. Disjoint read/review
or write scopes may proceed in isolated workspaces; shared files/DB/contracts
and final integration remain serialized. No duplicate unknown dispatch.

Implemented, tested, independently reviewed and adopted are different states.
Code Issues remain open until their required exact-source closure gates pass.
Child completion never substitutes for parent integration or product acceptance.

## Current source of truth

Before starting, resuming or stopping, read the current sections of [STATE.md](STATE.md)
and [DECISIONS.md](DECISIONS.md), and reconcile the latest owner instruction with
exact source/evidence. These are the existing project judgment records; do not
create another authority file.

Current interfaces: [PAL-contracts-v5](docs/design/contracts-v5/PAL-contracts-v5.md)
and the applicable frozen scope in `docs/design/contracts-v5/`. Current scope and
latest explicit decisions govern older proposal headers and historical checkpoints.
[ACCEPTANCE.md](ACCEPTANCE.md) records evidence, not new authority. SPEC.md and
DESIGN.md are concise current pointers; their old bodies are retained history and
are not mandatory model inputs. Use [CODEX-PROMPT.md](CODEX-PROMPT.md) for development.

## Work boundaries

Use Python standard library only. Mock is the default. No new OAuth/auth, billing,
service, provider invocation or unrelated project change is authorized by these
documents. Follow actual current model-route assignments and approved alternatives
in STATE/DECISIONS; do not revive superseded routing or quota instructions.
Preserve old evidence, DBs and unknown native/CO outcomes. No unknown-call retry,
resume/cancel, forced lease release or old DB migration without current authorization.

Root owns shared contracts, canonical records, integration and publication.
Respect isolated write assignments and exact frozen fixed tests. Source authors'
self-checks are not independent reviews. Do not weaken criteria to obtain PASS.
Do not read/reuse old PAL implementation or preserve backwards compatibility.
Historical docs/receipts remain evidence, not active specifications or startup paths.

## Verification and reporting

```sh
python3.13 -E -s -B -m unittest discover -s tests -v
```

Retain all current v5 tests, including unsuffixed probes. Use disposable fixtures
and existing current v5 demos/lifetime verifiers for bounded local verification.
Report exact source, actual command/exit/count, findings and remaining limits.
Distinguish source approval, local mock/fixture proof, real transport qualification,
operational adoption and authentic human usefulness. Current HTTP/UI retains
LOCAL_MOCK_VERIFIED and LOCAL_NATIVE_FIXTURE_VERIFIED proof; C097 private-failure
source verification is full1037/exit0. Genuine native UI,
real qualification/usefulness and whole goal remain
NOT_MET. Use the existing Python3.13 interpreter for local verification; a Python3.9
StrEnum import failure is not a product regression.
Global guidance and saved owner instructions remain independently applicable.


## Latest owner clarification D060

CO is one development means, not a mandatory product or implementation condition.
Use approved direct alternatives when appropriate; do not promote one CO-native
profile's version/receipt limitation into a universal PAL stop. Conversation and
composition intelligence/quality remain delegated to the model under D031/D033:
no prose grading, style corpus, model judge or quality release gate. Functional
I/O, permissions, budgets, work state, controls, saved bytes and replay still need
verification. A new direct profile needs its own explicit source/functional proof;
this clarification does not permit new auth/cost/service or old UNKNOWN operations.
