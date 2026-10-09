# NATIVE-TEXT01/1 independent Astra review

Verdict: **APPROVE within the frozen pure-buffer/local-consistency scope**.
No source blocker found. This is not native completion or provider qualification.

Candidate: completed SWE output copied byte-for-byte from the assigned CO task,
reviewed against base `04f68456528d1891d3b720264eb66ec21de6ed68`.
Source SHA256 `e000aef8f9491223a1b53d58caf5f4a8b3b683e3d844062cceae45171276941f`.
Fixed test SHA256 `2f5128f01fce6b9b4c47afe1b864f73c579925373ee0768b08093b630046979d`
was unchanged. Candidate source is a read-only dependency overlay, not authored
or committed by this reviewer. This commit adds only this note.

## Evidence

`/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_native_text_v5.py -v`
passed 15 tests in 0.005s, exit0. Log `/private/tmp/native-text-astra-fixed15.log`.

Independent `/private/tmp/native_text_astra_probe.py` ran using the same interpreter
with `-E -s -B`: 19 tests in 0.002s, exit0; log
`/private/tmp/native-text-astra-probe19.log`. Fourteen ending fields each exercised
six substituted values (None/list/dict/bool/int/float), including positive zero
where the contract permits it. Additional probes exercised immutable copied
attempt binding, nontext/malformed poison, full optional Japanese receipt
canonicalization, exact UTF8 cap, late update/final seal and invalid-receipt retry.
No transport or provider was invoked.

The first private probe incorrectly classified integer zero as invalid for
owned_exit_code/tool_events/pending_permissions. All three resulting failures
were fixture errors: the frozen contract explicitly permits them. The private
probe was corrected to assert success for those exact cases; original log retained
at `/private/tmp/native-text-astra-probe19-fixture-red.log`. Product source and
fixed tests were not changed. Next type-matrix review must distinguish exact type
rejection from field-specific valid zero values.

## Source conclusions

Constructor copies the closed attempt mapping into immutable storage; results
receive a fresh mapping (lines47–65,118–126). Text is retained only after begin,
only for agent_message_chunk/text, with strict encoding and cumulative UTF8/chunk
caps. Nontext/malformed/overflow and repeated begin permanently poison and clear
partial output (68–107). Thoughts and unrelated updates contribute no output.

Receipt checks bind original attempt/model/stop/mode and exact boolean/integer
ending fields (129–169); bool is rejected as integer. Canonicalization uses sorted
compact JSON with ensure_ascii default true and nonfinite rejection, retaining
all optional real host fields in the digest (173–182). Negative owned exit is
correctly permitted. It does not invent an exit0 requirement.

A failed finish validation leaves capture open (110–117). Independent probe
confirmed it releases no result; a subsequent valid receipt can seal exactly
once. This is not poison recovery: poisoned buffers remain permanently refused.
The scope makes malformed chunks poisonous but does not require every rejected
receipt attempt to poison. No contract change is requested. The external adapter
must still call finish only after the original actual verifier's full drain;
retrying a local validation is never permission to retry inference or manufacture
an ending. After successful seal, neither late updates nor another finish can
change/release a second result.

## Limits

The public buffer has no session/RPC envelope or version/cleanup observation.
It checks local receipt consistency, not authority. Original host.observe_model,
verify(session), verify_text_cessation, installed profile qualification and durable
C15 binding remain external responsibilities. current_update is not an authority
selector. Matching synthetic receipts, returned text and these tests establish no
actual EOF, owned wait, remote cessation or native Primary acceptance.

Tests cover ordinary trusted observer/receipt mappings and malformed JSON-like
values, not hostile Python Mapping/string subclasses, adversarial recursion or a
sandbox against trusted host code. No broader full suite, real model call,
process-lifetime proof, native integration or usefulness test was run. No old PAL
source, live DB, credentials or CO state was accessed or changed.
