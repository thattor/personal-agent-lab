# PRI02-MODEL-OVERFLOW/1 — first bounded overflow reason, source only

Root frozen local source scope, 2026-10-10, production base300d40d123e675b354f811b9f2240025730e5daf.
C091's actual INCOMPLETE/0 observations/0 hints loses the overflow boundary. Local
source/12 synthetic cases distinguish possible paths; they do not reconstruct
original frames or prove the unique RuntimeError. This scope repairs prospective
observability only. Original PRI02-MODEL-DIAGNOSTIC/1 API, nine-key snapshot,
limits/projections/refusal/ignore behavior stay unchanged.

## Outcome and exclusion

Add one private count/reason-only first-overflow sidecar at the existing public
model callbacks, with no raw option/value/session/error frames. Never increase
bounds, grant model authority, alter strict ending/NativeReturned/replay or edit
CO/runtime/state. No provider/CLI/ACP execution, RPC/set_config, extra pumping,
unknown retry/release, N4/real Expert/UI, new auth/service/cost or old PAL code.
New capture/wrapper source hashes invalidate the prior envelope as usual. No
existing N1/N2/N3 or CO file is modified, reconstructed or reclassified.

## Closed pure API

Append NativeModelDiagnostic.overflow_snapshot() in the existing capture file;
the existing constructor/observe/snapshot results and behavior remain. It returns
a fresh plain dictionary with exactly nine keys:
version='PRI02-MODEL-OVERFLOW/1', authority='unqualified', request_sha256,
profile_sha256, attempt_ref, requested_model_id, status, first_overflow, limits.
Bindings and five existing limits equal the original diagnostic snapshot. Add
limits.max_marker_record_bytes=4096. status is not_observed|overflow; first_overflow
is null before actual collector-bound overflow and a closed marker afterward.
This is only relevant callback collection, not frame coverage or RuntimeError
cause. If the canonical UTF8 sidecar exceeds4096, overflow_snapshot raises
ValueError; best-effort wrapper omission cannot change original behavior.

Marker keys, all mandatory:
- retained_index: number of previously retained observations,0..32; never wire order.
- hook:observe|verify_session; shape:field_snapshot|config_option_update|preprompt_snapshot.
- original_hook:returned|raised, current_update:exact bool; same conservative metadata
  normalization as the original row, never a new native success assertion.
- reason:observation_count|option_count|value_count|token_length|record_bytes.
- site:observations|configOptions|select_options|group_options|flattened_options|
  option_id|category|current_value|available_value|group_id|snapshot.
- unit:count|codepoints|utf8_bytes.
- limit:the exact original exceeded bound; observed_at_least:limit+1, never raw length.
- valid_hint_retained:exact bool, any valid non-null hint in the previous retained
  prefix; not requested equality or effective-model proof.

Reason/site/unit/limit combinations are closed: observation_count/observations/
count/32; option_count/configOptions/count/16; value_count/select_options or
 group_options or flattened_options/count/32; token_length/option_id or category
or current_value or available_value or group_id/codepoints or utf8_bytes/256;
record_bytes/snapshot/utf8_bytes/32768. Preserve the original first refusal order.
A cheap character-length refusal marks codepoints; encoded-byte refusal marks
utf8_bytes. Malformed UTF8/wrong types, ignored text, constructor binding refusal,
sessionId overflow converted to malformed, and generic diagnostic exception do
not become a first-overflow marker. Once incomplete, later callbacks still ignore;
exactly the first marker is retained. Input/snapshot mutation cannot alter it.
No unbounded raw serialization/deepcopy or new I/O in the pure class.

## Wrapper and ownership

Only pal/native_text_v5.py and tools/native_devin_text_v5.py production change.
Best-effort write local0600 model-overflow.json once alongside the existing model
record after the original supported stop, and after ending.json on strict success.
Entered generic/interrupt failure retains it under the same existing rules;
pre-entry/NeverEntered emits neither diagnostic. Catch diagnostic BaseException
locally; marker construction/snapshot/write errors preserve original result/error,
stop count/order and pumping. No changes to ordinary diagnostic or semantic parsing.
The sidecar cannot enter TSK/ART/READ/replay or NativeReturned evidence.

Root owns scope/canon/integration. Separate Native Sol fixed tests first in
 tests/test_native_model_overflow_v5.py and tests/test_native_devin_model_overflow_v5.py;
record original RED then freeze exact bytes. Isolated Native Astra implements both
production files against those fixed tests under the existing D056/C073 fallback.
Separate Sol review context differs from Astra author; fixed-test ownership is
reported. No blind duplicate of the preserved CO SWE UNKNOWN. All old20/native151
and current969 cases remain. Return commit/diff/source and fixture hashes,
commands/counts/exits and residual issues; authors' self-check is not independent review.

## Required verification and limits

Meaningful pure fixtures cover each actual overflow path/site/unit, grouped
cumulative overflow, prefix retention/hints, observation33, first marker stability,
ignored/malformed/session overflow controls, defensive copy/UTF8, sidecar4096
refusal and unchanged original nine-key snapshots. Wrapper fixtures cover strict
success and original-null/false refusal, raised hook/interrupt, stop-before-write
exactly once, write/snapshot failure noninterference, pre-entry/NeverEntered omission,
and no extra calls/pumping. Fixtures use fake public bridge/runtime only.
Independent approval plus Root full suite is required before integration. This
source verification does not authorize another native case, real integration or
whole-goal completion. Any later provider entry needs a distinct evidence-based
reassessment and exact reviewed operator/source freeze; no such entry is proposed here.
