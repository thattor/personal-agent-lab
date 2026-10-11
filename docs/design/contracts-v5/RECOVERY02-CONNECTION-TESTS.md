# RECOVERY02 real saved-tail connection tests

Pinned base `e2ba3e00244f8ba75b9444870bc3c6cd8f95e823`; frozen RECOVERY02/1.
Only tests/test_saved_tail_connection_v5.py and this note are added. Existing
owner fixed tests/source/shared contracts are unchanged.

4 methods (latest-intent method has four finite subcases), 14393 UTF8 bytes.
SHA256 `7fa1d4e2dbac6d6be7f2dcf2fee2087f068d4637163a50fce2f2884bac7f1920`.
Fixture dependency: tests/test_mock_recovery_connection_v5.py imported as a module,
not its TestCase. Reuses actual Owners/create/grant/readback helpers, no inherited
or duplicate test discovery. Direct owners: HOST, MEM, TSK, ART, VER, MockInvoker;
public shared key and sanitizer. No fake source gate, lease, PID or cessation flag.

## Process evidence and fixed expectations

The owned Python subprocess registers/starts the actual managed HOST, creates
fresh file SQLite owners/work, reserves and invokes a synchronous fixed compose
through C15 MockInvoker, then begins its Step. A pipe barrier occurs after actual
ART save returns (COMMIT) and before any TSK.finish_step, or before save. Child
blocks on stdin; parent confirms it is alive, SIGKILLs it and waits for -SIGKILL.
No detached process or provider exists. Admission/action is a trusted mock fixture,
not model/semantic proof. Poll/read wait is bounded at10s, kill/wait5s, cleanup
kills and waits any still-owned child; no sleeps. Live-lock refusal is not repeated.

Fixed cases:
1. Saved-tail recovery finishes original unchanged WorkRef/Step result, preserves
   all ART rows/calls/Goal and host charges, exposes current artifact and exact
   body/hash; same-key replay adds no rows. Actual EventReader/HostReader public
   inspect_session readback includes the artifact.
2. First ordinary finished draft and old VER precede second started saved compose
   in the same child. Recovery keeps original VER receipt/history but invalidates
   use; fresh verification under a new claimed/fenced WorkRef accepts both ARTs.
   Old completion is stale; fresh ordinary completion succeeds. No model claim.
3. Crash before save gives definitive ART absence, abandons original Step without
   resave; one fresh bounded MockRunner callback saves/checks/completes a distinct
   draft, consuming the second host model charge.
4. A distinct guardless SQLite owner applies pause/change/cancel/source-stop after
   child death and before recovery. Latest intent wins, Step abandons, current
   artifact set remains empty and historical original ART receipt/rows persist.
   Definitive ineligibility skips the ART lookup spy entirely. This ordering proves
   serial latest-intent precedence, not a simultaneous thread race.

Private SQLite queries are diagnostic equality/counter/Step evidence, never an
owner callback replacement. Parent RecoveryOwners wires actual ART.lookup_saved
into actual TaskStore; the only spy records lookup calls and delegates directly.
Source author must not edit this fixed fixture to achieve green. Root runs final
actual connections after independent source approvals and qualifies file/process
proof separately from CO metadata tests.

## Baseline result and limits

`/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_saved_tail_connection_v5.py -v`

Observed4 methods /7 errors, all TypeError from unsupported artifact_lookup
constructor keyword. Seven actual child barriers, kill/wait sequences complete;
no child fixture failure is counted as feature RED. Log:
`/private/tmp/pal-saved-tail-connection-red.log`. AST and git diff --check PASS.
No recovery adoption/fresh VER/latest-intent assertion PASS is claimed: parent
construction fails before those assertions. No full suite duplicated. This is
local POSIX file/process acceptance preparation, not network filesystem,
EXE/provider/PRI/semantic/whole-C13/product usefulness evidence.
