# C096 native UI and PRI02 failure-observation design review (Opus)

Independent milestone design advice from the supplied snapshot only (BASE 6170c26). No tools, tests or commands were run. This is not code certification, provider qualification, cessation evidence or a disposition; Root owns disposition. C094 stays consumed UNKNOWN/active held, and the current no-second-entry/no-rotation boundary is unchanged.

## Verdict: REFINE

- UI02-NATIVE-FIXTURE/1 progression as integrated in C096: aligned as a source/fixture-only slice. I found no blocking defect in the read. Section 2 lists clarifications only.
- PRI02-CLAUDE-FAILURE/1: the boundary is correct. It is limited to one wrapper, applies prospectively only, makes no retrospective C094 update, and claims no cessation. Section 3 lists the minimum corrections needed before Root freezes the 8 methods.

## 1. What the evidence does and does not establish

- C096 verification.json records the following:
  - Root full suite: 1029 tests, exit 0.
  - Independent Astra APPROVE of Sol source ef918b7: 10 fixed tests, 19 old HTTP tests, 3 malformed-owner probes held, 0 malformed dispatches.
  - Local browser path: synthetic typed fixture, 4 typed fixture invokes, 0 actual native model calls.
  - These establish local fixture behavior only. native_qualification NOT_RUN, whole_goal NOT_MET and C094 UNKNOWN_NOT_PROVEN_ACTIVE_HELD are the correct readings. They are not genuine provider qualification, real usefulness or release.
- C094 native-summary.json records entry_count 1, PAL_effects 0, accepted_ending false, accepted_capture false, active_held true, and local_EOF_wait_receipt NOT_RETAINED_NOT_PROVEN.
  - The raw exact claude-opus-5-5 IDs, result success/end_turn and terminal_reason completed are protocol observations. They are not accepted cessation, an accepted ending or semantic adoption.
  - The feed-only reproduction proves a decoder rejection (finish_called false). It does not exclude a separate original cleanup failure.
  - The C095 usage correction is new source. It does not retroactively qualify C094.

## 2. UI02 review (value, responsibilities, contracts)

Value. The slice connects the existing native owners (NativePrimaryHost, NativeExpertRunner, TaskStore/Memory/Artifact/Verification) to the UI01/2 loopback surface without a second owner engine. It also adds an honest closed status: native_fixture, native_available false, qualification NOT_RUN.

Confirmed responsibilities in pal/native_http_v5.py:

- Constructor gate. It rejects callable providers, a non-NativeProfile profile, a fixture_only value other than exactly True, a missing preflight/invoke, nonempty capabilities and limits outside 0..20 with max_operations 0.
  - The constructor calls no preflight or invoke.
  - A held recovery or a non-ready startup refuses construction and retains the DB.
- Profile and marker snapshot. _unchanged() is rechecked in owners, reservation, slice, before Expert entry and in status. A change latches held while core owners stay readable, and turn read fails closed with a pathless 503.
- Complete owner-envelope progression.
  - _primary_value validates the closed Primary envelope before its status is inspected.
  - Only committed reaches at most one execute_next.
  - failed, interrupted and pending do not advance. held and malformed responses latch held.
  - Primary UNAVAILABLE latches held. DENIED and INVALID_INPUT are not converted.
  - The Expert result is shape-checked after its single slice. A malformed shape or an exception latches held through _work. Exact {status: empty} does not hold.
- Held, read, control and source-stop. Held discards queued items without progression and keeps durable turns saved. Reads, pause/cancel controls and source-stop use separate connections. close() closes the guard and keeps the directory/DB, including UNKNOWN.

Clarifications (non-blocking, document rather than change):

- U1. While held, resume and structured-answer controls are refused with 503 at create_server's _reserve_slot, before tasks.control. The answer is therefore not durably recorded, not merely left unscheduled. This is consistent with no progression while held. The contract text that controls remain available should say this explicitly.
- U2. fixture_only is a caller declaration only. NativeClaudeText has no __slots__, so a trusted caller could attach the marker to a real wrapper. evidence_kind fixture is not required. The contract already says the marker is not attestation. It must remain a blocker against reusing LocalNativeApp as a real launcher (see B4).
- U3. A startup refusal retains the fresh directory, but the caller holds no object or path to it. This is acceptable for fixtures. Note it as a retention limit.
- U4. _expert_value accepts released/completed only with control_status none. A concurrent control that yields a different control_status would latch held. This is conservative and fail-closed. Root should confirm that the fixed concurrent-control method exercises this shape, so the held latch is intended rather than incidental.
- U5. Review binding. The APPROVE names ef918b7, while the verified integration is 20d512a. Root should record that the four UI source hashes in verification.json equal the reviewed ef918b7 bytes.

## 3. PRI02-CLAUDE-FAILURE/1: minimum corrections

The current invoke() suppresses any _cleanup exception. For an activated Exception it raises a generic RuntimeError from None. That is why C094 has no durable primary or cleanup cause. One bounded private failure.json in the newly owned call directory is the right minimum. Corrections:

- P1. Public outcome wording. Replace preserve original exception classes at the public boundary with preserve the existing public outcomes exactly:
  - An activated Exception raises RuntimeError('Claude native text unavailable') from None.
  - A pre-activation failure raises NativeNeverEntered with the unchanged evidence_ref.
  - A non-Exception BaseException is re-raised as the same object.
  - Raising the original class would change runner handling and is out of scope.
