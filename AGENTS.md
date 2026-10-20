# AGENTS.md — Personal Agent Lab v5

## Current owner instruction and development closure — 2026-10-20

Kosuzu (こすず) coordinates PAL development as Controller and assigns each bounded
unit's author, independent reviewer and integration owner. Any tool or model may
be used within existing contracts and usage allowances when it incurs no additional
cost, including Codex and Claude through direct or indirect routes. Sol, Astra,
Luna, Opus, Sonnet, SWE-2 and OpenCode free ZDR models are examples, not a closed list.
The latest 2026-10-20 owner instruction supersedes conflicting tool/model bans,
fixed-person/model requirements and old routing in STATE/DECISIONS and prompts.
The former 40% remaining-quota floor stays revoked; old unlimited/free periods
do not establish current entitlement. Check no-extra-cost conditions at execution.
Historical approvals remain evidence for their original bytes, not launch grants.
No new authentication, credentials, contract, service, cost, permission/safety
change, paid fallback or automatic reload is allowed. No merge or publication.
Use only an existing route whose current connectivity and no-extra-cost conditions
have actually been checked. An offline or unqualified route is not an invocation.

### Development roles and zero-additional-cost admission

- Controller (Kosuzu): fix one small Issue's acceptance/contracts/write set, freeze the
  exact source, integrate serially, run verification and record the disposition.
- Implementation: any tool/model assigned by Kosuzu with a currently verified
  zero-additional-cost entitlement. A Free catalog label
  alone is not proof that the current account can execute without an upgrade.
- Independent review: any qualified tool/model assigned by Kosuzu within the
  existing no-extra-cost entitlement, in a separate fresh reviewer context. The reviewer must
  not have authored that delta. Fixes invalidate the affected earlier review.
- Fixed regression/connection tests may use a separate qualified worker with a
  disjoint test write set. Controller self-checks are not independent review.

CO 0.3 priority is an existing-route candidate, not a mandatory version or route.
If that route is blocked, choose another existing route with equivalent permission,
account, cost, model and workspace conditions, including an existing direct CLI.
Never bypass a permission denial or start new authentication to force a route.
No fixed model is universally required. Existing/default selection is allowed when
its effective route/model and no-extra-cost boundaries can be verified and recorded.
For OpenCode, check the selected model/provider's current ZDR and training terms,
not just a zero price. Its small_model, title generation, compaction and subagents
must also satisfy the same applicable no-extra-cost/data conditions or be disabled.
No automatic provider fallback, quota refill or paid upgrade is permitted.

Before each bounded dispatch record route/CLI version, exact model, current free
or included entitlement, relevant ZDR proof, no-overage/autoreload settings, source
hashes, isolated write scope and no duplicate invocation. Listing a model is not
an execution or review. After dispatch retain the actual provider/model identity,
original result, usage/cost observations, owned ending and source-bound review;
unavailable evidence stays UNKNOWN/NOT_RUN, not assumed zero-cost success.
This role assignment changes development routing only. It neither replaces PAL's
product provider contracts nor qualifies a real Primary/Expert/UI or old UNKNOWN.

A closed loop is one bounded design -> implementation -> independent review ->
verification -> repair -> reverification -> evidence/adoption cycle, not a timer.
Before work, reconcile live head/base/blob identities, current STATE/DECISIONS,
ACCEPTANCE and the latest comments in existing Issue #22 and PR #19/#23.

The work-item exit requires all of the following against the same final source:

1. Fixed functional acceptance criteria and input/output/error/state contracts;
   explicit write ownership, dependency and authorized execution boundaries.
2. The reproduced failure and frozen regression, minimal implementation, and an
   exact source delta. Existing tests and historical evidence remain intact.
3. Actual independent review on a qualified permitted route of final bytes and contract effects;
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
are not mandatory model inputs. Historical CODEX-PROMPT.md does not authorize execution;
the current owner routing and the assigned small Issue govern development.

## Work boundaries

Use Python standard library only. Mock is the default. No new OAuth/auth, billing,
service, unqualified provider invocation or unrelated project change is authorized by these
documents. Follow Kosuzu's current bounded assignments and qualified alternatives
under the owner instruction above; do not revive superseded routing or quota rules.
Preserve old evidence, DBs and unknown native/CO outcomes. No unknown-call retry,
resume/cancel, forced lease release or old DB migration without current authorization.

Kosuzu assigns owners for shared contracts, canonical records and serial integration.
An assignment does not authorize merge or publication.
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
