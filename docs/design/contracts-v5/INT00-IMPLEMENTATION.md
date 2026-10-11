# INT00/1 implementation

Scope: `PAL-v5-common-wire / INT00/1`, from PAL-contracts-v5 section 3 and C12.
Implementation uses the completed [Opus design](../../../evidence/operations/co-int00-20261009/opus-design.txt)
and [SOL disposition](../../../evidence/operations/co-int00-20261009/design-disposition.json).
D036 authorizes this isolated native Astra implementation on baseline
`a6983916ce78714fd97ae2320be8e374924f4313`; it does not change the accepted semantics.
No old CO workspace/state, existing helper, service, DB or canonical record is changed.

## Public API

`pal.contracts_v5` exports frozen, slotted dataclasses: `WorkRef`, `Ref`,
`DraftCondition`, `Condition`, `TargetFile`, `Target`, `DraftBrief`, `Brief`,
`Limits`, `Grant`, `ErrorInfo`, `Result`, and six Action classes (`LookupAction`,
`OperateAction`, `AskAction`, `ComposeAction`, `VerifyAction`, `ReportAction`).
`Action` is their union. `RefKind`, `CheckKind`, `ErrorCode`, `ActionKind` and
`MediaType` are closed string enums.

- `loads(raw)` accepts exact str or UTF-8 bytes and returns plain JSON.
- `Type.from_json(data)` parses strict decoded wire data. `action_from_json(data)`
  selects the Action variant; an individual Action's `from_json` checks its kind.
- `value.to_json()` returns fresh plain dict/list data. `dumps(value)` accepts a
  supported contract value or exact plain JSON and emits sorted compact JSON with
  Unicode preserved. It rejects Python tuples at the plain-JSON boundary.
- Constructors validate their fields, accept list/tuple for typed sequences and
  snapshot those sequences as tuples. Decoded wire arrays must be exact lists.
- `JsonValue(data)` snapshots arbitrary valid JSON as immutable normalized text;
  `.data` returns recursively immutable mappings/tuples and `.to_json()` fresh
  plain JSON. Object key order and numeric lexical spellings are normalized;
  integer/float/bool distinctions and negative floating zero are preserved in
  serialization, equality and hashing.
- `Result.from_json(data, value_decoder=WorkRef.from_json)` optionally binds a
  success value to a host-selected decoder. The decoder must return one of these
  immutable contract types or JsonValue and preserve the entire original wire
  value. Mutable, lossy or failing decoder output raises bounded ContractError.
  Without a decoder, success values use JsonValue, including JSON null.
  `Result.success(value)` and `Result.failure(code, message, refs=())` are helpers.
- `parse_model_draft_brief(raw, *, allowed_refs)` and
  `parse_model_action(raw, *, allowed_refs)` require the explicit iterable of Ref
  objects and check exact `(kind, id)` membership. A malformed allowed set is host
  misuse (TypeError). Host shape parsers do not perform this model membership check.

Runnable example (repository root):

```python
from pal.contracts_v5 import Ref, WorkRef, Result, dumps, loads, parse_model_action

allowed = [Ref('source', 'source:synthetic')]
action = parse_model_action(
    '{"kind":"compose","content":"Summary",'
    '"media_type":"text/markdown",'
    '"source_refs":[{"kind":"source","id":"source:synthetic"}]}',
    allowed_refs=allowed,
)
assert loads(dumps(action)) == action.to_json()
result = Result.from_json(
    {'ok': True, 'value': {'goal_id': 'g', 'revision': 1, 'epoch': 0}},
    value_decoder=WorkRef.from_json,
)
assert result.value == WorkRef('g', 1, 0)
```

## Wire decisions and design disposition

The flat `kind` field is the sole Action discriminator. Fields are exactly C12's:
lookup(query, optional source_refs), operate(capability, arguments, source_refs),
ask(question, missing_fact, source_refs), compose(content, media_type, source_refs),
verify(artifact_refs), report(summary). Arguments must be a JSON object and retain
ordinary nested content. Ref-shaped objects inside opaque arguments are adapter
payload, not additional C12 source selection fields. Adapters must enforce their
own resource/argument contracts.

