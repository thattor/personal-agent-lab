# PRI01 independent process / whole mock connection preparation

Base da8bf4f25432ff0dbbfedbb54a4cad470fa9ea71; frozen PRI01/RECOVERY01/02.
Only tests/test_primary_process_v5.py and this note added. No source/owner-fixed
suite/shared contracts edits; no unapproved TSK candidate copied or accepted.
5 methods, 14765 UTF8 bytes.
SHA256 `9916a1309de31091d2472cc1fbfe09b145bd2c5c796e45d2d45da0e250b1174d`.

Independent minimal actual-owner setup, no TestCase inheritance/import duplication:
MockHostSession, MemoryStore with actual sanitize, TaskStore/ArtifactStore/
VerificationStore, MockRunner/EventReader/HostReader/read consumer, contracts and
future PrimaryHost. All owners share a fresh temporary file SQLite and actual
source gates. Final integrated PRI01-TSK/MEM/WIRE APIs are dependencies, not copied
stubs. Root will run after exact source approvals. Primary model responses and
Expert actions are scripted synchronous mock JSON; no quality/semantic proof.

## Barriers

1. Actual child Primary callback admitted, then blocked on stdin. Parent confirms
   child alive, SIGKILL and wait -SIGKILL; new real guard/register/recover interrupts
   original turn with consumed model unit intact, no callback/refund/reentry.
2. Real C03 create COMMIT inside a public method wrapper, before PRI terminal write.
   Kill/wait; qualified startup uses original public receipt, one Goal/terminal
   result, no reapplication/reinference and unchanged charge.
3. Real MEM append COMMIT before PRI admission; kill/wait. Sanitized same-client
   resend completes admission using original single record, no early model debit,
   then one fresh call. No private schema or fake-success bridge.
4. Actual two threads use separate SQLite connections and the same registered live
   guard. An Event barrier holds winning callback while the other invocation sees
   pending. Structured cancel and source-stop complete before callback release;
   guard.close refuses active permit. Worker ends once, source-invalid reply fails,
   shared model charge1. No sleep-only proof or SQLite cross-thread connection use.
5. Whole scripted request→Primary new_work→Expert ask→Primary answer/change→Expert
   compose→new structural VER/completion→public saved readback→source-stop invalidated
   VER/history notice. Same Goal, revision2, three Primary plus two Expert debits,
   no semantic/provider/owner-usefulness assertion.

Child process is exclusively test-owned host, not launched/forked by callback.
Pipe readiness timeout10s, kill/wait5s; cleanup kills/waits every owned process.
Thread entry/release/join each bounded5s with release in finally. No network,
new service/auth/cost, old/live DB or detached process. These fixtures target local
POSIX, not remote callback or network filesystem cessation. Live-lock refusal and
fixed39 are not duplicated. Cooperative profile assumptions remain explicit.

## Initial result

`/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_primary_process_v5.py -v`
Observed5 errors, all ModuleNotFoundError for pal.primary_host_v5 in setUp.
Log /private/tmp/pal-primary-process-fixed-red.log. AST/git diff --check PASS.
No process barrier, thread competition, whole flow or new-source behavior has run:
all are NOT RUN, not falsely PASS from syntax. No fake implementation/skip.
Root source author and independent reviewer own later implementation proof;
Root runs/fixes genuine fixture issues distinctly from feature failures, records
actual exact-version results and full regression. Product usefulness and later
finite provider profile remain separate.


## Authorized ready-connection fixture correction

Root first execution:4 PASS/1 FAIL, callback never entered. The second connection
constructor unconditionally called TSK.register_host on the shared already-ready
guard; RECOVERY01 explicitly permits registration only in owned/startup. This
fixture error also left a constructor-open connection unreachable, producing a
ResourceWarning. The fixture now registers only owned/startup guards; the existing
ready guard/session is reused and ordinary owner methods still validate it. No
fake registration, guard/profile change, weaker source/entry/control assertion or
source edit. Original commit cbfb027 and failure log remain retained. Branch was
rebased on Root49115b2 (original test already integrated), then this bounded change.

Exact Root source was copied only as an untracked read dependency:
SHA256 e44a463b3655926d21b84430bba3271b046fcb96961dc53d9a80f02400616310.
Independent actual execution:
`/opt/homebrew/bin/python3.13 -E -s -B -W error::ResourceWarning -m unittest discover -s tests -p test_primary_process_v5.py -v`
5 PASS0.358s: three real SIGKILL/wait barriers, separate-connection thread entry
and immediate controls/source-stop, whole scripted mock flow. No ResourceWarning
or other warning appeared. Log /private/tmp/pal-primary-process-fixture-order.log.
This is fixture selfcheck, not independent Primary source approval; Root reruns
and owns adoption/full qualification. Next connection fixture must distinguish
startup registration from reuse of an existing ready managed session.
