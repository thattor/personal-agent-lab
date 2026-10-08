# Personal Agent Lab

Private greenfield development repository for an open-sourceable personal AI assistant focused on:
- natural conversation;
- durable memory and recall;
- task completion without user-side task management;
- Primary/Responder and Expert/Executor delegation;
- evidence-based finish and restart-safe continuation.

## Current goal
**Stable-0 complete** under the D-019 functional-first definition. Version `stable-0`; [completion evidence and limits](evidence/final/stable0/README.md). All20 required acceptance rows and final66 tests PASS; master Issue #1 closed.

## Start here
- AGENTS.md — rules for Codex, Opus, and SWE-2 High collaboration
- CODEX-PROMPT.md — paste/run this as the Codex goal prompt
- SPEC.md — Stable-0 product scope
- DESIGN.md — accepted architecture
- ACCEPTANCE.md — definition of done and evidence gates
- DECISIONS.md — durable decisions and reviewer conclusions
- STATE.md — current implementation state and next action
- [Future image/audio design and research](docs/design/multimodal-qwen38-v1.md) — Qwen3.8-27B handoff candidate and retained evidence; not implemented

## Important
This repository is greenfield. Old PAL implementations and compatibility constraints are explicitly out of scope.

Stable-0 requires all structural and functional acceptance rows plus one direct human usefulness evaluation (D-019). The historical 72-hour soak is optional and remains unmet; functional acceptance makes no long-term stability claim.

## Run deterministic tests

Python standard library only; no dependency install required.

```sh
python3 -m unittest discover -s tests -v
```

The host canonical store is in `pal/store.py`. It is not an Executor capability. Draft bytes are bounded SQLite blobs and host receipts are verified by readback. The loopback UI defaults to mock. The explicit official live functionality and direct human evaluation are recorded in evidence/final/stable0/audit.json. See STATE.md for the current release state and completion record.

## Local conversation and inspect

```sh
python3 -m pal.server --db runtime/pal.db --port 8765
```

Open http://127.0.0.1:8765/. Ordinary chat/remember requests do not create Goals. “Make a draft …, do not send” creates a local draft; “stop that”, “pause that”, “resume that”, “correct that: …”, “answer: …”, and “forget that” apply to the current work/context. Inspect is read-only and shows Goal, Attempt, fixed criteria, receipts, rejected results and errors. No send/shell/remote write capability exists. Browser Session receipt contains accepted IDs, without message bodies; copy it before closing a test session when evidence is needed. Scripted receipts do not constitute human evaluation.

## Official native smoke

`scripts/live_smoke.py --help` documents the explicit proof-file route. Verify the existing signed-in official Pro account, quota, credits OFF and auto-reload OFF immediately before running. Access proof expires after 15 minutes and native authentication is checked again. Do not fabricate a proof or enable paid fallback. Existing successful proof is an historical smoke record, not continuing authorization for new model calls. Default UI and optional soak make no native calls.

## Explicit bounded real-provider UI

After the controller actually verifies the existing official Pro account, quota, credits OFF and auto-reload OFF, it may create a metadata-only proof file with exactly `verified_at` (current Unix seconds), `no_extra_charge` (true), and `route` (official_claude_pro). No credential or token belongs in that file. Then start explicitly:

```sh
python3 -m pal.server --db runtime/functional.db --port 58500 --provider official_claude_pro --access-proof runtime/fresh-proof.json --native-call-limit 16
```

The proof is consumed once per checkout and expires after 15 minutes by both wall and elapsed time. Failed startup burns a valid proof. Keep runtime/native-proof-use markers; copying a proof or changing its JSON formatting cannot renew it. This is a local operator guardrail, not cryptographic attestation or a global account limit. A trusted operator can forge/delete local metadata or use another checkout.

The shared conversation/task provider reserves at most 16 generation invocations (configurable 1–32). Failed calls consume a slot. This bounds host invocations, not unobserved CLI HTTP retries or token refreshes. Each auth phase has a 10-second bound; generation is rechecked for freshness after auth and has a 120-second deadline. A call admitted just before expiry can finish within 1020 seconds of proof verification. UI shows mode, remaining budget and closed failure codes; read-only provider status also exposes the expiry timestamp. Expiry/exhaustion/auth failure remains visible; no silent mock substitution, renewal or retry. Fresh verification and an explicit restart are required for new calls. Failed work requires a new request.

Cancel/pause fence work results without killing unrelated conversation. An already admitted call can consume its slot after cancellation; shutdown or host death terminates supervised auth/model processes. Fixed functional scenarios are in ACCEPTANCE.md. Content checks and actual provider outputs are separate from the user's single usefulness evaluation.

## Optional historical soak

The monitor in scripts/soak_monitor.py remains available for separately requested long-term observation. Earlier DBs, hash chains and human receipts are retained without repair or clock transfer. None of the stopped historical runs satisfies the original 72-hour criterion. D-019 removes only the mandatory time/turn/session quotas; all canonical, security and restart tests remain required.
