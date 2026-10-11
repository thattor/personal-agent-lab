# CHANGE01/1 implementation and author verification

Implemented against frozen scope `e0fbdc23602e2a0cf6dc8f2c0590aaae459619a8` (scope SHA256 `fdd1fe51f1d8931bb900f21f4dd4b097c1e17ea5cab838b905553b22cbfaf62c`). Author native Astra; independent fixed tests and Root integration fixtures precede this source. This report is author verification, not independent review or product completion.

## Behavior and API

Only `pal/tasks_v5.py` changed. `control(request)` accepts closed `command={kind:'change',brief:DraftBrief,origin_record_ref:Ref}` with existing parser semantics. No authority/scope keyword, provider or new external API. Same-key canonical replay precedes current authority; fresh human control tolerates epoch only. Origin reuse across the same Goal conflicts. Trusted host binds the saved correction and every derived record to the supplied Brief; the code does not infer or prove natural-language authority.

Grant intersects current host with latest prior grant, preserving the prior ordering and limits without restoring removed permissions. New revision/epoch increment, fresh Conditions and required sources are written atomically with prior work/question supersession, inherited pause/drain, the change event and receipt. Goal and host usage stay unchanged. Every Condition ID and the change event ID is minted with a savepoint/ownership/change-count guard before the first owned write. The local event insert uses the preminted ID; IntakeStore and unrelated event paths remain unchanged. Callback transaction loss is detected; arbitrary hostile committed callback effects cannot be undone.

Historical C02 and C04 receipts remain readable. Only old open questions become superseded; answered links remain historical and do not enter the replacement's claim. Historical/latest state consistency and existing bidirectional question integrity are checked. No-lease claim selects only the latest queued revision. Retained old leases remain diagnostic and cannot authorize new work.

Cross-revision release validates calls, model reservations and linked Step shapes/indices/WorkRefs before cleanup, rejects uncertain/admitted activity, and abandons only old started Steps. Latest cancel/pause wins; old failure cannot fail the replacement. Returned/raised/not_entered calls without Step may settle once fenced. Release returns latest WorkRef and replays that saved result unchanged. Existing same-revision release behavior remains intact.

Source-stop still acts on latest dependencies. Old-only stop does not invalidate an independent replacement; explicitly reused stopped sources fail the new gate. A failed latest work remains terminal and cannot be changed. ART/VER/MEM body ownership, completed-history semantics and current artifact/verification checks are unchanged. No RUN change was needed by the fixed connected tests.

## Fixed inputs and verification

Independent inputs (source commits preserved): TSK `e0b5affd62883e1609720736f03795663f70f3d0`; RUN `3a0a5ff250e1ec799db1cc2e78b6bbc0a4efca0a`; Root connection/demo `8a1434686d58b7c528ca2b6cd9a27367f3035926`.

All three fixed test files remain byte-identical:

| File | SHA256 |
|---|---|
| tests/test_tasks_change_v5.py | a1b8a68a95a8430879e5b73fb83e7c60b5bd9d69d92fa977f6a9a961bccda9fd |
| tests/test_mock_change_v5.py | c26585fed57b80a5bfcd342b3e4469fc688a054dc02a4c3983d69e6cb348dc75 |
| tests/test_change_connection_v5.py | 31c92e805407689abebae60d5ffd10c4d1811a4d1f0abe6892aabd76a13feaa1 |

Commands use `/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests`:

| Suffix | Actual result | Retained local log basename |
|---|---|---|
| `-p test_tasks_change_v5.py -v` | 28 PASS, 0.809s (initial source) | pal-change-tsk-first.log |
| `-p 'test_*change*_v5.py' -v` | 50 PASS, 0.978s (final source) | pal-change-focused-final.log |
| `-p 'test_task*.py' -v` | 121 PASS, 1.549s (final source) | pal-change-task-final.log |
| `-v` restricted attempt | 844 run, 29 socket permission errors + 3 related probe failures; NOT PASS | pal-change-full.log |
| `-v` approved temporary-local-socket execution | 844 PASS, 26.310s, exit 0 (final source) | pal-change-full-authorized.log |

Restricted failure cause was inability to bind local test sockets, not a failed CHANGE assertion. The successful rerun changed only the execution permission for the same full suite. Next full verification must distinguish the socket-capable environment from restricted execution; original failure evidence is retained locally. No tests were weakened and no provider/live DB was used. `git diff --check` passed. Source SHA256: `60e7ccb02279a374e3283297c8bce3fe23c7a0b42cd04ccba08a4ad6777d68d5`.

Root-owned connection fixtures were executed here as author checks; the executable demo was not separately run by this author. Root independent full/demo/integration and separate exact-source review remain outstanding. Raw logs stay local; this note publishes only necessary validation metadata, without raw operational conversation IDs or personal workspace paths. No schema migration, recovery activation, PRI/provider/UI, semantic sufficiency, external operation or whole-PAL acceptance is claimed.

## Independent review correction: stored admission identity and sources

Root and independent Sol rejected source `076d4d20c170638b46f2e06f697e985e4476514b`: old-call cleanup checked mutually equal references but did not separately validate nonempty IDs, canonical admission call ID or saved-source structure/membership. Consistently corrupting both sides therefore released a slot. Independent immutable regression `b3b955412b2d09aed58b1fc6099789c4f02e9df8` adds one method/nine subcases: empty/null/noncanonical call ID, empty reservation ID, empty Step ID, malformed/missing/unregistered/invalid saved sources. Author reproduced all nine failures at the original source (0.074s, no errors); log `pal-change-integrity-author-red.log` remains local.

The bounded correction adds nonempty ID validation, exact `dumps(['C15.call',lease_id,index])` binding and strict Ref parsing plus `required(old) <= supplied(old call) <= registered(old)`, all before cleanup writes. No MEM availability gate is invoked: ended execution must still relinquish its slot when old sources have subsequently stopped. Original tests and other owner modules are unchanged. Next related cleanup review must test consistent corruption of both binding endpoints as well as one-sided mismatch, and preserve successful cessation after old-source stop.

Final focused command with the same Python3.13 flags and `-p 'test_*change*_v5.py' -v`: **51 PASS, 1.111s, exit 0** (`pal-change-integrity-focused-green.log`). Task regression `-p 'test_task*.py' -v`: **122 PASS, 1.645s, exit 0** (`pal-change-integrity-task-green.log`). New immutable test SHA256 `717cf1f445b9590df3797e6a1f1289e251d24591f139b63babf1c7e36597ffa2`; previous three hashes remain unchanged. Final source SHA256 `498b06ca6033c980bfdfe24b54195f247dbc7a46d267c67a1a54b0028f5c3e8f`. The earlier full844 applies to the prior source; Root owns final full845 and repaired-source independent review. This correction does not relabel the prior review as approved.
