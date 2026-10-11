# PRI02-N host preparation (proposal only)

Input commit `39d16359c680e1b683caa98c9e1750d118b5aad4`, current Primary
source SHA256 `81a5ec8b6c65fce3b6aa5f76b0cd0430d4914ea972ea1740a16100842d99bfec`.
Read current Primary constructor/call/ending/recovery, HOST local guard and TSK
workless public allowance seams, PRI01 scope, adopted PRI02-T scope and actual
Opus PRI02 report. Root owns N adoption. No source, tests, runtime, model, provider,
DB or shared contracts were changed. Only this preparation note is authored.

## What can be reused, and what cannot

Keep Primary submit/run_turn/get_turn/recover_turns and all current owner routing,
source/fingerprint checks, original receipt lookup and C14 transaction handling.
Keep TSK's one workless model reserve+consume and shared host counter. Keep the
HOST OS lock and activity permits as local process/connection ownership only.
Do not introduce a Goal lease for Primary, a second counter or another engine.

Current constructor accepts any callable but labels all sessions/turns/calls
managed-inprocess-mock/1 (primary_host_v5.py:102–139). _binding requires that exact
profile (:184–188); exception handling marks callback raised (:756–765); startup
converts admitted to interrupted (:656–669,825–856). All three are specifically
unsafe for native substitution. A native callback cannot be passed through the
existing mock constructor and inherit those conclusions.

Use a distinct trusted native adapter entry at construction, mutually exclusive
with the existing mock callable. The exact adapter implementation/profile is
host configuration, not a public/model `proof` flag. Constructor checks profile,
route/model/version/config qualification before any reservation. Persist its
identity in PRI session/turn/call; accept known historical profiles for reads by
profile-specific validation, never reinterpret old mock rows as native. Simplest
first scope: one PRI invocation profile per local host session; mixed profiles
in one session are rejected. Restart can read historical profile records without
admitting their callbacks. No migration or reinterpretation of existing DBs.

TSK's current local session enrollment still uses its mock qualification profile
(tasks_v5.py:13,169–188). Its Primary allowance validates the local guard/session
and receipt, not native inference (993–1044). N must explicitly adopt that
separation; changing the string globally would incorrectly widen Expert recovery.
No native proof is written into TSK private tables. Same public reserve/consume,
one charge, unchanged no-refund semantics suffice once this separation is frozen.

## Native adapter and durable ending

Root reports Sol found a public DevinAdapter observer receiving validated
session/update agent_message_chunk. A stacked observer must preserve host.observe_model
and host.verify/transport/verify_text_cessation. This is a promising reported seam,
not yet independently qualified here; make_adapter alone returns no dynamic text.
expected_response=None cessation does not itself bind the collected output hash.

The native adapter therefore needs one narrow trusted result boundary: original
PAL request binding, exact native request/attempt/session, effective profile,
collected output hash, and verified ending evidence must refer to the same call.
Model output remains just text. Observer checks update session identity, ordered
chunks, accepted chunk kinds/encoding/size, no unaccounted text and completion
boundary. No output is released before original-request cessation verification.
Define whether the protocol supplies a final message boundary or only cumulative
chunks; do not assume the last chunk is a complete answer. If this cannot be
proved using public APIs, N remains unqualified even when Stage T succeeds.

Before possible external entry, persist immutable request/profile/nonce bindings
and a single-entry marker. Reserve/consume only once, with fresh preflight before
reserve and another entry-time drift check. Known preflight refusal costs no
charge; drift after reservation never causes refund or fallback. The entry hook
must durably commit before prompt exposure. The public ACP request-send boundary
must be identified; adapter.execute start is a conservative earlier boundary if
needed. No await or provider wait inside SQLite transactions.

A minimal PRI-owned side row keyed by call_id holds canonical request hash,
profile/qualification digest, native attempt/session binding, entry state and
ending record with output hash. Cross-bind it to the existing call hash. It must
be mandatory for native calls and absent for mock calls. Validate both directions,
strict enums/keys/types and phase converse before use. Deletion, partial ending,
or a one-sided hash/profile mismatch means unavailable, never replay permission.
Trusted evidence hashes are consistency checks, not hostile-host attestation.

Publish returned to the PRI state machine only after the adapter has verified
correlated completion, the N profile's EOF/drain and owned wait requirements,
and its own dynamic output binding. Commit ending side row, returned/output_hash,
turn phase and updated call hash in one PRI transaction. On commit failure keep
admitted/unknown; no retry of the external request. A retained in-process known
ending can retry only that same bounded local persistence operation if adopted.
Do not invent durable proof serialization: restart validation of a raw receipt
needs an exact public verifier or the call must stay held.

