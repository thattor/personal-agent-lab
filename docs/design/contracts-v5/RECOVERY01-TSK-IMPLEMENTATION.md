# RECOVERY01/1 TSK implementation

Author scope: `pal/tasks_v5.py` and this note only. Input assignment commit
`9f9b6082974f0efd38e3f84d2712876e25cafb76`; original TSK SHA256
`498b06ca6033c980bfdfe24b54195f247dbc7a46d267c67a1a54b0028f5c3e8f`.
Frozen RECOVERY01-SCOPE is normative; the earlier proposal is not implementation
permission. HOST/RUN and fixed tests belong to separate authors.

## Decisions

- Optional exact `MockHostSession` with read-only `startup_guard` property;
  registry/database/lifetime verification remains HOST's public check_connection.
  Lazy import preserves the unqualified legacy in-memory test seam.
- Separate enrollment, append-only session and lease-owner tables bind profile,
  database UUID, session/runner and exact claim WorkRef. No legacy active lease
  gains proof through registration. Registration retry reconstructs its original
  orphan snapshot before calling mark_registered after commit.
- register_host/recover/finish_startup are explicit. Held compose/operate is a
  successful inspectable classification, with no writes, event, replay or ready
  transition. No ART/VER SQL, old-body adoption or operation dispatch occurs.
- Managed execution checks apply before execution replay, including consume,
  end_call and atomic ask/complete. Claim-WorkRef lookup distinguishes an old
  receipt from a newer session's active lease. Readonly ART/VER save-authority
  callbacks also require ready ownership; factual inspection is separate.
- Recover validates canonical call identity, strict WorkRef/index, both model
  and referenced Step reservations, full recorded source membership, reverse
  links, questions and artifact set before minting/writing. Reservation-only
  crashes remain consumed history. Source availability is not cessation proof.
- Only recover creates interrupted, with no Step/output. End-call's three
  accepted input outcomes are unchanged. All stored status consumers recognize
  interrupted; interrupted with a Step is corruption. Its get_call response
  explicitly includes step_id:null and may_enter:false.
- Recovery and release share a small latest-intent selector. Recovery separately
  fences nonterminal epoch once; terminal facts, completed Steps, answers,
  budgets and source availability remain unchanged. Preminted event and replay
  commit atomically with lease closure; BaseException rolls back and propagates.

## Verification and limits

The immutable fixed test SHA256 is
`2aa33aad2d401d42a84980a6523563fd28b8829f7449307406c0f53b5d843bf0`.
Actual HOST-dependent results are recorded after delivery below. Before delivery,
legacy test_tasks_v5 ran36 PASS and test_task_*.py ran38 PASS. test_tasks_*.py
ran106:84 existing PASS,22 ModuleNotFoundError for the undelivered HOST module;
no fixture body executed and no fake HOST was introduced. Final pre-HOST
legacy collection explicitly excluded only test_tasks_recovery_v5 from the
test_tasks_*.py and test_task_*.py patterns:122 PASS1.750s, exit0. Local log:
`/private/tmp/pal-recovery-tsk-legacy-122.log`.

This is author self-verification, not independent review or whole-C13 acceptance.
Subprocess lifetime proof, actual managed RUN connection and full regression are
Root-owned. Unresolved started compose/operate remain occupied; PRI/provider,
remote/child cessation, recovery ART adoption and whole-product acceptance are
NOT_RUN. Trusted callbacks are not sandboxed, and a callback's own COMMIT cannot
be undone retroactively.

## Prepared-source historical Step defect

Independent Sol found that recovery deeply checked only the occupied lease's
calls, while earlier leases' Steps received only backlink/started checks. An old
finished report with unknown status, bool index or unknown producing-call status
could therefore escape pre-settlement validation. Author reproduced unknown
status acceptance before the repair; local RED log:
`/private/tmp/pal-recovery-history-red.log`.

Recovery now feeds every call referenced by this revision's historical Steps
through the same strict call, model/Step reservation and closed Step validation,
using that call's own lease and original WorkRef. Only the occupied lease must
match its current claim WorkRef; historical epochs are not rewritten or forced
to equal the new claim. A historical started Step still refuses. Return value
continues to contain only the occupied lease's calls, so history cannot be
interrupted or mutated by settlement.

Author re-execution of Sol's two unchanged validator probes passes (three corrupt
variants plus intact-history preservation), 0.043s. Affected existing regression
passes122,1.891s. Logs: `/private/tmp/pal-recovery-history-independent-probes.log`,
`/private/tmp/pal-recovery-history-green.log`,
`/private/tmp/pal-recovery-history-regression.log`. This is author verification,
not Sol's exact-source approval. Next check: actual managed recovery must reject
these same mutations before any state/event/replay writes after HOST delivery.

## Actual HOST handoff

Root's source-only HOST dependency `bd92c4a2f7a061f9a99b5b652c3c2115286e656e`
was cherry-picked separately, equal SHA256
`e9b8f5eda1e01ec9a76ba52f3783845f302df262eea2248f4c5c36738a670208`.
This is the known returned initial SWE source. No unknown automatic-repair
output was adopted and no HOST source was changed by this author.

First actual fixed22 execution ran in0.537s, with8 failures and0 errors. All8
came from four test methods creating admitted calls but omitting their IDs from
settled's expected interrupted_call_ids argument (default empty). The dedicated
interruption expectation and scope require those IDs. Source output was not
weakened; the original failure log is retained at
`/private/tmp/pal-recovery-tsk-actual-host-first.log`, and Root/test owner were
asked to correct the fixture explicitly. Original fixed22 was not edited here.

All five independent integrity probe methods from note/probe commit
`8573d3666535125d392278e3a8b1687a90d27370` execute against this TSK and actual HOST:
PASS0.129s, including seven UUID/profile/session/claim corruptions, multiple
control epochs and public managed recovery rejection of corrupt historical
Steps. Log: `/private/tmp/pal-recovery-tsk-actual-independent-probes.log`.
These executions are author selfchecks of independently authored expectations;
independent final exact-source review remains separate.

Independent test-owner correction `0eeae0853ebd88cd141e234285b8897f7b4b323e`
was imported as a separate dependency. Four methods now retain the admitted
fixture call ID and assert it explicitly; no helper assertion was removed.
Corrected fixed22 SHA256:
`f659a9bc186d44a1d2ccd46799e8fa7073124ea9690d424c2226c9c760b351e1`.
With unchanged repaired TSK source and actual HOST:

```
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_tasks_recovery_v5.py -v
```

22 PASS0.618s, exit0. Log:
`/private/tmp/pal-recovery-tsk-actual-host-green.log`.
Source SHA256: `d5b207b24bac6c928960394ad0f4903506ebdb934cf25d838f334511883a7791`.
The same source passed existing122 and independent5 as recorded above. No full
suite or subprocess recovery claim; Root owns those subsequent integration checks.
