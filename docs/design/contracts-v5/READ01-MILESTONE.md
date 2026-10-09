# READ01 milestone candidate

Source ff1a1cc: VerificationStore.read, HostReader and bounded inspect_session/render
now let a local user follow C14 result and completed-history notice references to
the saved draft, fixed structural checks, current TSK state and present usability.
Same-consumer demo: `/opt/homebrew/bin/python3.13 -E -s -B scripts/demo_readback_v5.py`.
It owns only a temporary SQLite directory, accepts no DB path, sends nothing, and
uses a mock callable. Read `evidence/operations/read01-20261009/demo-green.log` for
the observed output and demo.json for structured before/after evidence.

Both before/after show completed; verification content/hash remain identical.
After source stop, verification is no longer usable and has explicit source-stop
notice evidence; the stopped record remains visible to user_view. Time labels
distinguish stored MEM/ART observation from current VER read time. Conservative
not-current without a cause is retained when a relevant notice is outside the
scanned window. No cross-owner atomic snapshot is promised.

Authorship: independent native Sol tests21 came first and then stopped. Actual
CO SWE b981736d authored VER.read (one repair after fixed10 found context error
precedence). New direct AGY cli1.3.2 claude-sonnet-5-5-high authored two real Python
modules as structured response, actual model confirmed in init, no file/tool
actions beyond finish. It passed fixed11. Root contract3 and actual owners found
missing behavior; independent CO Opus531650 confirms D1/D2/D3 and adds F1. Separate
CO SWE f2e11233 repairs D1/D2/D3 (fixed14). Root corrects real C11 optional fields
and its own connection-fixture key/case mistakes with original failures retained.

Focused36 now PASS0.152s (VER10, consumer11, regression6, actual owners9); the
actual demo additionally asserts complete/history/hash/source-stop/visible-MEM
behavior. Full regression is in verification.json, with exact source and exit.
Independent exact CO Opus de3d5d69 approves the final code. Its milestone
REFINE requests only reproducible demo provenance; Root has addressed it below.
Green component verifiers alone are not overall acceptance. The original Sonnet candidate is not
retroactively approved, and its author claim of NOT_RUN remains accurate.

CO stays0.4.5 on the qualified shared state. Actual measured peak3 owned CO calls
(Claude2/Devin1 during planning/review), not30; host cap12/adapter, remote quotas
unknown. Latest actual AGY preflight: Google AI Pro, AI Credits off, weekly63.20%,
five-hour97.41% remaining. No native author/reviewer was newly spawned underD039.
Old unknown/refused calls stay untouched; no reset/auth/cost/publication/live DB.

Remaining: not product/PRI/UI/provider activation, semantic quality, restart
recovery, external read tools or usefulness evidence. Proposed next value unit is
ASK01-PROPOSAL: save a mock question, wait safely for a record answer, then resume
the bounded work and inspect its outcome. Freeze exact same-transaction semantics
with technical consultation before assigning code; current READ01 acceptance is
independent of that proposal. C076's retained verify-authority note must accompany
the next RUN edit. Neither checkpoint introduces a new owner approval gate.

## Evidence provenance correction and Root disposition

Opus de3d5d69 Code APPROVE applies to unchanged ff1a1cc product source. Milestone
REFINE is preserved verbatim: the original demo-green.log/demo.json came from a
Root subprocess/runpy wrapper, not the demo script main block. The literal
assertion harness is now saved as scripts/verify_readback_demo_v5.py. Reproduce:

`/opt/homebrew/bin/python3.13 -E -s -B scripts/verify_readback_demo_v5.py --output-dir evidence/operations/read01-20261009/verified-demo`

This command PASSes and emits verified-demo/demo.json and demo.log. Original
wrapper outputs remain separate. verification.json now records review limits.
Root treats the local READ01 slice as MET after satisfying these explicit
provenance corrections, not by relabeling the Opus milestone REFINE as ALIGNED.
No source-code change after independent approval and no product/semantic claim.

Retain nonblocking Opus notes for actual consumer/model/UI expansion: prefix or
escape multiline display strings to prevent misleading layout; derive real-model
labels from provenance; share a structured notice identity before adding notices.
Hash recomputation is optional hardening, and the snapshot writer-blocking test
applies to rollback-journal mode; the one-read-TX guarantee is the claimed boundary.
Next ASK01 scope must resolve the review's source-stop/waiting/resume/lease cases
with ongoing SWE advice before assigning implementation.
