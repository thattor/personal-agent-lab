# LEGACY01/1 — remove the old PAL operational engine

Root freezes this deletion scope atdbf0df115dfb4fa9693db68ca8e02f1b0c944fee.
The latest actual owner instruction says: 「palの旧版を参照している可能性が
あるなら旧版の削除をしてください。互換は必要ありません」. The owner turn
was read in the existing human-design lane; its raw identity remains local.

## Current defect and outcome

Independent source and documentation audits confirm that README launches
`pal.server`, which serves the old pal/web and old Runtime/Store/NativeClaude.
Current v5 owners have a separate closed import graph; their only common pure
utility is pal.sanitize. No v5 HTTP/UI implementation exists. Remove the old
operational engine, its exclusive scripts/UI/tests and current startup/model-input
instructions. Retain current owner semantics and all current validation cases.
Do not add compatibility aliases, migrate old data or advertise a replacement UI.

## Owners and write scope

Astra owns an isolated deletion-only source commit: the old pal modules
classification, controls, draft_envelope, native, native_supervisor, primary,
runtime, server, soak, store and template_intake, the pal/web directory, and the
old scripts live_cancel_probe/live_evidence/live_gate/live_operator/live_runner/
live_smoke/primary_qualification/soak_monitor. Remove their exclusive old tests,
old UI test scripts and test helpers only after tracing their imports. Keep all
tests that use current v5 owners, including test_v5_* and the unsuffixed
test_recovery02_event_marker_probe.py. Keep fixtures used by current v5 tests or
native qualification. A name or suffix alone is never a deletion criterion.
Return exact deleted-path inventory and current-test/fixture dependency proof.

Separate Sol owns README.md, CODEX-PROMPT.md, AGENTS.md, SPEC.md and DESIGN.md in
an isolated documentation commit. Give one current v5 entry; do not read old
specifications as mandatory model inputs. SPEC/DESIGN may move their exact old
bodies to explicitly historical docs before current files are replaced with
concise factual v5 references. Git preserves deleted old code; do not copy it
into an operational archive. Existing history/evidence remains outside current
input and startup instructions. No new design or completion criteria are adopted.

Root owns shared STATE/DECISIONS/ACCEPTANCE/CHECKPOINTS/DEFECTS, the shared v5
contract header, integration and publication. Separate source reviewers verify
author diffs. No concurrent writes to shared contracts, DBs or the canonical tree.

## Preservation and limits

Delete only identified tracked code in the current candidate. No broad directory
cleanup, old-checkout deletion, live or historical DB inspection/migration, raw
conversation removal, provider execution, unknown-call/CO/state/ledger change,
new auth/service/cost or deploy. Historic evidence, scripts embedded as immutable
historic observations, receipts, old outcomes and source commits stay preserved.
Root's exact-current-checkout open-file query returned no matching open path and
no stderr before this freeze. Static audits do not prove global old services ceased.
Do not stop unrelated processes or infer that deletion completes the product.

## Acceptance

* Current operational pal/scripts/tools import closure reaches no removed old
  engine; pal.sanitize remains the unchanged pure utility where actually used.
* Current mandatory docs/model inputs identify v5, its accepted frozen contracts,
  mock default and remaining real connection/UI/usefulness gaps.
* Removed pal.server is unavailable; no current instruction advertises it.
* Every current-v5 test method is retained. Run normal full discovery after old
  exclusive tests are removed, report the new count and its deletion reason, and
  do not present a lower count as proof of removed old behavior.
* Run the three existing mock demos and the two existing current native lifetime
  fixture verifiers against the integrated candidate, without a provider call.
* Preserve previous1210/full/crash evidence as version-bound history; Root checks
  integrated diffs and independent reviews before committing final canon.

Whole goal remains NOT_MET. The next product work still requires actual model
qualification and a v5 UI, not recreation of the removed old engine.