| Finding | INT00 handling and remaining owner obligation |
|---|---|
| U1 | Closed eight-code ErrorCode only. No state-to-error mapper; later host tests bind unknown ID/not_found, revision/stale and state/conflict. |
| U2 | Generic immutable Result value, with optional lossless typed decoder. Providers must bind their actual result types. |
| U3 | Adopted flat kind discriminator in all six Actions and fixtures. |
| U4 | Unprovided model Ref raises ContractError with invalid_input; availability/permission failures belong to hosts. |
| U5 | Compose permits text/plain and text/markdown, matching C08. |
| U6 | All structural Ref kinds remain available in verify; saved artifact identity, kind and provenance are later VER obligations. |
| U7 | No invented issue-number positivity, nonempty content, duplicate-ID prohibition or semantic quality rule. IDs alone are nonempty opaque strings, without trimming. Repository/path/ref/capability/content strings may be empty. |
| U8 | Absent lookup source_refs differs from []; explicit null is invalid. |
| U9 | No grant expansion, resource/scope authorization, reference availability, revision/epoch/state fencing or ownership proof is inferred from a parsed value. Later hosts enforce them. |
| U10 | Python's configured integer conversion digit limit applies to raw and host-created integers. Excessive nesting/cycles and conversion overflow become bounded invalid_input; no global interpreter limit changes. |

DraftBrief rejects formal condition IDs; Brief requires them. Neither parser mints
IDs. Conditions must be nonempty. All limit fields are mandatory nonnegative exact
integers; zero is preserved as exhausted, never unlimited. Result.ok is exact bool;
success contains only ok/value, failure only ok/error with exact code/message/refs.
Unknown/missing keys, strict type violations (including subclasses/bool as int),
invalid enum members, nonfinite/non-JSON values, invalid UTF-8 and duplicate raw
JSON keys at any depth are rejected.

The design's `raise ... from None` claim was corrected according to SOL's
reproduction: caught exceptions are released before the public error is raised
outside the handler. Tests verify no decoder exception in `__cause__` or
`__context__`, no raw input in error attributes/message, and bounded message length.
ContractError has fixed code invalid_input, root path `$` and a fixed-vocabulary
reason; root-only paths deliberately avoid accumulating attacker-controlled keys
or unbounded paths. As with ordinary Python APIs, callers should log the bounded
error message, not capture arbitrary caller traceback locals as a payload.

No unresolved contradiction blocks this pure scope. U1/U2/U6/U7/U9 retain the
explicit downstream host obligations above; they are not certified by this parser.

## Verification and defect record

Command:

```sh
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_contracts_v5.py -v
```

The targeted suite contains 15 unittest methods, 119 shared synthetic fixture
cases and 3 runnable doctest examples. Fixture cases label acceptance/rejection,
contract IDs and model allowed refs. Coverage includes WorkRef boundaries; all
six Ref kinds, all eight Result errors and all six Actions; C03/CT-24 draft/formal
separation; C12/CT-12 source membership; C15/CT-17/29 zero/negative budgets; nested
shape failures, duplicate raw keys and UTF-8/nonfinite handling. Accepted values
are compared recursively with exact types and floating sign, then round-tripped.
Focused tests cover immutability/copy isolation, numeric equality, missing vs empty
lookup refs, required model-boundary arguments, direct constructors, closed keys,
raw/Python non-JSON input, depth/cycles/integer limits and exception sanitization.
These CT labels identify parser coverage, not service-level CT completion.

During the initial targeted run, the tuple negative test failed: top-level
`dumps((1,))` was accepted. Cause: dumps reused the typed-value tuple conversion
before validating plain JSON. Correction: serialization converts only supported
contract objects at the public boundary; arbitrary input must pass strict JSON
validation first. The same focused regression now passes. Next serialization
change must preserve both accepted typed tuple-backed fields and rejected plain
Python tuples/subclasses. This is a local boundary fix, not a new approval gate.
Initial failing evidence: `/private/tmp/pal-int00-astra-targeted-initial.txt`.
Final targeted evidence: `/private/tmp/pal-int00-astra-targeted.txt` (PASS).
SOL retains/integrates the logs as appropriate; temporary logs are not permanent
repository evidence or independent review.

Full regression, independent exact-commit review and SOL's consumer integration
check remain pending outside this implementation owner's targeted run. C01–C15
services, Operation ledger (EXE01), existing five-helper integration, persistence
and control races (CT-04/07/08/25 and others), E2E-01–09, actual provider/connector
calls, service activation and human-value evaluation are **NOT_RUN**. No product,
v5-wide, CO-task-verification or independent-review completion is claimed.
