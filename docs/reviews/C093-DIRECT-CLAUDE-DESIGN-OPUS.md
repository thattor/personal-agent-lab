# C093 — PRI02-CLAUDE-DIRECT/1 design review (Opus 5.5, independent)

Verdict: **REFINE**

Scope reviewed: `docs/design/contracts-v5/PRI02-CLAUDE-DIRECT-SCOPE.md` at BASE 3f69337, read with `PAL-contracts-v5.md`, `pal/native_call_v5.py` and `pal/native_expert_runner_v5.py` as context. This is a document design review only. It is not source verification, a test run, a qualification or a native call, and it grants no permission. Root owns the disposition and the exact freeze.

## Basis for the verdict

The design is coherent and contains no method-level contradiction, so STOP is not warranted. These parts are aligned:

- The closed two-pair profile keeps the Devin default byte-identical, because `_body()` already serialises `id` through the property.
- The original Devin gates and the `NativeDevinText` refusal are preserved.
- The design separates advertised agents, skills and plugins from the zero-valued `subagent_stats`, tools and permission counters.
- It accepts multiple assistant frames that share `request_id` and `message.id`.
- `prompt_sha256` is correctly limited to proving local stdin submission. Owned EOF and wait are correctly limited to proving local CLI completion.
- Fixed tests come before source, and the scope makes no conversation or prose grading claim.

ALIGNED is not warranted either. The items marked blocks-source leave real ambiguity in the frozen boundary. Some of these gaps would convert into permanent lane holds or budget-burning TSK unknowns. The ending, pin and capture key sets are fixed as exact, so the gaps must be closed before source is written.

## Concrete minimum corrections

### S1 — Pre-entry refusal shape and lane ordering (blocks-source)

The current behaviour creates a cascade:

- `NativeExpertRunner._native_dispatch` marks the TSK call unknown for any exception raised from `invoke`. Unknown means no refund and no reinvoke.
- The scope says only that post-entry uncertainty raises. It does not define refusals that happen before the hook runs: lane busy, request schema or bounds failure, pin or version drift, or the executable check.
- Once one unknown holds `active.json`, every later Primary or Expert call would therefore burn a model reservation and create a new unknown.

The scope should fix the following order: validate request and profile → take a non-blocking `flock` → check that no `active.json` exists and recheck the executable pin → write and fsync `active.json`, the request, the pin and the attempt journal → call `on_enter` once → `Popen`.

It should also state two rules:

- Any refusal before `active.json` is written and before `on_enter` is called returns a genuine `NativeNeverEntered` with a fixed safe `evidence_ref` format. An example format is `pal-claude-refusal:` + a hash of the fixed reason and request digest.
- `flock` is held only to check, write and release the active record. It is never held across the child, and a busy lane never blocks.

Add fixed tests for busy-lane refusal and drift refusal. They must show `NativeNeverEntered`, no hook call and no TSK unknown.

### S2 — Closed post-entry outcome classification and crash window (blocks-source)

The phrase 'release active only after a known complete ending' does not say whether an exit after full EOF with a nonzero code, or a protocol or parser refusal after exit 0, counts as known. The scope should state a closed rule:

- **Release** happens only after an accepted ending has been validated and durably saved.
- **Hold** applies to every other outcome after `active.json` exists, with a finite reason code and no retry. This includes:
  - hook failure, or spawn failure after the hook ran;
  - partial stdin;
  - a timeout or cap hit;
  - full EOF with a nonzero or non-int exit;
  - any frame, model or output refusal after exit 0;
  - failure to save the ending.

Define the crash window between saving the ending and releasing the lane. On restart, the provider may revalidate the saved ending against the journal and then release the lane. In this scope that ending is never adopted into TSK, so TSK recovery stays unknown with no refund. Add one fixed test for this window.

### S3 — Canonical request bytes (blocks-source)

The scope does not name the encoder behind 'canonical whole request' or the stdin bytes. It should state all of the following:

- The encoder is the same one that produces the TSK-admitted `request_sha256`. If that is the `_json_snapshot` form, say so: sorted keys, compact separators, `ensure_ascii=False`, `allow_nan=False`, UTF-8.
- No trailing LF is sent.
- The 65536-byte bound applies to exactly those bytes.
- `prompt_sha256 == request_sha256 ==` the SHA-256 of the bytes actually written to stdin.

Without this, Primary or TSK and the provider can disagree, and every real call fails after entry.

### S4 — Output aggregate rule (blocks-source)

State these rules:

- Text blocks from all assistant frames are concatenated in frame-then-block order with no separator.
- `chunks` is the number of text blocks.
- `utf8_bytes` and `output_sha256` cover only that aggregate. Thinking and signature data are excluded from the count, the bytes and the aggregate.
- `result` is compared byte-for-byte with that aggregate.

The current wording does not fix the separator or the chunk definition, and the fixed tests need both.

### S5 — argv binding is unverifiable as written (blocks-source)

`argv_sha256` includes a resolved executable path and a fresh session UUID, and `validate_claude_ending` receives no expected argv. As a result, the ending cannot show that the fixed argv was used. Apply one of these two corrections:

- **Option (a):** hash a canonical argv list where the executable element is a fixed placeholder. The executable is already bound by `executable_sha256` in the pin. `validate_claude_ending` then recomputes `argv_sha256` from the module's fixed template and the ending's `session_id`.
- **Option (b):** state explicitly that `argv_sha256` is a local record with no validation value.

(a) is recommended because it is small and makes the closed-flag claim checkable from the ending alone.

### S6 — Executable lookup and recheck at entry (blocks-source)

'Official lookup' is the seam that tests patch, so its contract must be defined:

