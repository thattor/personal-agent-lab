# NATIVE-TEXT01/1 — bounded dynamic text capture

SOL freezes this independent prerequisite for PRI02-N. It is a pure standard
library module, not a provider, native qualification, PAL routing authority or
cessation verifier. Actual public DevinTextHost verifier/transport remain the
authority for correlated completion/EOF/owned wait. No CO runtime change.

Module `pal/native_text_v5.py`; independent tests
`tests/test_native_text_v5.py` precede source. Read current source-bound
PRI02-TEXT-SEAM-ANALYSIS.md. The external trusted adapter must call the original
host.observe_model first, then this buffer, after original host.verify(session)
passes. It calls finish only after the same actual host cessation verifier has
completed its full drain. Pure fixtures cannot acquire native proof.

## Interface and bindings

`NativeTextBuffer(*, request_sha256, profile_sha256, attempt_ref, model_id)`.
Digests are exactly64 lower hex; attempt_ref is a closed mapping of nonempty
bounded run_id/job_id/attempt_id strings, copied immutably. model_id is the exact
trusted nonempty bounded model string. Invalid input raises a fixed safe
ValueError without storing source text.

`begin()` opens capture once at the original session verification boundary before
prompt send. Calling twice poisons capture. `observe(fields, *, current_update=False)`
accepts public observer mapping. Before begin ignore all text, retaining none.
After begin capture only sessionUpdate=agent_message_chunk with content.type=text
and strict UTF8 content.text. A nontext/missing content in agent_message_chunk
poisons capture; do not silently treat a partial text subset as the whole answer.
Optional metadata is never captured. Other updates,
including agent thoughts/user text/model metadata, add no output. Original host
still checks model/session/activity. Unknown fields alone grant no authority.
Observed adapter order is preserved; this API has no outer session/RPC envelope
and cannot independently validate it. At most32768 output UTF8 bytes and2048
text chunks, including empty chunks. Overflow/malformed text poisons capture;
subsequent operations cannot recover it or release partial text.

`finish(cessation)` seals once and returns the private result mapping:
text, output_sha256, utf8_bytes, chunks, request_sha256, profile_sha256,
attempt_ref, cessation_sha256, evidence_ref. No public summary is produced here;
the caller keeps text/actual raw ending local and publishes only necessary hashes.
Empty final output, no begin, already sealed, or poisoned state refuses.

The provided cessation mapping must match the original attempt_ref,
guarantee_model=native_handoff_v1, capability=devin.text.only,
native_stop_reason=end_turn, native_mode=plan, effective_model=model_id,
effective_model_verified=true, stdout_eof_validated=true, integer owned_pid>0,
integer owned_exit_code, tool_events=0 and pending_permissions=0 (bool not ints),
and lower64hex session_sha256/prompt_rpc_sha256. Its evidence_ref is
`devin.acp:text-only:end_turn:` plus SHA256 of sorted compact JSON of the entire
cessation mapping excluding evidence_ref, matching installed host's ensure_ascii
default=true. `cessation_sha256` hashes that same original mapping. Retain other
real host fields in this hash; mutation of one side refuses. A negative owned
exit code is permitted because actual verifier may terminate its owned CLI after
correlated completion; this is not provider-global or descendant cessation.

Validation and these hashes establish local consistency only. A lookalike dict
or test double cannot establish actual native completion. External adapter must
also bind installed implementation/qualification/model/version and current C15
request, own durable entering/ending records and real capacity owner. Native
Primary/Expert lifetime integration remains separately frozen, not adopted by
this module or tests. Existing mock recovery and C15 wire stay unchanged.

## Fixed checks

Exact ordered Japanese fragments; pre-begin text/thoughts ignored; strict types,
UTF8/byte/chunk caps; duplicate begin/finish and poisoned partial buffer; immutable
constructor request/profile/attempt binding; full original host receipt hash;
wrong attempt/model/stop/mode/EOF/wait/tool/permission/session/RPC/hash refuses;
negative owned exit after correlated completion allowed; no source text in fixed
exception message. Fixtures are explicitly not process/provider proof.
Return isolated diff/source-test hashes/results/remaining qualification gap.
