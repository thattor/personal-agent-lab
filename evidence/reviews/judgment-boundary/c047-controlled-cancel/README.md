# C047 actual controlled cancellation — scoped PASS

Pushed candidate `c44d3b4d46a68295a3c8d8a5502471a21daa7046`; unchanged product
`content:sha256:53a616572229072f80feea032b133b714b19627938c16568705b8700a4b436ad`.
[Predeclared two-input contract](../c047-controlled-cancel-contract.json), cap3/600s/
proof900s, no reserve or repeated samples. Official Opus and SWE reviews are in D029
C046/C047. Existing official Claude Pro/extra usage OFF was freshly observed; exact
CLI2.1.291 alias opus, server revision not exposed. Qwen3.8-27B was not called.

Controller entered the fixed request through actual conversation UI. After the actual
Executor returned, the existing worker fault seam held delivery before canonical apply.
UI and journal showed one running Goal/Attempt. The second UI input requested the same
Maple draft be stopped; actual Primary selected cancel. Goal epoch1→2 and state cancelled,
Attempt fenced, fixed revision/acceptance/sources unchanged. Releasing the result produced
exactly one host `stale artifact` rejection bound to that Attempt. No artifact, receipt,
outcome, question or approval was accepted. This proves controlled delivery fencing;
it does not prove upstream generation cancellation or natural timing reliability.

- [Six-record fsync journal](journal.jsonl), [actual two-turn UI receipt](receipt-ax.txt).
- [Before cancellation UI](running.jpg), [cancelled UI](cancelled.jpg).
- [Controller audit](controller-audit.json), [independent Astra audit](independent-audit.json).
- [Authorized teardown proof](teardown-check.json): exact ECONNREFUSED61, known PID gone,
  terminal exit0; journal normal closure200.824s, no cleanup errors. Its temporary browser
  tab was closed. No unrelated process/tab/DB or blocked artifact route was touched.
- [268 full tests PASS24.048s](../c047-full.txt), prior to actual run on identical source.

All17 product and six frozen harness files match after the run; read-only DB integrity
passes and counts match the final snapshot. Source DB stays ignored at
`runtime/c047-controlled-cancel/state.sqlite`; no Store constructor/migration/repair or
artifact-body access was used by audits. Three native slots consumed, two complete Primary
turns, one actual Executor return. Controller inputs are synthetic; no human evaluation.

Observer limitations/errors are preserved. Initial port check treated any connect error
as closure without recording errno; restricted sandbox EPERM can mimic it. Retained
`controller-audit-initial.json` is invalid for that claim. Separate authorized check proves
actual refusal/process exit; independent auditor correctly labels its denied port check
unavailable. Screenshot API returned raw JPEG bytes (not a data URL); corrected saving
before cancel input, with no extra model call. Receipt summary was not matched by a DOM
button role despite AX's button label; observed exact text worked. No canonical write or
resampling resulted from these observer corrections. See docs/DEFECTS.md.

Historical C035/C045 timing outcomes remain unchanged. C045 blocked ABS-A2 and nine
artifact-dependent cases remain unverified/unrun; no whole N1 row or release promotion.
One actual version-bound whole-flow usefulness evaluation and final acceptance audit
remain. Stable0 remains released; Stable1 and overall PAL remain incomplete.
