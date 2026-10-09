# Personal Agent Lab — current v5

PAL v5 develops a personal assistant that remembers relevant context, accepts work,
prepares saved results and returns evidence without requiring the user to manage
internal tasks. The whole goal is **NOT_MET**. Earlier Stable releases are history,
not the current operational implementation.

## Start here

Read [AGENTS.md](AGENTS.md), then the current sections of [STATE.md](STATE.md)
and [DECISIONS.md](DECISIONS.md). Current accepted interfaces are in
[PAL-contracts-v5](docs/design/contracts-v5/PAL-contracts-v5.md), read together with
the applicable frozen scope under `docs/design/contracts-v5/`. Latest explicit
owner decisions and current frozen scope govern older proposal descriptions.
[ACCEPTANCE.md](ACCEPTANCE.md) records version-bound evidence and remaining gaps.
[CODEX-PROMPT.md](CODEX-PROMPT.md) is the current development prompt.

## Implemented local slice and remaining work

Current v5 owners provide memory/reference-stop, intake and task controls,
reservations, managed mock recovery, saved artifacts, structural verification,
completion and read inspection. Primary mock composition and explicit native
Primary/Expert ownership boundaries have local fixture tests. Native fixture
endings and source approval are not real-provider qualification.

HTTP/UI: **NOT_IMPLEMENTED**. Real model qualification, real Expert connection,
authentic whole-flow usefulness and overall product acceptance: **NOT_MET**.
There is no replacement web-server startup command. Current development defaults
to mock; no provider invocation is needed for the checks below.

## Run local checks

Python standard library only. The integrated LEGACY01 candidate's normal discovery
must retain every current v5 case, including unsuffixed integrity probes:

```sh
python3 -E -s -B -m unittest discover -s tests -v
```

Existing demos use current owners and disposable local SQLite:

```sh
python3 -E -s -B scripts/demo_ask_v5.py
python3 -E -s -B scripts/demo_change_v5.py
python3 -E -s -B scripts/demo_readback_v5.py
```

The fixture lifetime tools `tools/verify_native_primary_lifetime_v5.py` and
`tools/verify_native_expert_lifetime_v5.py` test owned local process boundaries;
they do not invoke a provider or establish native/remote qualification. Primary
source is `pal/primary_host_v5.py`; native Expert orchestration is
`pal/native_expert_runner_v5.py`. Their current frozen scopes describe exact limits.

## Historical material

[Earlier product scope](docs/history/legacy-spec-pre-v5.md) and
[earlier architecture](docs/history/legacy-design-pre-v5.md) preserve exact prior
bodies. Historical evidence, receipts and unresolved outcomes remain retained.
They are not mandatory model inputs, current startup instructions or authority
for a new call. No old DB migration or compatibility layer is required.
