# PRI02-MODEL-DIAGNOSTIC/1 — bounded public-hook observations

Root frozen source scope, 2026-10-10. Base fff19cc022c6845fdfde4236cbda349d1513d82d.
Adopts Astra's bounded diagnostic proposal after direct installed-source and
[official ACP](https://agentclientprotocol.com/protocol/v1/session-config-options)
comparison. This is fixture-only implementation authority, not a new real call.
D052/D053 and unchanged PRI02-DIAGNOSTIC/1/NativeCall remain governing boundaries.

## Outcome and exclusion

Preserve bounded modern model configuration delivered by existing public callbacks
for future diagnosis. Never qualify a model, change original cessation/evidence,
relax NativeTextBuffer.finish/NativeReturned.validate, or recover old unsaved N2
frames. No RPC/set_config/events/status/execute added, CO/runtime/state edit,
unknown retry/release, N3/T2/real Expert, old engine, service/auth/cost change.
Callbacks are deliveries, not wire frame count/order or prompt-RPC proof. The
installed observer also receives set_config results: non-update values are called
field_snapshot, never asserted to be an original session/new result. Current
boolean capability negotiation is not proved by this collector.

## Pure API and closed record

Append NativeModelDiagnostic in pal/native_text_v5.py. Constructor kwargs:
request_sha256, profile_sha256, attempt_ref, model_id. Hashes are lowercase hex64;
attempt_ref is exact dict of run_id/job_id/attempt_id, each nonempty UTF8<=512
bytes; model_id nonempty UTF8<=512. Invalid bindings raise ValueError before use.
The existing NativeTextBuffer API/behavior remains unchanged.

observe(fields, *, hook, current_update=False, original_hook='returned') records
only hook observe or verify_session. original_hook is returned|raised and means
the existing original callback returned or raised; it is not successful model
verification. Arguments are never changed. observe returns None. For observe,
ignore dict payloads with none of configOptions/sessionId and no sessionUpdate
config_option_update. Ignore text/thought chunks; do not fill the model budget
with text. Nondict target input records malformed. verify_session always records.
Valid current_update is exactly bool. Invalid hook metadata records malformed
with conservative defaults observe/field_snapshot/raised/false, never raw values.

snapshot() returns a fresh plain dict with exactly these nine keys:
version='PRI02-MODEL-DIAGNOSTIC/1', authority='unqualified', request_sha256,
profile_sha256, attempt_ref, requested_model_id, status, observations,
limits={max_observations:32,max_options:16,max_values:32,max_string_bytes:256,
max_record_bytes:32768}. status=complete|incomplete describes delivered relevant
callbacks retained within limits, never protocol coverage or model qualification.

Each observation has exactly: delivery_index (0-based retained delivery order),
hook, shape=field_snapshot|config_option_update|preprompt_snapshot, original_hook,
session_sha256 (explicit valid sessionId UTF8<=512 hash or null), current_update,
projection_status=valid|malformed, options, effective_model_hint.
verify_session shape is preprompt_snapshot; observe with exact config_option_update
is config_option_update; other relevant observe is field_snapshot. No inherited
session ID or prompt ID is inserted. The outer update session binding is checked
by CO before callback but not included in its public argument. Duplicate deliveries
and changed hints remain separate; later good observations never erase earlier ones.

options projects only configOptions, preserving order. Absent options is valid []
for non-config updates; a config_option_update without configOptions is malformed.
Each projected option has exactly id/category/type/current_value/available_values.
id is a nonempty UTF8<=256 string; missing category maps null, otherwise UTF8<=256
string. type is select|boolean. select currentValue is nonempty UTF8<=256 string,
options a nonempty list of flat value dicts OR group dicts (not mixed). Flat entries
have nonempty value UTF8<=256. Groups have nonempty group UTF8<=256 and nonempty
options lists of value dicts, flattened in source order. Ignore all names,
descriptions/_meta/unknown keys without copying or serializing them. boolean
currentValue is exactly bool and available_values=[], with no options field.
Duplicate option IDs/values remain diagnostic data, not unique identity proof.
Invalid targeted types/UTF8/mixed groups produce one malformed observation with
options=[] and hint=null; do not retain raw values or exception strings.

A hint is null unless exactly one projected option has id=='model', type select,
and its current_value occurs in available_values. Then hint is exactly
{option_id:'model',current_value:<original string>}. Category/label/configId/fuzzy
matching/requested equality are not identity evidence. A match stays unqualified.

Limits:32 retained observations,16 options per entry,32 flattened values per
option,256 UTF8 bytes per projected token,32768 canonical JSON UTF8 bytes for the
whole snapshot, using sorted keys/compact separators/ensure_ascii=False/allow_nan=False.
Count/byte overflow freezes the previous valid prefix and status=incomplete; no
further collection occurs. Reserve room for the longer incomplete status when
checking total size. Validate cheap type/count/character bounds before encoding
or iterating; never deepcopy/stringify a huge raw payload. Malformed small values
consume a bounded observation and permit subsequent callbacks. Defensive snapshot
copy; input mutation cannot rewrite saved projections. Pure code does no I/O.

## Wrapper integration and proof boundary

Only tools/native_devin_text_v5.py changes besides the pure file and two independent
new test files. Best-effort create collector after original buffer creation.
Keep host.verify, request identity check, buffer.begin and host.observe_model /
buffer.observe order unchanged. Record relevant original hook returned/raised in
an independent best-effort finally, catching BaseException only for diagnostic work.
Original callback/result/Exception/BaseException propagation is unchanged.

Write local0600 model-observations.json once, best-effort after the existing own
supported stop attempt. On strict success write after existing ending.json; on
generic entered failure write after own stop and existing unqualified-output.json,
before existing non-pumping diagnostic. Diagnostic construction/observe/snapshot/
write failure cannot change original success or original failure. No file on
pre-entry failure or exact NativeNeverEntered. The existing stop count/order and
execute/status/events behavior remain. This record cannot enter TSK/ART/READ/replay.

The pure class remains in the existing capture file, so current exact capture and
wrapper hashes automatically invalidate the old qualification envelope without
adding pin keys or a new unverifiable imported module. No new profile is adopted.

## Assignments and done

Independent Sol fixed tests first: tests/test_native_model_diagnostic_v5.py and
tests/test_native_devin_model_diagnostic_v5.py; record original RED, then freeze.
CO SWE-2 High pure class only; Native Astra wrapper only after fixed tests exist.
Root integrates exact bytes, independent source reviewers differ from authors.
Returned deliverables: commit/diff/hash, explicit commands/counts/exits, remaining
issues. Tests cover projections, grouping/booleans/duplicates/order/absence/
changed and ambiguous hints, boundary overflow/UTF8/mutation, original hook
Exception/BaseException, stop-before-write exactly once and no extra pumping,
diagnostic failure noninterference, pre-entry/NeverEntered no file, null/false
original model still refused despite matching hint. Full current suite must pass.
Source verified is not real qualification, usefulness or whole goal completion.
