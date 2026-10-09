# RECOVERY02/1 TSK implementation

Author work begins at b0b02998a8db2548bafb3ca4feb5c70565ad2d4e with immutable
TSK test input ecea63733820c2fc39e39f34f2a9aff3fe9d88f4. The subsequent Root
clarification preserves the exact ComposeAction source list (including selection,
order and duplicates); the original producing-call list is separately nonempty,
duplicate-free and entirely records. This note reports author checks, not
independent acceptance or complete C13/product recovery.

## API and atomic ownership

`TaskStore(..., artifact_lookup=None)` adds one optional trusted readonly
collaborator. Recovery uses the shared `artifact_save_key(original_work, step_id)`
and passes `{key, work_ref, step_id, action}` on its existing transaction. No new
public recovery or Step shape is introduced. Ordinary finish is unchanged.

Managed session/claim/call/reservation/history validation precedes classification.
Replacement, terminal/cancel, paused intent or definitive source denial abandons
the started compose and settles without ART lookup. Eligible recovery checks the
full producing-call dependency union once, then uses the ART owner callback.
Definitive absence abandons; uncertainty keeps the occupied tail with no writes.
An absent collaborator retains the prior artifact-tail hold. Operate remains held.

The callback savepoint detects writes and lost/replaced transactions. Ordinary
callback errors become bounded uncertainty; BaseException cleans up and propagates
through the outer rollback. This is a trusted-host contract, not a sandbox: a
collaborator's already committed writes cannot be retroactively rolled back.

Successful adoption updates the original Step, artifact set, one fixed state
event, adoption links, internal recovery receipt, lease and latest-intent state
inside the same transaction. The event ID is minted before owned settlement
writes. Budget usage, reservations, calls, source registration and ART data remain
unchanged. No output is regenerated and no inference or save is retried.

## Durable integrity

The required `v5_tsk_recovery_adoption` table binds the original Step/call/lease,
artifact, original and adopted WorkRefs, recover key and event. The internal
`v5_tsk_recovery_replay` table stores recover key, nullable adopted Step, event ID
and an exact Result copy. The copy permits detection of a changed generic replay
receipt without assuming that later mutable work state still equals settlement.

Artifact-set reads and recovery replay validate both directions: annotations,
finished compose, original managed claim, model/Step reservations, exact artifact
set entry, canonical replay input, settled Result and fixed event marker. Deleting
either typed annotation alone remains detectable through the other. Event
producer identity comes from their event_id bindings, not public event text. Ordinary finished compose and pre-RECOVERY02 ordinary recoveries remain
valid without retroactive enrollment. This does not detect coordinated forgery
of every trusted local evidence row.

## Verification record

- Fixed new TSK tests are unchanged; SHA256
  `44cc86a7295781d0f162235f07abb1ec45d24e687b48af7fb8ba722037d59c1c`.
- Existing RECOVERY01 fixed22 passed after the initial implementation.
- Existing task/completion/binding suites: 144 PASS, 2.418s; independent historical
  integrity probes: 6 PASS, 0.237s. These are author reruns of existing expectations.
- The initial broad task run included the new tests before ART.lookup_saved was
  delivered. Adoption/absence assertions remained RED because the missing owner
  method was treated as uncertainty. No fake lookup implementation was supplied;
  the original log is retained locally. This is a dependency failure, not evidence
  of successful adoption. Final actual-owner results will be recorded below.

Remaining boundaries: Root owns actual process-crash connection tests, full
regression and integration. Independent review uses a separate context. External
operation tails, remote/provider cessation, live DB migration, Primary execution,
service activation and complete product usefulness remain outside this slice.

## Independent review correction

The initial draft scanned every C14 event for the fixed adoption phrase. The
independent reviewer reproduced ordinary report and release text causing later
reads to fail. This confused content with producer identity; even narrowing the
scan to state events would reserve valid public content. Root clarified that the
two mutually checked TSK tables identify recovery-produced events; their bound
events still require exact state kind, text, refs and WorkRef. No arbitrary text
scan or third registry remains. The original failing evidence is retained locally;
the independent phrase-collision probe is the next-use regression condition.

Actual ART dependency SHA256 is
`1e37f0ed0435f97c54166210b1ac2746ce52edb271482030ce646a3e388c3ef1`.
The original actual-owner fixed20 run yielded 19 PASS / 1 fixture failure: the
later-startup historical replay changed lease_id after a new claim while expecting
the old receipt. A separate probe using the original request returned that receipt
without writes. Only the independent test owner may correct that fixture; the
source preserves changed-input conflict.

## Final author results

Independent test-owner correction `54ed82aac20ac599c51ba7ebfb3f776a809d4ade`
changes only the replay fixture's original lease capture/request. Corrected fixed20
SHA256 is `0c1090afeb8d6773b93c865394ade58935640c8ed0c1915b2f206e67a7c92f1d`;
no test assertions or source expectations were changed by the implementation author.

- `/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_tasks_artifact_recovery_v5.py -v`:
  **20 PASS, 0.850s**, exit 0, actual ART dependency above.
- Independent unchanged probe from `89de4678031f0dc5b4316eaaa6c9a4793e422c8b`:
  **1 method / 2 cases PASS, 0.017s**, exit 0; imported from a scratch file with
  this checkout's test fixtures, without adding it to the author commit.
- Python3.13 `unittest.TestLoader.discover` over `test_task*_v5.py` excluding the
  separately run fixed20, plus `test_recovery*probe_v5.py`:
  **150 PASS, 2.801s**, exit 0. Includes original managed22 and historical probes.
- `git diff --check`: exit 0.

Local logs: `/private/tmp/rec02-actual-art-fixed20-green.log`,
`/private/tmp/rec02-marker-probe-green.log`,
`/private/tmp/rec02-final-affected150.log`. Retained red evidence:
`/private/tmp/rec02-actual-art-first.log` and
`/private/tmp/rec02-marker-collision-red.log`.

Final TSK source SHA256:
`611e05509966df9bb09e85baec9f893625372dc91cc83cf3b692c09461a1ecc1`.
ART is an exact dependency overlay only and is not staged or committed here.