- Resolve the realpath once. A launcher symlink may be part of the official install, so 'reject symlink' must apply to source origins, not blindly to the launcher.
- Require the resolved file's version to equal 2.1.291 and its SHA-256 to equal the pin's `executable_sha256`.
- Spawn that hashed realpath. Never spawn through a PATH lookup.
- Repeat this check under the lane lock immediately before writing the journal (see S1). The preflight result alone is not entry authority.
- Run the `--version` and `auth status --json` preflight calls with the same restricted env and a fresh cwd. Give them a fixed small timeout and output cap. Discard account values before any record is made.

### S7 — Qualification pin source coverage is incomplete (blocks-source)

The pin's `source_hashes` set is exact, but it omits code that determines the Claude path's behaviour:

- `pal/mock_runner_v5.py`, which provides `_RunnerCore`, the base class of `NativeExpertRunner`.
- `pal/contracts_v5.py`, which provides `parse_model_action`, `Result` and `dumps`.
- `pal/native_text_v5.py`, which `native_call_v5.py` imports.

On this path, a change to any of these files would leave the pin unchanged. Fix one of the following before source:

- **Option (a):** fix the list as the first-party import closure of the Claude invocation path at the frozen commit, with at least the three files above.
- **Option (b):** state that the pin is partial and that Root binds the integration commit separately.

### S8 — attempt_ref derivation and provider surface (blocks-source)

Define how the Claude provider fills the run_id, job_id and attempt_id triple, so that duplicate-call and restart tests are deterministic. One option is run_id = a fixed lane label, job_id = the hashed call-directory name, and attempt_id = the session UUID. The triple must map one-to-one to the session UUID and the call.

Also state that `NativeClaudeText` exposes an immutable `.profile` that is the `NativeProfile` instance. `NativeExpertRunner` refuses providers that lack `profile`, `preflight` or `invoke`, and compares profiles on every slice.

## Material unresolved assurance

### L1 — 60 s deadline versus high effort (blocks-later-real-entry)

`PAL-contracts-v5.md` §10 records one Opus 5.5 call at 90.96 s. A timeout is a post-entry hold with no clearance path in this scope, so a real attempt could permanently disable the lane on its first try. Before any real entry, Root must justify a finite deadline for the bounded request and output sizes, or reduce the requested effort. Fixing the chosen constant at source freeze avoids a second freeze.

### L2 — No additional cost is detected, not prevented (blocks-later-real-entry)

The current checks only detect cost after the fact:

- The `rate_limit_event` check refuses overage only after the call has happened.
- An absent event is permitted, so it proves nothing.
- The 17-key ending does not record whether a rate-limit observation occurred.
- Preflight accepts team and enterprise subscriptions, beyond the observed pro account.

Later entry needs four things:

- an operator-observed record that extra or overage usage is disabled on the account;
- a subscription pin narrowed to the observed type;
- a statement that the source's checks are post-hoc detection;
- either a decision now to record the rate-limit observation in the ending or receipt, which would make this item blocks-source, or acceptance that it stays private journal data.

### L3 — Unobserved real-shape risks convert to held lanes after a possibly billed call (blocks-later-real-entry)

These behaviours have not been observed:

- whether `message.model` exactly equals `claude-opus-5-5` rather than a suffixed ID;
- whether `modelUsage` is a singleton under auxiliary traffic;
- whether `result` equals the multi-block text aggregate;
- whether redacted-thinking blocks or unlisted system subtypes appear;
- how large frames get with high-effort thinking against the 262144-byte frame limit and the 1 MiB stdout limit;
- whether `--safe-mode` and `--permission-prompts none` are accepted.

The later freeze must cite retained original 2.1.291 observations as provenance for each 'as observed' constant. Fixture consistency is not that evidence.

### L4 — Held-lane and TSK-unknown disposition, and a finite attempt count (blocks-later-real-entry)

This scope never clears an unknown, which is correct for source. The later distinct design and operator freeze must still define two things:

- the finite total number of real attempts;
- who disposes of a held `active.json` and the matching TSK unknown, and how. Otherwise one unknown ends the route.

This must not become an unknown retry or release by rotating the root.

### L5 — Evidence kind is self-declared (blocks-later-real-entry)

`evidence_kind` is part of the profile, and validation does not distinguish fixture evidence from `native_profile` evidence. Later entry must define who may construct a `native_profile` Claude profile. Its evidence may come only from the pinned executable and real run. Fixture-kind evidence must never be presented as qualification or as Devin evidence.

## Non-blocking clarifications

### N1 — Independent contexts (non-blocking)

Name the contexts for the fixed-test author, the wrapper author and the core/consumer reviewer, and require them to be pairwise distinct. The scope's two 'Separate Sol' roles currently read as possibly the same context.

### N2 — Mixed-profile refusal tests (non-blocking)

The ending dispatch already rejects mismatches, but make the profile-laundering tests explicit:

- a Claude cessation validated against a Devin profile, and the reverse;
- a mismatch between `cessation.profile_id`, `model_id` and the `evidence_ref` prefix.

The shared version `NATIVE-CALL01/1` must not let evidence from one profile pass as the other.

### N3 — Scope size is proportionate (non-blocking)

The closed schemas are appropriately strict for a pinned CLI version. No overdesign removal is required. The cost of that strictness is captured in L3, not as a reason to loosen the schemas.

## Blocking summary

- **Blocks source:** S1, S2, S3, S4, S5, S6, S7, S8.
- **Blocks later real entry:** L1, L2, L3, L4, L5. L2 becomes blocks-source if Root chooses to record the rate-limit observation in the ending.
- **Non-blocking:** N1, N2, N3.
