# Current PAL v5 design references

The accepted contract-first module boundaries and sole owners are defined by
[PAL-contracts-v5](docs/design/contracts-v5/PAL-contracts-v5.md) and applicable
frozen implementation scopes. Current [STATE.md](STATE.md) and
[DECISIONS.md](DECISIONS.md) distinguish adopted interfaces, implemented local
slices, unresolved outcomes and proposals. Read the specific scope before changing
an owner; this file adopts no additional architecture or proof criterion.

Current owners include memory, intake/tasks, artifacts, structural verification,
events/read inspection and Primary composition. Mock and explicit native runners
have different evidence/entry semantics. PAL core imports no CO; an external
wrapper's public runtime dependency does not become product qualification.
Current HTTP/UI remains NOT_IMPLEMENTED. Real qualification/usefulness and whole
goal remain NOT_MET. Old operational engines are outside the current import graph
and are targeted for removal under LEGACY01, without compatibility wrappers.

The exact earlier architecture body is [historical](docs/history/legacy-design-pre-v5.md).
Do not use it as a mandatory model input or current startup guide.
