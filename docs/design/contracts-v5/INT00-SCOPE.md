# INT-00: shared v5 wire contracts

Owner: SOL. Input version: PAL-contracts-v5 / C01–C15, 2026-10-09.
This is a scoped development preparation milestone. Imported v5 documents remain
design candidates; external capability adoption, product activation and human
usefulness are separate decisions. The current owner explicitly authorized CO
development, necessary private development materials and actual available capacity.

## Assigned sequence and ownership

The planner must produce exactly three sequential steps: design, implement, review.
The design step examines v5 common definitions and the boundaries relevant to this
scope; its output is an explicit input to implementation. Opus 5.5 handles design
and independent review in separate invocations; SWE-2 High implements the files.
SOL alone owns canonical records, contract adoption, integration and shared DB.
Each CO step uses the exact committed baseline passed by the CLI. CO owns its
isolated workspace; it must not mutate the caller repository or other projects.

Read only the three imported v5 documents, this scope and pal/__init__.py.
Create only:

- pal/contracts_v5.py
- tests/test_contracts_v5.py
- tests/fixtures/contracts_v5.json
- docs/design/contracts-v5/INT00-IMPLEMENTATION.md

Use Python standard library only. No shell, network, provider calls, SQLite, UI,
runtime changes, credentials, live data or new dependencies in the implementation.
Do not implement C01–C15 services, a second state machine, a connector or new model
selection. Downstream modules depend on these shared wire definitions; they wait
for SOL's reviewed contract disposition. No other worker may change these files.

## Function and public surface

Implement the shared section-3 values: WorkRef, Ref, DraftCondition, Condition,
Target (repository, issue_numbers, files with path/ref), DraftBrief, Brief, Limits
and Grant. Also provide the closed Result error vocabulary and C12 Action shapes.
Use a small public parsing/serialization API documented with runnable examples.
Prefer immutable values and normalized serialization; do not build a schema
framework. Equality and round trips must preserve all information.

Use the documented exact fields, optional fields and enums. Reject wrong strict
types (including bool as int), missing/extra keys, invalid enum members, empty
IDs, revision <1, epoch <0, empty conditions and negative limits. Zero limits
are valid exhausted budgets; no default unlimited value or permission expansion.
Reject non-JSON values, non-finite numbers and duplicate JSON keys at the raw JSON
boundary. Strings must be valid UTF-8. Do not invent semantic quality rules or
restrict ordinary content merely to simplify a parser.

Define and document one wire discriminator for Action, e.g. kind=lookup, operate,
ask, compose, verify or report, and use it in every example. Nested arguments are
JSON objects and retain their content. Result.ok is strictly bool; success carries
only value, failure only error {code,message,refs}. Invalid shape raises a bounded
ContractError with code=invalid_input without echoing raw model content.

DraftBrief accepts conditions without IDs and rejects host condition IDs. Brief
accepts formal Condition IDs; this module must not mint them. Model-originated
DraftBrief/Action parsing receives the allowed input Ref set and rejects any
unprovided Ref. That check does not authorize capabilities/repositories, prove
source availability, verify semantic scope, or replace host transaction fencing.
Do not silently normalize one Ref kind into another. Immutable host values are
data, not credentials or ownership proof.

## Shared cases and completion

The JSON fixture is reusable by future producers/consumers, contains only synthetic
data, and labels each input as accepted/rejected plus its intended contract case.
At minimum cover WorkRef boundaries; all Ref kinds; C03/CT-24 draft-to-formal
condition-ID separation; strict Result variants and error enum; every C12 action;
unprovided refs; zero/negative grant budgets; invalid nested shape and duplicate
keys at the raw JSON boundary. Tests consume the fixture and assert expected
public behavior. Add focused tests for immutability and raw JSON handling where
fixture representation cannot express the condition. Avoid implementation mirrors.

Verification: /opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests
-p test_contracts_v5.py -v. The reviewer independently checks the resulting files,
v5 consistency, case coverage, absence of out-of-scope behavior and verifier output.
Return request_changes for a concrete blocker. SOL will inspect the diff and run
the required complete unittest suite after integration.

INT00-IMPLEMENTATION.md records the implemented API, wire decisions, design findings
and their disposition, exact test scope and remaining problems. If design finds a
material v5 contradiction, describe it as unresolved and keep it out of this pure
implementation; do not silently adopt new product authority. CT-04/07/08/25 and
other persistence/control races, E2E-01–09, real models/services and human value
evaluation remain NOT RUN. Parsing examples do not count as those service tests.

Return all four file contents as the CLI requires, test results, review findings
and remaining limitations. CO verified covers this verifier and file version;
it does not mean PAL or all v5 contracts are complete.
