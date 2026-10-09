# PRI02-T/1 — one native CLI compatibility proof

Frozen by SOL after the actual C081 Opus5.5 design review and independent Astra
comparison of the installed CO0.4.5 public API. This stage has zero PAL owner
effects and is not a qualified native C15 profile. Native integration remains a
separate contract; managed-inprocess-mock/1 is unchanged.

## Fixed boundary

One synthetic ordinary Primary-shaped request, one CLI prompt, at most one actual
invocation, no automatic retry/fallback/refund. Exact existing devin/swe-2-high,
measured CLI3000.11.3, freshly checked Free tier. No new auth, cost, service,
CO edits or direct CO state/ledger writes. Existing public
`NativeCandidates.selection` and `infer_selected` own pinning, preflight,
shared12-slot admission and process cleanup. An external qualification tool may
call these public APIs; PAL runtime imports no CO module. A multi-call CO task
is never represented as one product charge.

Tool: `tools/qualify_primary_native_v5.py`. Test owner writes
`tests/test_primary_native_qualification_v5.py`; SWE writes only the tool.
SOL owns this scope, integration and the one real invocation. Independent review
uses a separate execution context. No MEM/TSK/PRI DB, owner dispatch, Grant,
old PAL source, live service or product budget is involved. Synthetic call and
reservation IDs are fixture labels, not product admission evidence.

## Public tool interface

`qualify(request, *, candidates, attempt_dir, runtime_binding=None)` returns a
minimized JSON mapping. `candidates` supports the installed public methods above;
test doubles establish only fixture behavior. `runtime_binding=None` always
labels evidence `fixture`, never native proof. CLI accepts required absolute
`--runtime`, `--state-dir`, `--attempt-dir`, `--request` paths; it loads the
installed public NativeCandidates after hashing VERSION and the actual
task/select.py, task/infer.py, task/transcript.py and task/admission.py.
Production output labels `native_cli_compatibility`, not C15 qualification.

Input is a closed C15-shaped mapping with call_id/reservation_id nonempty bounded
strings, role=primary, output_kind=primary_proposal, nonempty messages with closed
role/text fields (system/user only), and a list of valid RECORD Ref JSON source_refs.
Total UTF8 request bytes <=32768. No source body or raw output in minimized
summary. The synthetic prompt instructs strict PRI01-WIRE JSON with an ordinary
reply and proposal kind=none; fixture refs are explicitly synthetic. No semantic
truth or useful-result claim follows from valid JSON.

Use exact fixed policy target implement=devin/swe-2-high, focus=code.
Selection must match the route/model and measured digest. Timeout=60 seconds.
Pinned version/config/Free preflight is rechecked by CO before before_launch.
The optional runtime_binding records installed source digests and exact version;
the result must report version3000.11.3, cost_tier=Free, exact pin/selection digest,
tool_calls=0 and nonempty bounded text. Do not substitute a different model.

## One-attempt journal and ending

Create attempt_dir exclusively, mode0700, before any selection/inference. Existing
directory refuses without entry, even for a different request. Own atomic fsynced
journal binds profile, request/prompt/pin hashes, qualification PID/PPID, start
time and nonce. Raw request/prompt/CO return are retained only inside this local
private attempt directory; stdout/public summary contains hashes and fixed codes.
No paths, account context, credentials or exception messages are exported.

Write/fsync `prepared` before entry. The before_launch hook writes/fsync `entering`
once before CO's prompt-bearing Popen. Duplicate hook refuses; no re-entry. Any
exception before hook -> not_entered; after hook -> unknown. A parse/validation
failure after a normally returned API -> returned_invalid; it proves only a
normal CLI ending, never an applicable Primary proposal. Failure to durably save
the original return/terminal journal -> unknown; keep the entering journal and
never retry. BaseException must not create a false successful result.

Normal result status is `returned_correlated_export`: original-prompt strict
ATIF-v1.7, exact model/version, no tool calls, CLI exit0, bounded stdout/stderr,
owned wait/process-group absence are underpinned by the pinned CO code. It is
NOT complete EOF drain: current _spawn may close pipes after leader grace0.5s.
It is NOT ACP completion or provider-global remote cessation. Child PID is not
returned by this API; parent death in the entry gap stays unknown. CLI internal
provider retries are unknown, so the counting claim is one CLI prompt.

CO capture stdout+stderr stops above8MiB (one read chunk overshoot possible).
ATIF export is checked <=8MiB after exit; it has no live hard disk cap. This
limited T compatibility test honestly retains that restriction and does not
adopt it as the future native C15 bounded-output/cessation guarantee. Final
Primary wire <=32768 UTF8, reply <=8192; Opus's8192 whole-wire shorthand is not
adopted. No monkeypatch/private API or fabricated EOF/process receipt.

## Fixed checks before the one actual invocation

Separate fixed tests precede tool code: valid fixture mapping/pin/timeout,
malformed/oversized request before entry, wrong route/model before entry,
prehook error not_entered, posthook timeout/exception unknown, duplicate hook,
wrong effective model/version/Free/tool count returned_invalid, invalid JSON or
non-none proposal returned_invalid, durable terminal failure unknown,
existing-directory no invoke, journal profile/request/pin binding, and minimized
summary without raw body/context/error canaries. Fixture results are never live
proof. SOL inspects the actual diff, runs fixed tests and receives independent
source review. Fresh route/capacity/cost check precedes the one real invocation.

Return diff, exact source/test hashes, command/exit/results and unresolved limits.
The real proof records actual requested/observed model/version, one entering
marker, strict output verdict and local original hashes. It is neither product
integration, real Expert behavior, nor the authentic human usefulness judgment.
