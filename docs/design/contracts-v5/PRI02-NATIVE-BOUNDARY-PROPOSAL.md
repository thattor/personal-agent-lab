# PRI02 native boundary — proposal, not adopted

Input: PAL `cca97cda0537d1bc4c13d79f0c30fd5a192c6c66`; Primary source
`d9f0e12de2db00a24e502dbe06acbf8843ce9be6`, SHA256
`81a5ec8b6c65fce3b6aa5f76b0cd0430d4914ea972ea1740a16100842d99bfec`.
Also read Root's pending PRI02-CONSULTATION-REQUEST.md and committed provider
proposal. C081 acceptance and new consultation are Root-owned. This note neither
freezes a profile nor authorizes an inference. No source, DB, provider, CO state,
configuration or shared contract was changed. Only this note is authored.

## Recommendation and actual interface limit

Use two explicit gates: (1) one synthetic, bounded single-attempt transport proof
with zero owner effects, then (2) a separately frozen native Primary integration.
The latest consultation request's one call supersedes the earlier provider
proposal's suggested three-call experiment. Neither proves authentic usefulness
or a real Expert loop. Existing PRI state and owner routing should be reused;
a second execution engine is unnecessary.

Root forwarded Sol's independent public-API inspection: CO0.4.5 exposes no
supported single-text CLI. `DevinTextHost(config).make_adapter()` and
`verify_text_cessation(...)` use actual qualified host configuration, conditions,
scope and AcpTransport completion/EOF/owned-wait evidence. `DevinTextRoute`
requires ControllerState/Attempt. NativeCandidates/infer_selected selection and
before_launch metadata do not themselves certify text cessation. The fixed
expected-response canary is distinct from arbitrary dynamic JSON. These are
reported API facts, not APIs independently re-read here or actual invocation.

Consequently an external standard-library subprocess/JSON boundary is a proposed
connection requiring its own qualification; existing module presence does not
qualify a new wrapper. PAL must not silently import co_v4, invent a supported CLI,
or count an opaque multi-call `task run` as one model unit. Root/Opus must select
an exact existing supported qualification path before coding or calling it.

## Minimal owner split

* Primary continues to own turns, immutable admission/snapshot/call/intent/outcome
  bindings, original owner keys, source gates, receipt-only restart and C14.
  Current `_binding` hardcodes the mock profile (primary_host_v5.py:184–188);
  supporting native therefore needs an explicit profile distinction, not a
  Python callback wrapper substituted into the existing mock constructor.
* TSK remains the sole finite shared model-counter owner. Its workless Primary
  reservation validates session and original reserve/consume records
  (tasks_v5.py:993–1044). This proves allowance and local ownership, not native
  entry/cessation. No fictional Goal lease or second model counter. Retaining
  this locally managed reservation for native requires an explicit contract
  clarification separating local allowance profile from native call profile.
* HOST lock/check_connection/activity prove local DB/process lifetime only
  (mock_host_v5.py:203,275). They can bound local admission and callback activity,
  but cannot certify a subprocess or remote inference stopped. Existing mock
  TSK recovery and MockRunner remain qualified only for their existing mocks.
* A trusted external single-attempt adapter owns native invocation and ending
  evidence. Model JSON cannot select profile, model, budget, call identity,
  ending, or proof. Its result must separate model-produced text from host
  completion facts. Exact public wrapper shape remains unresolved until the
  existing host API and dynamic-output qualification are adopted.

No `proof=True`, caller-selected profile string, PID-only check, or cryptographic
attestation framework. Hashes bind trusted local records consistently; they do
not establish authority against coordinated tampering or a hostile host.

## Required lifecycle delta

Before any possible provider entry, commit the original PAL turn/call/reservation,
local session/nonce, native profile/version/effective route, exact request hash,
and single-attempt identity. Source exposure is rechecked at admission as today.
If the external API creates identity only after starting, precommit a PAL attempt
identity and bind the returned external identity to it; failure in that gap is
unknown, never fabricated never-entered. No await or native wait inside SQLite TX.

Keep current returned-output parsing and owner checks, but require a trusted
ending before output can become an adoptable returned call:

| Observed native fact | Durable meaning and next action |
| --- | --- |
| Qualified original request completed, exact output correlated, required EOF/drain and owned wait observed | returned; bind output/evidence digest; closed WIRE and source/owner checks still required |
| Bound evidence establishes entry never occurred | not_entered; terminal failure permitted; consumed budget stays spent |
| Timeout, transport exception after possible entry, response loss, parent death, kill/reap, or EOF without qualified completion | admitted/unknown held; no effect, retry, refund, inferred completion, or automatic new call |
| Known completed output is malformed UTF-8/JSON/WIRE | known ended invalid output; closed failure, no repair inference |
| Known returned output produced applying intent, owner receipt uncertain | preserve applying and original owner key; lookup only, never redispatch |

