# Personal Agent Lab

[English](README.md) | [日本語](README.ja.md)

Public greenfield development repository for a personal AI assistant focused on:
- natural conversation;
- durable memory and recall;
- task completion without user-side task management;
- Primary/Responder and Expert/Executor delegation;
- evidence-based finish and restart-safe continuation.

## Development status

This README describes public `main`. The newer `codex/pal-v5-co` development branch is tracked in [Draft PR #19](https://github.com/thattor/personal-agent-lab/pull/19), unmerged as checked on 2026-10-10. Its v5 interfaces and fixture evidence are separate from the implementation and acceptance recorded here.

**Stable-1 release candidate** on `main` awaits its one whole-flow owner usefulness evaluation and final release audit. Functional evidence is limited to the scope recorded in [C061](evidence/reviews/judgment-boundary/c061-target-function/README.md); the later finite-session extension is recorded in [STATE.md](STATE.md). This is not a Stable-1 release or overall project completion. D-031 ends additional prose-quality tuning; known editable-output imperfections are accepted for initial use.

**Stable-0 complete** under the D-019 functional-first definition. Version `stable-0`; [completion evidence and limits](evidence/final/stable0/README.md). All 20 required acceptance rows and the final 66 tests are recorded as PASS for that release; master Issue #1 closed.

## Start here
- [AGENTS.md](AGENTS.md) — development collaboration rules
- [CODEX-PROMPT.md](CODEX-PROMPT.md) — development goal prompt
- [SPEC.md](SPEC.md) — product scope and milestone boundaries
- [DESIGN.md](DESIGN.md) — accepted architecture
- [ACCEPTANCE.md](ACCEPTANCE.md) — definition of done and evidence gates
- [DECISIONS.md](DECISIONS.md) — durable decisions and reviewer conclusions
- [STATE.md](STATE.md) — implementation state and next action for this branch
- [Future image/audio design and research](docs/design/multimodal-qwen38-v1.md) — Qwen3.8-27B handoff candidate and retained evidence; not implemented

## Scope and acceptance
This repository is greenfield. Old PAL implementations and compatibility constraints are explicitly out of scope.

Stable-0 requires all structural and functional acceptance rows plus one direct human usefulness evaluation (D-019). The historical 72-hour soak is optional and remains unmet; functional acceptance makes no long-term stability claim.

## Setup

Python 3.11+ and the standard library only; no dependency install required.

```sh
git clone https://github.com/thattor/personal-agent-lab.git
cd personal-agent-lab
```

## Run deterministic tests

```sh
python3 -m unittest discover -s tests -v
```

The host canonical store is in [pal/store.py](pal/store.py). It is not an Executor capability. Draft bytes are bounded SQLite blobs and host receipts are verified by readback. The loopback UI defaults to mock. The historical official live functionality and direct human evaluation are recorded in [the Stable-0 audit](evidence/final/stable0/audit.json). See [STATE.md](STATE.md) for the branch's release state and completion record.

## Local conversation and inspect

```sh
python3 -m pal.server --db runtime/pal.db --port 8765
```

Open http://127.0.0.1:8765/. Ordinary chat/remember requests do not create Goals. In mock mode, “Make a draft …, do not send” creates a local draft; “stop that”, “pause that”, “resume that”, “correct that: …”, “answer: …”, and “forget that” apply to the current work/context. Inspect is read-only and shows Goal, Attempt, fixed criteria, receipts, rejected results and errors. No send/shell/remote write capability exists. Browser Session receipt contains accepted IDs, without message bodies; copy it before closing a test session when evidence is needed. Scripted receipts do not constitute human evaluation.

## Official native smoke

The [historical smoke script](scripts/live_smoke.py) takes positional proof-file and output-directory arguments; it has no `--help` interface. It is not a default setup step. Verify the existing signed-in official Pro account, quota, credits OFF and auto-reload OFF immediately before any explicitly authorized live run. Access proof expires after 15 minutes and native authentication is checked again. Do not fabricate a proof or enable paid fallback. Existing successful proof is a historical smoke record, not continuing authorization for new model calls. Default UI and optional soak make no native calls.

## Explicit bounded real-provider UI

After the controller actually verifies the existing official Pro account, quota, credits OFF and auto-reload OFF, it may create a metadata-only proof file with exactly `verified_at` (current Unix seconds), `no_extra_charge` (true), and `route` (official_claude_pro). No credential or token belongs in that file. Then start explicitly:

```sh
python3 -m pal.server --db runtime/functional.db --port 58500 --provider official_claude_pro --access-proof runtime/fresh-proof.json --native-call-limit 16
```

The proof must be fresh within15 minutes at startup and is consumed once per checkout. New-call admission defaults to15 minutes by both wall and elapsed time. For an explicitly authorized longer trial, `--native-session-seconds 8100` allows2 hours15 minutes from the fresh verification (strict integer1..8100). D032 uses that margin to provide at least2 hours remaining when readiness is announced. It does not increase the invocation budget. Failed startup burns a valid proof. Keep runtime/native-proof-use markers; copying a proof or changing its JSON formatting or session duration cannot renew it. This is a local operator guardrail, not cryptographic attestation or a global account limit. A trusted operator can forge/delete local metadata or use another checkout.

The shared conversation/task provider reserves at most16 generation invocations (configurable1–32). Primary and Expert share those slots; one draft request can use more than one. Failed calls consume a slot. This bounds host invocations, not unobserved CLI HTTP retries or token refreshes. Each auth phase has a10-second bound; generation is rechecked against the selected admission deadline after auth and has a120-second deadline. Admitted work may finish after the displayed deadline, with existing bounded supervisor cleanup grace. UI shows mode, remaining budget, absolute local admission deadline and closed failure codes. Sleep consumes the wall-clock window. Expiry/exhaustion/auth failure remains visible; no silent mock substitution, renewal or retry. Fresh verification and an explicit restart are required for newly authorized calls. A time-only extension must carry the actual remaining count into `--native-call-limit`; zero is not permission to reset to16. Failed work requires a new request. The no-extra-usage setting is checked when issuing the proof; per-call authentication does not independently recheck that setting.

Cancel/pause fence work results without killing unrelated conversation. An already admitted call can consume its slot after cancellation; shutdown or host death terminates supervised auth/model processes. Fixed functional scenarios are in ACCEPTANCE.md. Content checks and actual provider outputs are separate from the user's single usefulness evaluation.

## Optional historical soak

The monitor in [scripts/soak_monitor.py](scripts/soak_monitor.py) remains available for separately requested long-term observation. Earlier DBs, hash chains and human receipts are retained without repair or clock transfer. None of the stopped historical runs satisfies the original 72-hour criterion. D-019 removes only the mandatory time/turn/session quotas; all canonical, security and restart tests remain required.


## Stable-1 usage and current limitations

With the real provider explicitly selected, requests can be made naturally in Japanese or English. PAL uses conversation context to prepare local drafts. If it asks for essential missing information, answer in the same conversation. When several tasks could be the target, select the intended one before correcting it. Use conversation or the task's correction/cancel controls while work is active or paused. To change completed text, request a new draft and describe the changes. Open the draft to inspect the result and check it yourself before sending it elsewhere. External sending, publishing and scheduling are unavailable.

Ask PAL to remember information you want to retain. “Stop AI reference” prevents future AI use of the source; it does not physically delete saved history. Context is bounded to the most recent 30 records and the first 20 memory notes. Recall of every past conversation is not promised.

Draft wording and supplementary content can be imperfect. Corrections and feedback can inform later development, but automatic learning, automatic model updates and guaranteed improvement from experience are not implemented. Initial usability takes priority over further prose-quality testing. Permission, cost, target-selection, reference-stop and recovery safeguards remain in place.

Recorded real-model measurements use the existing official Claude/Opus route. Qwen3.8-27B is a capability reference; its operation in PAL is unverified. Image and audio input have future design material but are unavailable in this implementation. Real-provider use is a finite session after fresh verification of the existing subscription. Defaults are at most 16 calls and a 15-minute proof window; a request may use both a Primary and an Expert call. Expiry or budget exhaustion stops new calls without switching to a paid route; saved results remain viewable. Restart requires the operator to check current cost settings and explicitly start a new authorized session. Always-on autonomous execution, automatic monitoring and previously stopped schedules are not enabled.
