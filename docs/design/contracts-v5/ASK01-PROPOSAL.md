# ASK01 next value proposal (not a frozen implementation contract)

After READ01 passes real readback and independent review, connect one mock Expert
question to a saved user answer and a later completed draft. This is existing
v5 C04/C10/C12/C13/C14 preparation under D038/D039, not a new user-facing rollout.
Current compose-only flow can produce a draft but cannot durably wait for a fact.
The value is to preserve the actual question and answer across the work lifecycle,
not to score natural-language question quality.

Proposed minimal slice: TaskStore owns one open question for the exact work and
started ask Step, atomically saves question+finished Step+waiting_input+question
event and idempotent receipt. Host releases the already-ended local model call
without turning waiting_input into queued. An answer through existing control
uses the saved record Ref, checks question/revision/source availability, attaches
the input and resolves the question once; waiting work becomes queued, paused
work remains paused. MockRunner dispatches ask and ends its bounded turn, then
resumes from a separately submitted answer on the next explicit local invocation.
C02/checkpoint expose the actual open question; no invented question Ref kind.
Root owns a real temporary-SQLite ask -> waiting -> answer -> compose -> verify
-> completed -> current readback demonstration.

Do not implement yet: first obtain exact contract/persistence advice and resolve
release/lease/current-epoch/error/replay semantics in one shared scope. In
particular reconcile source-stop, concurrent pause/cancel, changed epoch versus
revision, answer replay with later terminal state, and storage failure/lost reply.
Carry C076's verify-authority handling note into the next RUN change. Keep
unknown model outcome retention unchanged; no provider cessation or recovery
claim. No C10.change, broad recovery, semantic verifier, UI/Primary/real model,
external source adapter, auth/payment, live DB/migration, publication or schedule.

Suggested independent ownership after freezing: SWE-2 High TSK persistence and
RUN code in separate file workspaces; AGY Sonnet5.5 small acceptance/helper task
where it adds value, with independent Opus code/design evaluation. SOL owns
contracts, integration and real evidence. Conserve native Codex calls. No need
to manufacture parallel tasks to reach30. Existing owner authority covers this
preparation; uncertain technical semantics require technical advice, not an
extra owner approval gate.
