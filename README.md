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

The host canonical store is in `pal/store.py`. It is not an Executor capability. Draft bytes are bounded SQLite blobs and host receipts are verified by readback. There is no live runtime/UI yet. See STATE.md for exact continuation.
