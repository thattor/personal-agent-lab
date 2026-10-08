# Independent preparation slice 1

Owner/integration: SOL. Contract binding: PAL-v5-common-wire INT00/1;
local boundary versions EXE02-request/1 and ART01-content/1, based on C07/C08
of PAL-contracts-v5 (2026-10-09). These are unused, pure development components.
No PAL service, external capability, shared DB or v5 service adoption is activated.
The unresolved INT00 task owns its original four files; neither task below may
replace those files or implement its shared WorkRef/Ref/Action/Result types.

Each ordinary CO run receives its exact committed base SHA through --base.
Read only this scope, PAL-contracts-v5.md and pal/__init__.py. Separate CO task
workspaces own disjoint writes. SOL alone edits shared contracts, canonical records,
integration tests and shared DB/schema. Use Python standard library only. Return
all declared file contents, concrete review findings and remaining problems;
CO supplies the diff, verifier log and separate review outcome. A verified CO run
does not complete PAL or the service contract tests.

## A: EXE02-request/1 — SWE implementation, Opus design/review

Create only pal/github_read_request_v5.py and tests/test_github_read_request_v5.py.
First obtain a scoped Opus design review: confirm this pure request constructor
is useful preparation for EXE02, has no new running capability, and leaves EXE01
authority, operation reservation, recovery, response/provenance and actual provider
execution to their owners. SWE implements a small module after that review; its
implementation explanation records its technical choice before the file contents.
Opus reviews the resulting diff in a separate call.

Public API: prepare_read(capability, arguments, *, timeout_seconds=30,
max_bytes=1048576) -> immutable ReadRequest; ReadRequest fields capability, argv,
timeout_seconds, max_bytes. ReadRequestError has bounded code and message.
No subprocess/network calls, credentials, environment reads, filesystem or DB.
Do not issue operation/receipt IDs. An EXE01 host may later pass the request to its
owned process executor; this module is not that executor or an authorization gate.

Only github.issue.read accepts exactly {repository,number}, and github.file.read
accepts exactly {repository,path,ref}. Repository must be exactly
thattor/personal-agent-lab. Issue number is strict positive int (bool is invalid).
File path is a nonempty valid UTF-8 relative POSIX path; reject absolute paths,
empty/dot/dotdot segments, backslashes and C0/DEL controls. Ordinary Unicode,
spaces and shell metacharacters remain literal; do not invent a filename quality
restriction. Ref must be an exact lowercase 40-hex commit SHA for this initial
pure boundary, so a mutable branch cannot masquerade as observed provenance.
Later branch resolution is the host's responsibility before this constructor.

Build fixed argv beginning ('gh','api','--method','GET','--hostname','github.com',
<endpoint>). Issue endpoint repos/thattor/personal-agent-lab/issues/<number>;
file endpoint repos/thattor/personal-agent-lab/contents/<encoded-path>?ref=<sha>.
Percent-encode each path segment, preserve separators; never interpolate shell
code or add arguments derived from unvalidated fields. Exact integer bounds:
1..30 seconds and 1..1048576 response bytes. Invalid types/keys/encoding ->
invalid_input; another repository -> denied; bounds above the hard maxima ->
limit. Errors must not echo raw inputs or retain caught exceptions with raw data.

Meaningful cases: exact issue argv; literal Unicode/space/$/;/#/? file path
encoding; immutable argv; wrong capability/keys/type/bool; other repository;
path escape/control/surrogate; malformed/mutable commit; both bounds, zero and
negative values. No test requires shell execution or a real GitHub connection.
Verify: python -E -s -B -m unittest discover -s tests
-p test_github_read_request_v5.py -v. Return only these two files; do not create
a substitute common-contract module, full connector or extra framework.

## B: ART01-content/1 — Opus implementation, separate Opus review

Create only pal/artifact_content_v5.py and tests/test_artifact_content_v5.py.
This small pure helper needs no persistence/concurrency strategy. Use two
sequential steps: implementation then independent review in a fresh call.

Public API: prepare_content(content, media_type) -> immutable ArtifactContent
with content:str, media_type:str, data:bytes, sha256:str and byte_count:int.
Only strict str inputs and media types text/plain or text/markdown. Preserve
content exactly (including empty strings, line endings and Unicode normalization).
Encode valid UTF-8, limit encoded bytes to 1048576 inclusive, hash exactly those
bytes. ArtifactContentError exposes bounded code/message: invalid_input for wrong
types/media/encoding and limit for excess bytes. Do not retain raw decoder context.
No Ref, key/ID minting, source checking, DB, filesystem, provider or network call.
ART01 later owns transactional WorkRef/source availability, immutable saved IDs,
idempotency and C11 readback; this value is not a receipt or completion evidence.

Meaningful cases: known byte/hash result; multi-byte UTF-8 limits; empty/CRLF and
normalization preservation; invalid type/media/surrogate; exact maximum and excess;
immutability; bounded errors with no raw exception context. Avoid a schema engine
or mirroring private methods. Verify: python -E -s -B -m unittest discover -s tests
-p test_artifact_content_v5.py -v. Return only the two declared files.

## Integration and finish

After exact diff inspection and separate reviews, SOL combines a synthetic bounded
GitHub request with mock read text and prepared artifact bytes, checking their
contract-facing values. No external execution or persisted completion is claimed.
Run targeted tests and the required full unittest suite before commit/push.
CT03/04/07/08/25, E2E01–09, real provider reads, reference availability and user value
remain NOT_RUN. These tasks are independent of the unknown INT00 implementation;
common-service wiring waits for that unresolved work rather than duplicating it.
