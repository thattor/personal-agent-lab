# Current model-led Primary target/crash coverage

Product/prompt stays frozen at1a14de9. Test-only additions use existing reviewed fault
hooks, real subprocess SIGKILL, and scripted provider outputs; no live-model claim.

25 focused tests PASS in [the log](primary-target-crash-current.txt). Added scenarios:

- Ambiguous target produces a persisted conversational question and no target mutation;
  SIGKILL mid-transaction/before/after commit yields atomic rollback or one stored reply.
- Correction selects one of two Goals; kill at control-mid/Primary-mid/before/after
  commit preserves full rollback or exactly one revision with unchanged criteria,
  genuine source bindings and fenced previous attempt. Other Goal remains unchanged.
- Runtime kill before/after commit records one scripted Primary invocation. Restart
  and replay never invoke Primary again or duplicate effects/replies. Legitimate Expert
  continuation after committed correction is separate from Primary replay.

Initial test-only export mistakes used nonexistent inspect selections projection;
retained error logs show the diagnosis. Tests use the actual Store.selections() API.
No product defect or canonical-row repair was found. This covers N1-04 affected current
Primary boundaries, not semantic model correctness or actual UI target/cancel behavior.
