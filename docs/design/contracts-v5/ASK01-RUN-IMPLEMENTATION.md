# ASK01/1 native RUN implementation

Author base `744ca12c130ce8ca8c7ac7787292c4e871182335`, isolated
`/private/tmp/pal-ask-run-sol-20261009`, `codex/pal-ask-run-sol`.
Only `pal/mock_runner_v5.py` and this note are owned. Fixed independent
`tests/test_mock_ask_v5.py` remains byte-identical:
`3e4552a251d5d55c16ce7496d34d2df4599f70243c429c4b90b92b778847ad36`.

The frozen ASK01-SCOPE/ASK01-RUN-TEST-PLAN govern this change. Native Sol implements
RUN after AGY's approval rejection before any model call; no Sonnet code/output,
unknown-call retry or parallel owner output is adopted. No TSK, contract, tests,
canonical records, runtime, live DB, provider/auth/cost or other project changes.

## Behavior

After begin_step, ask uses the persisted closed Step/AskAction and canonical
`dumps(['C04.ask',work,step_id])`, preserving duplicate selected Ref entries.
It retries the identical public ask request at most three times on unavailable,
then performs exactly one get_question_by_key request. Strict waiting receipt
validation requires the exact current WorkRef, nonempty question ID and closed
three-key waiting_input shape. Success reports waiting, finished Step/call and
pending-link diagnostics without finish_step or release. A malformed owner response
is bounded unavailable. Authority refusal attempts release(yield), preserving
failure if occupancy cannot safely be released; unknown outcomes never authorize
failed release or another Expert invocation. Ordinary callback exceptions are
bounded; BaseException propagates with no invented cessation or completion.

A single started tail ask may reenter only after public get_call confirms exact
call/lease/current WorkRef/index/Step binding and returned status. Bool indices and
unended/foreign/malformed calls fail closed. Reentry uses the same C04 identity,
without reservation or inference. Other started Steps retain the previous recovery
boundary. This is local retained-runner continuation, not restart adoption.

Claimed pending_inputs are validated before reservation: unique question/Step IDs,
closed metadata, record answer Ref, producing finished ask Step with matching
Goal/revision, legitimate historical epoch and increasing producing index. C12
includes only links whose answer Ref is in the usable context and whose ask Step
passes the existing full source-provenance filtering. Empty eligible lists are
omitted. All claimed links remain in local released/waiting/completed diagnostics;
no body or reconstructed question association is inserted into source content.

The previous C076 verification-authority path called generic failed(), which could
terminalize a work after current controls. It now falls through to the bounded
loop; execution-context conflict/stale/denied settles through release(yield).
Required-source read/registration failures remain their existing separate path.
Source reads also bound ordinary malformed/throwing callbacks as unavailable;
BaseException still propagates. No additional persistence engine or model retry.

## Author evidence

Final commands:

```
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_mock_ask_v5.py -v
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p 'test_mock*.py' -v
```

Fixed15 PASS0.014s/exit0; mock77 PASS0.418s/exit0. Logs:
`/private/tmp/pal-ask-run-sol-fixed-tests.log` and
`/private/tmp/pal-ask-run-sol-mock-tests.log`.
Two additional in-memory public-double probes confirm KeyboardInterrupt/SystemExit
from ask propagate with one model call, retained started Step and no release or
generic finish. No fixed test was changed. `git diff --check` PASS.

The fixed ASK tests use explicitly synthetic owners and do not prove actual ASK
storage, controls, linked answer invalidation or completed/readback connection.
The77 include prior mock/real-owner composition tests on unchanged existing owners;
they do not integrate Astra's separate ASK TSK source. Root must integrate that
source, execute actual temporary SQLite consumer/demo/full regression, and obtain
independent RUN review before claiming the ASK milestone. No full product, semantic
answer sufficiency, live operation or general restart recovery is established.

## Independent-review correction: linked historical ask Step closure

Independent RUN review of `a7ceb54` reproduced that a linked finished historical
ask Step with `error=1`, `error='ask failed'` or an unknown field could enter C12.
Root confirmed the issue and owns the separate red regression. The author had
validated the linkage, action, state and binding without checking the Step's closed
shape, so valid association could conceal malformed historical Step data.

The bounded correction requires a linked finished ask Step to have exactly the
six committed C04 fields: step_id/work_ref/index/action/status/result_refs. No
error/extra field is accepted. This is the same closed invariant as the committed
ask path. Matching Goal/revision and legitimate historical epochs remain accepted;
no broader historical Step semantics or source-owner change is introduced.

Author green probes exercise the three independently reported mutations: all
refused before reservation/inference. Fixed15 PASS0.013s/exit0 and mock77
PASS0.401s/exit0; existing old-epoch linkage cases remain green. Logs:
`/private/tmp/pal-ask-run-sol-review-fixed-tests.log` and
`/private/tmp/pal-ask-run-sol-review-mock-tests.log`. Fixed15 hash is unchanged.
No new test file is authored here; Root's independent regression and rereview
remain separate evidence.

Prevention/next check: when carrying stored public Steps into C12, validate the
closed committed shape alongside relationship and lifecycle checks. Reuse Root's
extra/error-field regression for later linkage changes. This correction does not
prove every historical Step kind or actual ASK integration; Root still owns those
acceptance boundaries and the independent reviewer must assess this exact fix.