A bare exception is not native `raised` cessation evidence. A normal CLI exit is
also insufficient without original request/result correlation and the qualified
route's completion requirements. Remote cessation claims must stay within that
route's actual documented proof, not provider-global certainty.

An external completion record must be recoverably bound to the original native
attempt if restart adoption is supported. It is not established that existing
in-memory proof objects are serializable/revalidatable. If the public route
cannot validate durable evidence independently after parent death, retain this
commit gap as held; do not invent a proof token or rerun the request to recover it.

## Startup, current controls and history

Current recover_turns (primary_host_v5.py:825–856) sends any non-applying orphan
to interrupted, and `_terminal` atomically converts a foreign admitted call to
interrupted (656–694). This is correct only for the qualified in-process mock.
Native profile dispatch must occur before that branch. Unknown native entry can
never reach the mock interruption rule merely because a new guard holds the lock.
Keep the existing exact mock behavior; reject missing/contradictory profile data.

Minimum first native profile: refuse new native inference while any unresolved
native admission exists, across connections and restarts, including the current
session. Existing `_ready` (239–245) only blocks foreign-session active turns;
it is insufficient alone for same-session native uncertainty. This is an admission
check, not a lock around control/read transactions. Immediate structured controls,
source stops, history and receipt lookup must remain available while native waits.
No implicit unlock by deleting a turn or assigning a new local session.

Known immutable returned/applying records may use current original-key owner
lookup (`_dispatch`,619) and source-gated history. Missing receipt does not permit
re-dispatch after restart. Bound returned output without an applying intent need
not acquire a new inference: a conservative first slice can close failed adoption
without applying effects, or hold on uncertain persistence. Define its status
explicitly rather than reuse a name implying remote interruption. Terminal ending,
outcome and C14 must commit atomically; append failure rolls all of them back.

Source stop cannot retract a prompt already exposed remotely. Preserve full actual
exposure closure, including uncited visible candidate dependencies, and recheck
before reply/effect adoption. Withheld metadata is not body provenance or select
authority. Controls racing native execution keep current owner precedence; native
completion cannot revive stopped records, old WorkRefs or revoked Grants. Existing
historical owner receipts remain factual even when their reusable text is withheld.
Local raw evidence stays local under D045; minimized hashes/statuses suffice for
public validation records. No copied provider reply becomes MEM/C14 context.

## Fixed acceptance before integrated native use

1. One actual attempt, exact effective model/route/version and finite output/time;
   no hidden planning/repair, fallback, extra charge or new authentication.
   Synthetic canary and dynamic PRI JSON qualifications are reported separately.
2. Before-entry failure, response loss after admission, post-launch timeout and
   parent death: exact original ledger remains, no duplicate invocation or refund.
   Reacquired OS lock must not settle native admitted as mock interrupted.
3. Mutate each request/call/reservation/session/profile/completion binding;
   refuse adoption and inference. Replay unchanged records without spending again.
4. Same-session and restarted unknown admission refuse another native entry,
   while a second connection can control/stop/read without awaiting provider IO.
5. Known completion plus invalid output closes safely; source stop after exposure
   suppresses reply/effect. Test stop-before-admit and stop-before-adoption barriers.
6. Applying receipt present/missing/unavailable, owner commit then response loss,
   and C14 append failure: no redispatch, no reinference, atomic terminal settlement.
7. Exercise actual external transport completion/EOF/wait and unknown paths;
   local doubles validate PAL logic only. Root's full mock regression still must
   preserve PRI01, TSK and Expert mock contracts.

## Root/Opus decisions still required

Select the supported qualification entry and whether it can accept dynamic JSON
without treating canary success as output proof. Freeze exact native profile,
trusted adapter evidence shape and durable revalidation limits; settle the
known-return-before-intent crash status. Explicitly adopt local workless budget
reuse and unresolved-native admission refusal. These are technical contract
choices, not new routine human-permission gates. No received Opus endorsement is
claimed. Until resolved, a standalone one-call transport experiment cannot be
reported as integrated Primary or product completion.

A later real Expert needs its own call/lease/cessation and saved-tail contract.
Passing it into MockRunner would incorrectly inherit in-process recovery proof;
that connection is deferred, not silently included in this Primary slice.