An exception after possible entry is unknown even if a Python callback has
returned control or its local process was reaped. No generic native `raised`
ending. Confirmed never-entered can terminate failed; malformed wire after a
verified native ending can terminate failed without another inference. Source
stop suppresses adoption, but cannot retroactively erase the exposed prompt.

Stage T's returned_correlated_export intentionally lacks complete EOF proof and
is NOT accepted as N returned_bound. No ACP or remote cessation is synthesized
from its strict ATIF/exit0/local group-cleanup result.

## Per-turn hold, readiness and startup

Adopt Root's requested per-turn hold, consistent with Opus L4, rather than the
conservative global native block suggested in my earlier pre-consultation note.
An unknown native call remains nonterminal and replaying that turn returns held;
no second entry, re-reserve, re-consume or effect dispatch. A different explicit
submit may proceed with its own allowance, subject to actual transport capacity
and no-extra-cost limits. A provider capacity lease may remain held; PAL cannot
force-release it to implement this readiness choice.

Current _ready (:239–245) blocks every foreign-session nonterminal turn. Replace
only that predicate's native-unknown case with validated, inspectable per-turn
hold; do not broadly ignore foreign active/corrupt mock or applying records.
Startup validates native binding before classification. No mock interrupted
inference runs for native admitted, even if the old HOST lock is now free.
Same-session uncertainty follows the same per-turn rule. Pending/preparing with
no entry can be closed without reinference under separately precise phase rules.
Uncertain marker persistence is held, not inferred never-entered.

Known returned/applying uses current original-key lookup only, never owner
redispatch. Found receipt can settle with current source-gated reply/history;
not_found may close local adoption without declaring the provider interrupted.
Unavailable remains held. Known returned without intent may fail local adoption
rather than infer again. Name the terminal turn result independently of native
call cessation; preserve verified returned status. Never turn unknown into a
terminal ending merely to unblock other turns.

Controls and record stop must remain short owner operations while native waits.
Activity lifetime covers native call and ending attempt, with no DB transaction.
After parent death, the local activity count/lock tells nothing about remote
cessation. Current exposure checks are retained; N1 residual best-effort race for
answer/control/stop is disclosed, while create/change carry atomic full closure.
N2 current-record answer restriction is already enforced by WIRE. No source-gate
weakening or model-created Grant, key, profile or target-authority inference.

## Fourteen meaningful fixed fixture cases

1. Native adapter supplied through mock construction refuses before reserve.
2. Wrong profile/model/version/config or unavailable route before reserve: zero entry/charge.
3. Request/turn/call/reservation/session/nonce mismatch: zero entry, fail closed.
4. Durable entry marker failure: no prompt send; admitted uncertainty is not retried.
5. Two connections run the same turn: exactly one admission and one charge.
6. Valid ordered dynamic chunks plus original cessation proof: exact output hash and one returned transition.
7. Wrong session/chunk order, over-cap/invalid encoding, late chunks or missing final boundary: no adoptable output.
8. Output received without EOF/wait/original completion: unknown, no reply/effect.
9. Timeout, callback exception and parent SIGKILL after entry: held; restarted mock recovery cannot interrupt native.
10. Same held turn re-entry makes no call; a distinct explicit turn may proceed, while actual capacity refusal stays refusal.
11. Side-row deletion/hash/ending/phase tamper: unavailable; no reinterpretation as mock or never-entered.
12. Source-stop barriers before entry and after native return: no stopped-source reply/effect; controls remain responsive during wait.
13. Known-return invalid WIRE and returned-before-intent crash: no repair inference; verified ending remains factual.
14. Applying owner commit/lost response and C14/ending write fault: receipt-only restart, atomic rollback, no redispatch/refund.

Use actual temporary owners for authority/races, plus injected transport facts for
state-machine tests. Doubles do not qualify real ACP/EOF/wait or remote cessation.
Then independently test the actual adapter/profile. Preserve full existing mock
regression and label provider proof versus integrated user value separately.

## Remaining technical decisions before N freeze

Sol's exact observer/verifier surface must establish dynamic-output completeness,
entry gate, environment/tool/cost qualification, bounded cancellation and durable
ending revalidation. Root must freeze exact native profile/side schema, local
allowance qualification, per-turn held view and known-return/local-adoption failure
status. These are contract choices, not extra human permission gates. No new
provider, auth, paid fallback, CO edits, real Expert or service activation follows.
