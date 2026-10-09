# PRI02 dynamic text seam — read-only analysis

Observed PAL base2a3df54165d529fd1a2acd550c4e4385aef2e865. Read current native-boundary proposal, actual Opus report, and installed CO0.4.5 public source/docstrings. No inference, import/execution of CO, state/SQL/config mutation, provider access, runtime code copy or PAL production write. This is an existing API composition candidate, not T/N qualification or a frozen adapter contract.

## Conclusion

`DevinTextHost.make_adapter()` has no dynamic text result. expected_response=None uses host.transport and publishes status/cessation metadata only; fixed expected_response is allowlisted uppercase1..128 characters, its observation is a canary hash/match, and retained text is cleared. Adapter ResultEvent similarly carries state/reason, not text. The normal NativeCandidates return path must not be called equivalent to this host's completion/EOF/wait proof.

There is nevertheless a narrower existing **public constructor hook** than a new transport engine: `DevinAdapter(..., observe_model=callback)`. In the pinned implementation that callback receives full session-update dictionaries, including `agent_message_chunk`/content, after session identity validation. Stack a bounded local observer with the original host.observe_model, using the unchanged real host.transport and host.verify_text_cessation. This leaves the exact real AcpTransport/DelegatedTransport identity needed by the original verifier intact. No private transport field substitution or synthetic transport is required.

Important limit: this is source-demonstrated reachability of a public callback named model observation, not a documented stable dynamic-text-return contract or actual dynamic-output proof. `make_adapter` itself remains unsupported for returning dynamic text. Root must freeze/qualify the external wrapper against these exact installed bytes before treating its captured text as native C15 output. No supported single-text CLI is established by this finding; PAL must not silently import co_v4 or use opaque task-run as one attempt.

## Exact composition and correlation requirements

An external wrapper can construct one `DevinTextHost(config, expected_response=None)` and one public `DevinAdapter` with host.verify, host.transport, host.verify_text_cessation, plan mode, the same workspace binding and a stacked observe_model. Preserve host.observe_model on every callback, including current_update; do not replace effective-model validation with the text observer. A public verify_host wrapper must call host.verify first and mark the session phase only after it succeeds. In this source, that session phase occurs immediately before the single session/prompt send; earlier buffered creation updates are processed before it. Ignore pre-prompt text rather than associating it with the requested output.

Collect only exact UTF8 text agent_message_chunk content after that phase, bounded by the separately frozen output/drain ceiling; never agent thoughts, user chunks, telemetry, tools or concatenated opaque Result text. Keep collection local to one original ExecuteRequest/Attempt. The adapter already checks update session equality before forwarding fields; the observer callback does not receive the outer sessionId/RPC envelope, so a standalone callback cannot certify its own correlation. Bind its output only to the *same* adapter run whose host issued original cessation evidence. Discard any capture if protocol/model/mode/permission/tool checks fail, if ending is cancelled rather than successful end_turn, or if actual proof is missing. A public transport_factory observer wrapper could expose full envelopes, but is a larger composition requiring independent qualification; it is not needed to establish the narrow callback candidate.

The public verify_host session phase could support a conservative pre-prompt entering marker in a future wrapper, but is not by itself evidence of actual provider entry. ACP queues/writes must be reconciled with the separately frozen E1; a marker-write-to-send gap is unknown, not automatically never-entered. Preflight model/tier/version and PAL reservation order remain Root's profile decision.

## Why original cessation can remain authoritative

Installed anchors (relative to the installed CO runtime, not PAL source):

- co_v4/devin_host.py:87–112: allowlisted fixed response versus ordinary host transport; make_adapter wiring.
- co_v4/adapters/devin.py:397–410: public verify_host/transport_factory/verify_text_cessation/observe_model constructor dependencies.
- adapters/devin.py:732–744 and904–927: pre-session buffering replay and session validation before observer receives update.
- adapters/devin.py:808–819: original model observation plus callback forwarding of full fields.
- adapters/devin.py:874–899: host session verification immediately before original prompt send.
- adapters/devin.py:749–758,763–799: original RPC stop response correlation, deferred completion, verifier and late-frame drain.
- devin_host.py:225–282: exact real owned transports, bound session/prompt RPC, admitted/no-tool checks, reap_owned, complete drain, observed wait/EOF, evidence reference.
- adapters/devin.py:285–307: reap_owned waits/terminates only its CLI and drained requires EOF/no buffered/outgoing data. Cleanup is not a remote-provider-global cessation claim.

Observer exceptions fail protocol processing; the original verifier remains responsible for real completion/drain/wait. The host cessation observation for expected_response=None contains no dynamic output hash. Thus the wrapper must record an explicit side binding between canonical original PAL request/attempt, exact collected output hash/byte count and actual host proof/model/version. That is trusted local consistency evidence, not authority against coordinated forgery or unknown remote inference. No raw output should enter public CO/PAL evidence.

Pinned installed SHA256: devin_host.py `c00e0b050a42794b580a955a6c333cc6880419b2a2d49b721eb8ad8813c13367`; adapters/devin.py `1467cbd0cacec9ab3d3016f83460f07c92a504ef6f21d52848687e206cd3291a`; delegation.py `6fa4f523a17414878b86967df11f8d21d574129de33693d44d411f11d77cc6cc`.

## Remaining proof

No provider attempt or synthetic transport test was run. T can prove the original fixed canary/profile; it cannot silently prove this dynamic observer. N needs the exact external composition boundary, dynamic JSON qualification, one-send/finite-size rules, real completion+EOF+wait, output/evidence/request binding, post-launch timeout/parent death held semantics and source/control/owner integration cases. Qualified mock lock death never settles a native unknown. Opus's report remains REFINE/design evidence; this note neither adopts a new lifecycle nor changes any unknown outcome. Independent fixture/profile preparation can proceed while T waits, without repeating inference or changing CO.
