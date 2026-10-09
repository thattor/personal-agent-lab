# RECOVERY01 provisional independent TSK review

**REQUEST_CHANGES; no final approval.** Reviewed prepared Astra source snapshot SHA256 `7a2507173bcdeb5f8a2dcd5562c6a87b058bf0394b7e70b36fbf84a85f88dcbc`, verified before reading and copied unchanged into isolated review worktree based on `73b209a486ea62f3e9f76318e8ad8bf14255b1f5`. Source author is a separate Astra context; this Sol reviewer authored fixed owner tests, not implementation. Frozen RECOVERY01-SCOPE and current RUN17a7/fixed22 remain binding. Snapshot source is provisional/uncommitted and is **not** part of this note/probe commit.

## Concrete blocker

P1 — `pal/tasks_v5.py:1408–1413`: `_old_calls` deeply validates the recovering lease's calls/Steps, but older leases' Step history only receives call-backlink and dangling-started checks. Actual two-lease temporary SQLite fixture creates a returned report, finishes it and releases lease1; lease2 claims and saves a returned call without Step. Change lease1's wire status to `unknown`, its wire index to bool False, or its linked old call status to `unknown`. Recovery's actual validation entry `_old_calls(row,lease2,claim=current_claim_WorkRef)` accepts all three corrupt variants. Frozen recovery requires known Action/status, strict SQL/wire indices and all call/Step link validation before settlement; corrupt immutable history must remain unavailable/no writes. `_questions` and artifact-set checks do not catch these report corruptions. The actual managed-recover regression is retained but NOT_RUN pending real HOST. Root/Astra received this finding; author repair is separate.

The private-method probe establishes the executed validator gap; it is not a claim of executed managed recovery or lifetime proof. Intact historical Step passes the same probe. No old callback or result adoption was performed.

## Probes and executed evidence

New `tests/test_recovery_private_integrity_probe_v5.py` contains five methods. Two are runnable legacy actual-owner validator probes: intact history and three corrupt-history variants. Three require real MockHostSession and cover seven enrollment/old-session/lease-claim corruptions, preserved exact claim epoch under later pause/cancel epochs, and corrupt older history refused by public recover. No fake guard, new source mutation, live database, provider or subprocess callback.

Commands used `/opt/homebrew/bin/python3.13 -E -s -B`:

- `-m unittest discover -s tests -p test_tasks_change_v5.py -q`: 28 PASS, 0.943s.
- `-m unittest discover -s tests -p test_tasks_release_integrity_v5.py -q`: one method/18 existing subcases PASS, 0.082s.
- `-m unittest discover -s tests -p test_recovery_private_integrity_probe_v5.py -v`: five methods, exit1, **3 failures/9 errors**, 0.046s. Failures are the three concrete older-history corruptions. Nine errors are missing real `pal.mock_host_v5` (seven corruption subcases and two further managed methods); managed bodies are NOT_RUN. One intact-history validator case passes. Raw bounded log remains `/private/tmp/pal-recovery-tsk-private-probes.log`.

## Static assessment and remaining gates

Inspected enrollment/session/lease tables, UUID/profile checks, own-session/runner matching, claim-epoch binding, transaction/replay routing, startup-only recovery and historical replay, host permit coverage, consume/end/release authority, latest terminal/pause/change precedence, safe Step classification versus compose/operate holds, reservation preservation and premint rollback. Startup snapshots capture one active orphan and are reconstructible after registration reply loss; new nonce does not retroactively qualify an unmanaged lease. Recover receipts are keyed separately and do not restore execution authority. Physical cleanup does not MEM-regate stopped source bodies; fresh ART/VER/Step use is separately gated. These are source observations, not actual managed acceptance.

Real HOST final source, managed fixed22/Root connection and final TSK exact source are still required. Final review must execute UUID/profile/session/claim corruption refusal and control ordering with the genuine Host class, including subsequent repair bytes. No full suite, process-death proof, ART recovery adoption, provider/EXE/Primary activation or whole-C13/product acceptance is claimed. Root owns integration/canonical evidence. Historical compose/operate hold remains an explicit whole-draft recovery limitation.
