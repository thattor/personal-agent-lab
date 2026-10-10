# PRI01 independent binding/fault tests

Separate native Sol context, not Root source author. Base19e5f6e1f5ff4cd12de1ab6fc1035aa63866fac0. Initial readonly source overlay SHA256 `4e6c01d03c720e68e34d4cb0f75137970be1e2468b8badc5565e643980755eab` remains untracked and excluded from commit. Own writes are this note and `tests/test_primary_binding_review_v5.py`; frozen owner contracts/tests untouched.

Actual fixture is module-imported `test_primary_host_v5.PrimaryHostTests` instantiated locally, not an imported/discovered or inherited TestCase. Actual managed HOST, MEM/TSK/ART/VER, fresh file SQLite; labeled mock callback only. Connection subclass injects a known SQLite COMMIT response loss after the real admission commit. Deliberate SQL tampering uses current PRI-private columns; these are white-box persistence probes, not public schema contracts or a proof against coordinated database forgery.

Initial findings/fixed expectations:

- Changing terminal turn nonce or call ID/input_hash/reservation/status alone must fail unavailable with no reply/callback/write. Initial source accepts five such cases; session runner corruption already refuses. Bindings need durable independent consistency, rather than accepting individually shaped values.
- Dropping an exposed uncited record from saved metadata must not authorize the saved reply after that record stops. Initial source leaks the reply through its narrowed exposure metadata.
- Changing applying intent reply alone must hold at qualified startup without owner reapplication. Initial source adopts the changed reply against the original successful owner receipt.
- Stored outcome raw error canary must not be publicly returned; initial source publishes it. Canary is synthetic, not an actual secret.
- Known admission commit with lost response never enters callback. Its durable terminal failed call must be not_entered, not remain admitted. Initial source fails the ledger check (zero callbacks/one nonrefunded charge already hold).
- Invalid UTF8 callback string is a known returned call with failed bounded turn; no second inference. Initial source leaves the call admitted and run returns unavailable before bounded failed settlement.

Positive independent cases: C11 read writes and ROLLBACK+BEGIN cause reply omission without terminal/effect replay or DB change; read write failure in caller active TX rolls back the read's write while preserving the caller's prior row/TX. These exercise trusted owner callback guards; they do not claim arbitrary host-code sandboxing or restoration after a trusted COMMIT of caller work.

Command `/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_primary_binding_review_v5.py -v`:8 methods,10 failures (including five terminal corruption subcases),no errors,0.132s,exit1. Raw initial RED `/private/tmp/pri01-host-binding-initial-red.log`. Test SHA256 `4843db4708181c54cf61d11706a7642ac7a94d31dca34ae737b060b479fb54dd`. AST/diff check PASS. Source gaps were reported to Root before this commit. Expectations derive from frozen no-reply/no-entry/no-effect-repeat and corruption semantics; no source implementation is copied into assertions.

Final source execution is pending; no final Host approval or full-suite claim. Not covered here: full Primary usability, real provider, process death, all owner grammar/effect selection permutations, coordinated multicolumn/table forgery or external side effects. Root owns exact source repair, whole connection/full regression; independent final review should rerun these unchanged probes against the final source hash.

## Read-TX loss clarification and independent fixed-test execution

Test-owner independently reconciled frozen bad/corrupt connection→unavailable with ordinary C11 source refusal→committed history/no reply. Root authorized narrowing only the rollback_begin case: losing the read savepoint through ROLLBACK+BEGIN invalidates the trusted snapshot, so it must return failure(unavailable), with no value/reply. A read write whose savepoint can be rolled back still returns original committed history without reply; existing caller writes/TX must survive. Database snapshot/no new charge/no callback/idle assertions remain, with explicit charge equality added; no union of alternative acceptable codes and no effect-replay relaxation.

Original commit207a661 and RED remain preserved. Corrected fixed8 SHA256 `2e82a1814f6a932f4215766bc42c5d982694395dd76feed330a906c727068c27` independently executed against Root's readonly evolving draft source SHA256 `e44a463b3655926d21b84430bba3271b046fcb96961dc53d9a80f02400616310`: same unittest command,8 PASS0.147s,exit0,log `/private/tmp/pri01-host-binding-clarified-green.log`; AST/diff check PASS. This is test-owner criterion validation, not final exact source approval; separate Astra owns that review and Root whole/process proof. No production source is committed/edited here.