- P2. Ordering and suppression. Select the outcome before the diagnostic. Then:
  1. Run cleanup exactly once, only when a child exists.
  2. Attempt the diagnostic once.
  3. Suppress any exception from the diagnostic.
  4. Raise the pre-selected outcome.
  - The diagnostic never touches active.json, the lock or the lane, and never runs on success or for a non-activated refusal.
- P3. Phase tracking. Use one local phase variable assigned immediately before each step. The handles finally block (flush/fsync/close of stdout.bin/stderr.bin) can replace a pump exception. Either add a closed phase close_streams, or freeze capture_streams as covering both open and close. Record the masking as a stated limit: only the exception reaching the outer handler is primary_error, and its __context__ is not serialized.
- P4. Kind. Use exact type() membership, not isinstance, in a frozen tuple listed in the contract. Suggested tuple: ValueError, TypeError, KeyError, UnicodeDecodeError, UnicodeEncodeError, RuntimeError, OSError, FileExistsError, FileNotFoundError, PermissionError, BlockingIOError, BrokenPipeError, ChildProcessError, ProcessLookupError, TimeoutError, MemoryError, KeyboardInterrupt, SystemExit, subprocess.TimeoutExpired. Everything else is OtherError. errno is set only when exc is an OSError and type(exc.errno) is int, otherwise null.
- P5. Sites.
  - Walk only exc.__traceback__ via tb_next.
  - Keep frames whose filename equals str(self._root / relative) for a relative path in the fixed _SOURCE_FILES. Omit all others.
  - Keep the last 8 in traceback order, with positive tb_lineno.
  - Because _fail() raises from None, sites will usually end at the _fail caller. This is expected and is what distinguishes a decoder rejection from a timeout or cleanup refusal without message parsing.
- P6. cleanup_status.
  - not_attempted when child is None.
  - succeeded when _cleanup returned.
  - failed when it raised.
  - In phases after owned_wait (save_ending, save_capture, release), the child is already reaped and _cleanup only closes streams. succeeded there must be documented as stream-close only, never process or remote cessation.
- P7. Observations. observed_stdout_eof, observed_stderr_eof and observed_exit_code are copied only from the tuple _pump actually returned. Otherwise they are null. observed_exit_code is the WNOWAIT observation, not the reaped wait value, and an owned_wait mismatch is not recorded as a second code. ending_write_completed and capture_write_completed become true only after the corresponding _write returns.
- P8. Write rule.
  - Write call_dir/failure.json through the existing _write: O_EXCL|O_NOFOLLOW, 0600, file and directory fsync.
  - activated implies call_dir already exists from this invocation.
  - If canonical bytes exceed 4096, write nothing rather than truncate.
  - Never overwrite. An existing failure.json is retained and the outcome is unchanged.
  - The file stays private. Any later public evidence may reference only its hash.
- P9. Methods. Within the frozen 8, add explicit assertions for the following:
  - (a) The raised object is identical to the original for KeyboardInterrupt/SystemExit.
  - (b) A pump error followed by a stream-close error yields null EOF/exit and the agreed phase.
  - (c) Canaries in request text, stdout, environment and exception message are absent.
  - (d) A post-owned_wait failure reports both write flags truthfully while active.json stays held.
- P10. Pin. tools/native_claude_text_v5.py is in _SOURCE_FILES, so the change yields a new qualification_sha256 and profile. The change grants no entry authority, and the old C094 pin is not re-bindable.

Not needed and should not be added: remote cessation, charge proof, a recovery/release API, a second owner engine, a generic schema framework, _pump changes, or new auth/service/cost.

## 4. Old UNKNOWN versus a future decision

These are two distinct things:

- Preserved C094 UNKNOWN. All files and active.json are retained. The C094 lane mechanically refuses any new invoke: active.json present means pre-activation refusal. PRI02 source cannot recover its original EOF/wait/capture/ending and must never be pointed at it.
- Proposed explicit human decision. This would allow a distinct finite future MAX1 under a new attempt root, while C094 stays UNKNOWN, unreleased and unadopted. It requires a separate operator/source/budget/account freeze. It cannot be inferred from PRI02 acceptance, this review, the Astra APPROVE or the 1029 green suite. Until that separate decision exists, continued hold applies.

Design note only: if such a decision is ever made, landing PRI02 first means an activated failure would leave a bounded cause record that C094 lacks.

## 5. Source-versus-real-entry blockers

- B1. C094 is consumed UNKNOWN/active held. A new attempt root or MAX1 requires a separate explicit human decision. D065 no-second-entry/no-rotation stands.
- B2. No accepted real Claude ending exists. Observed raw IDs and result frames are not qualification or cessation.
- B3. The PRI02 source, its pin and the 17-file closure must be rebuilt and independently reviewed, and Root full-suite verification must follow, before even local source acceptance.
- B4. The HTTP/UI files are outside the 17-file closure. No qualified whole-flow launcher exists. The fixture_only marker must not become a real-entry gate (U2).
- B5. Real usefulness is unmeasured by design, and no prose or intelligence grading applies. The browser proof used 0 actual model calls.
- B6. Any future entry requires a concrete operator, account, budget and overage freeze that this proposal does not and should not invent.

CO is optional and was not used for any state or runtime change. No original case operation, raw semantic adoption, provider call, replay, cancel, release or rotation is implied.
