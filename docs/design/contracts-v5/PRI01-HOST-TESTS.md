# Independent PRI01 Host fixed acceptance

Frozen base1b1bd275fe76d470e5df796c79fed76c6eaa0cef; PRI01-SCOPE is authority.
Only tests/test_primary_host_v5.py and this note are authored. No Primary source,
shared scope, TSK candidate source, owner tests or canonical record edits.

39 methods, 28695 UTF8 bytes.
SHA256 `9afd8f43443e9994651d734bab37284815d6f223dfcf1f729af64108f4bddcd4`.

## Fixture dependencies and qualifications

No other TestCase imported/inherited or rediscovered. Uses actual MockHostSession,
MemoryStore, TaskStore, ArtifactStore, VerificationStore, EventReader, MockInvoker,
contracts and actual sanitizer. Fresh temporary file SQLite, managed registered
ready HOST, fixed Grant and same-connection owner gates/callbacks. Only Primary
invoke is labeled synchronous in-process mock; closed C15 request contains C01
JSON in its user message and returns JSONstr. No real model, provider, service,
old/live DB or callback subprocess. Owner failure tests inject public-method
protocol faults, not fake availability/authority. Private owner SQL only observes
existing shared charge counters or deliberately configures fixture ceilings.

Current dependencies additionally require adopted PRI01-MEM, PRI01-TSK and WIRE
APIs. TSK candidate uncommitted work was not copied, changed or accepted. Unknown
Primary schema is not guessed; source-specific session corruption/storage probes
belong to Root or independent review after actual schema exists. Cooperative
close/reopen startup cases do not claim process-death proof; Root owns process
barriers and whole flow.

## Fixed matrix

- Valid constructor; bad trusted config refuses. Public submit/get/run closed
  requests, sanitized duplicate identity, key conflict/session separation, byte
  bounds, no submit inference and exact original MEM key.
- Terminal/active duplicate runs and a separate Host instance reentry preserve
  durable entry; no reinference or charge. Actual C15 call/reservation binding,
  no transaction during callback; model0 and Step0 behavior.
- C01 current mandatory record, same-session recent6, truncation/drop-oldest and
  mandatory escaped-byte overflow before budget. Exact C11 closed shape/hash/
  usability and full ordered conservative exposure closure.
- Real new_work, question answer, same-Goal revision change and prior grant;
  wrong-but-listed control explicitly illustrates structural membership limit.
  Model grants/out-of-set/future tags do not dispatch or yield reply.
- Withheld historical A does not block unrelated new B under Root F5 disposition.
  Revision/question/new Goal fingerprint changes invalidate; epoch/state alone
  does not. Uncited exposed stop denies dispatch; later stop suppresses committed
  reply read without new effect. Own successful memory stop retains receipt and
  suppresses reply; separate immediate stop during callback makes none fail.
- Immediate structured cancel/stop bypass Primary inference/MEM admission/budget;
  no callback mutex. Owner namespace receipt equality and malformed kind/control.
- Definitive owner failure versus unavailable/exception/malformed applying outcome,
  no redispatch. Known owner commit with lost response reconciles receipt at startup;
  definitive absence interrupts, unknown lookup holds. Skipped PRI startup refuses.
- Caller active mutation transactions keep caller write/ownership; BaseException
  releases activity and known callback lifetime with startup interruption; terminal
  event failure preserves pending then uses original receipt without new callback.
  Callback exception/nontext is bounded, charged and not copied to persisted data.
- Fixed C14 terminal notice never model reply, no MEM assistant laundering.

Root clarifications before dispatch: C01 records and candidates are success VALUE
JSON, not Result wrappers. Accepted known failures project success+failed; uncertain
applying projects success+pending with no reply. Entrance refusal uses failed Result.
Constructor config refusal may be TypeError/ValueError/RuntimeError. Separate
structured stop invalidating none yields failed; only own confirmed effect may
retain committed history with suppressed reply. Terminal append failure yields
pending if readable, owner-effect applying can reconcile at startup. These are
Root technical dispositions, not invented additional Opus results.

## Baseline and limits

`/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_primary_host_v5.py -v`
Observed39 errors, all ModuleNotFoundError for absent pal.primary_host_v5. Log
/private/tmp/pal-primary-host-fixed-red.log. No feature assertion PASS claimed;
most coverage is unreachable until actual dependencies/source exist. No skips,
new source stub or relaxed alternative outcomes.

Separate fixture-only probe (without pretending a Primary implementation) constructs
actual owners, registers/startups, appends/creates/reads successfully; log
/private/tmp/pal-primary-host-owner-fixture.log. AST/diff checks PASS.
An initial helper name run accidentally overrode unittest.TestCase.run; renamed
run_turn before recording genuine absent-module baseline. Next author check must
preserve unittest lifecycle method names and verify actual absence-only errors.

Root writes Primary source only after this immutable commit, then separate reviewer
checks exact source. Root owns schema corruption, genuine simultaneous-process
entry, process cessation, whole sentence→ask/answer/change→saved/check/readback,
full regression and later authentic usefulness. These unit expectations prove no
semantic intention, quality rubric, real-provider profile, P001 or overall goal.
