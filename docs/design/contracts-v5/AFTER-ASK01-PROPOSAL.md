# After ASK01: bounded next-dependency assessment

Proposal only; Root owns adoption. Read current STATE/DECISIONS/SPEC and current
v5 contracts/interfaces. No implementation, test execution, external call or
activation was performed. ASK01 acceptance remains contingent on Root integration
and independent review; its candidate presence is not milestone acceptance.

## Recommendation

Next implement a bounded **C10.change with target/grant checks and immutable
revision fencing**, before adding a mock Primary/intake router. This connects the
clarified draft loop to a real correction: “use this revised requirement instead,”
without silently overwriting the accepted Brief, resetting budgets, or adopting a
late result from the previous requirement. Cancel already exists; correction is
the missing owner operation. A router without it would merely expose an unsupported
intent or disguise correction as a new Goal/ordinary answer.

SPEC's destination is authorized reversible work that survives interruption and
returns verified results, without making the user manage internal tasks. STATE
C077 records readback acceptance and ASK01's bounded continuation; DECISIONS D038/
D041 permit scoped technical continuation, not provider/UI activation or adoption
of the broader proposed plan.

## Existing connection and concrete gap

MEM append/read/stop, TSK create/get_work/control/ask, optional linked answers,
mock report/lookup/compose, ART save, deterministic VER, complete, C14 and local
readback already provide the building blocks. Semantic checks remain unknown.
`control` supports complete/answer and pause/resume/cancel, but not change.
`IntakeStore.create` already owns host grant/source/target checks; reuse its rules
through a small protected validation seam rather than a second authorization engine.
C03.attach, MEM.correct and Primary proposals are separate missing features; none
should be implicitly claimed by C10.change.

Contract anchors: PAL-contracts-v5 C10 (lines115–119), revision/epoch transitions
(lines157–176), CT-09 (line199), and C13 old-owned-lease release (line137).

## Prerequisites that belong in the same slice

Freeze the exact closed change command and trusted host scope check. Save the new
origin record through MEM first. TSK must check that record's current usability,
new target and original authorized grant; a model DraftBrief alone grants nothing.
Mint fresh fixed Condition IDs; increment revision/epoch, preserve cumulative
Goal/host budgets and retain old artifacts/checks as history. Do not automatically
copy old question/answer bodies or observations into the new revision.

Running change must fence old results immediately while retaining the occupied
lease until known calls end. Current release/current-work helpers assume the lease's
revision is current; that assumption must be reconciled explicitly so old-owned
release can close occupancy without reverting the new revision. Paused change stays
paused; queued/waiting change closes the old question and queues the new revision.
Terminal continuation remains a new Goal, not reopening history.

## Acceptance and boundary

Actual temporary SQLite: ask/answer -> draft -> change -> corrected draft -> current
verification/complete/readback, with old content still historical. Cover running
change during a held mock call, pause/cancel/stop ordering, old-result rejection,
old-lease release, closed questions, exact-key replay, target/grant refusal, no
budget reset, source-stop across old/new dependencies, and post-write rollback/
BaseException. Historical revision readback must remain accurate.

Then a small mock host intake can connect existing owner commands using persisted
input and explicit proposal validation. Natural-language interpretation, real PRI,
UI, recovery, providers and user usefulness remain separate obligations. No new
permission gate is proposed.
