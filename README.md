# Personal Agent Lab

Private greenfield development repository for an open-sourceable personal AI assistant focused on:
- natural conversation;
- durable memory and recall;
- task completion without user-side task management;
- Primary/Responder and Expert/Executor delegation;
- evidence-based finish and restart-safe continuation.

## Current goal
Reach **Stable-0**, the minimum stable implementation defined in ACCEPTANCE.md.

## Start here
- AGENTS.md — rules for Codex, Opus, and SWE-2 High collaboration
- CODEX-PROMPT.md — paste/run this as the Codex goal prompt
- SPEC.md — Stable-0 product scope
- DESIGN.md — accepted architecture
- ACCEPTANCE.md — definition of done and evidence gates
- DECISIONS.md — durable decisions and reviewer conclusions
- STATE.md — current implementation state and next action

## Important
This repository is greenfield. Old PAL implementations and compatibility constraints are explicitly out of scope.

Stable-0 is not complete until all required acceptance rows pass and the 72-hour soak finishes without manual canonical-state repair.

## Run deterministic tests

Python standard library only; no dependency install required.

```sh
python3 -m unittest discover -s tests -v
```

The host canonical store is in `pal/store.py`. It is not an Executor capability. Draft bytes are bounded SQLite blobs and host receipts are verified by readback. The loopback UI defaults to mock. The explicit official live smoke is evidenced separately; Stable-0 remains incomplete until the human-use soak passes. See STATE.md for exact continuation.

## Local conversation and inspect

```sh
python3 -m pal.server --db runtime/pal.db --port 8765
```

Open http://127.0.0.1:8765/. Ordinary chat/remember requests do not create Goals. “Make a draft …, do not send” creates a local draft; “stop that”, “pause that”, “resume that”, “correct that: …”, “answer: …”, and “forget that” apply to the current work/context. Inspect is read-only and shows Goal, Attempt, fixed criteria, receipts, rejected results and errors. No send/shell/remote write capability exists. Browser Session receipt contains accepted IDs, without message bodies; copy it before closing a human soak session. Confirm the first session receipt with the controller before creating a draft so the planned unfinished restart can be armed.

## Official native smoke

`scripts/live_smoke.py --help` documents the explicit proof-file route. Verify the existing signed-in official Pro account, quota, credits OFF and auto-reload OFF immediately before running. Access proof expires after 15 minutes and native authentication is checked again. Do not fabricate a proof or enable paid fallback. Existing successful proof is an historical smoke record, not continuing authorization for new model calls. Default UI and soak make no native calls.

## 72-hour human-use soak

After all S0-01–12 PASS and a clean baseline commit:

```sh
python3 scripts/soak_monitor.py --mode soak --run runtime/soak-<fresh-name> --port 58500
```

Keep the monitor running. It owns a mock loopback app with bounded 10-second draft latency, makes read-only invariant/health measurements every five minutes, and performs a supported restart during unfinished work from an explicitly attested human session. A preflight uses separate data and can never satisfy S0-13. Source/semantics changes, unexplained gaps, errors or canonical repair invalidate the run. Sleep/wake is disclosed as downtime; unavailable supporting evidence fails the run. Stopping before final audit requires a new run.

The actual user must type at least 20 turns in at least 3 sessions spanning at least 72 hours, create at least 5 Goals, cancel at least once, and correct or stop reference at least once. Synthetic probes do not count. Session receipts plus the user's explicit attestation identify qualifying sessions; host-observed times, not browser clocks, establish the span. The controller records a human-attestation.json only after that direct confirmation, with `source: direct_user_attestation` and the confirmed `session_ids`. No message text is needed in the attestation. `candidate.json` is a measurement result and cannot declare Stable-0. Final full tests, audit, evidence commit and master Issue closure are still required.

After a qualifying candidate, the controller reruns the full suite, audits all acceptance evidence and atomically writes controller-complete.json with final_full_suite/acceptance_audit PASS, test_log (repository-relative) and test_log_sha256. The monitor checks the real evidence file and anchors controller_audit_complete to the qualifying candidate. Only then does an orderly stop preserve the run. Historical verification uses pal.soak.historical_candidate over EvidenceLog.read output; it rechecks the entire chain and qualifying counts/time rather than trusting candidate.json. This marker is controller audit metadata, never a product/model capability.
