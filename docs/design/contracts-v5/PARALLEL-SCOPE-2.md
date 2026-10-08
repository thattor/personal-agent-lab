# Independent preparation slice 2

SOL owns interfaces, integration and canonical records. The first two-task batch
was a deliberately small runtime pilot, not a discovered two-task ceiling. No
third concurrent run was attempted or rejected. Its third task was a milestone
review dependent on the integrated source. The owner's subsequent question is in
PAL人間判断 turn01a11d9c-c641-7fd1-8a66-5fcca4a9b044. Continue authorized independent
work and test three real independent modules rather than fabricate more jobs.

Shared binding: PAL-v5-common-wire INT00/1; C07/C08/C09 of PAL-contracts-v5.
These local byte-processing APIs are settled below before parallel dispatch.
They are preparation components with no I/O, DB, model calls, IDs, Ref/Result/Action
implementation, new capability activation or runtime integration. INT00's four
files remain owned by the unknown original task; do not duplicate them.
Every task receives an exact committed base. Only declared files are writable;
CO owns its separate workspace. Return files, tests, findings and remaining gaps.
Use stdlib only. Errors have fixed bounded messages and no retained caught raw
exception. These values are not grants, receipts or saved verification evidence.

Each task has three steps: Opus design (assess the exact small boundary), isolated
implementation, separate Opus review. Keep plan instructions below1000 bytes by
referencing this scope. Do not change the settled API or claim a service contract
passed; flag a concrete contradiction rather than silently invent another wire.

## D — EXE02-file/1, SWE-2 High implementation

Write only pal/github_file_payload_v5.py and tests/test_github_file_payload_v5.py.
Public decode_file(payload:bytes, *, max_bytes=1048576) -> frozen DecodedFile
with content:str, data:bytes, byte_count:int, blob_sha:str.
FilePayloadError exposes code invalid_input or limit and a fixed message.

max_bytes is exact int,1..1048576; bool/wrong type/<=0 -> invalid_input;
>hard maximum -> limit. payload must have exact bytes type; raw length above
max_bytes -> limit. Strict UTF-8 JSON object: reject duplicate keys, NaN/Infinity,
invalid encoding and malformed JSON. Extra provider fields are allowed. Require
type='file', encoding='base64', content:exact str, size:exact nonnegative int,
sha:exact lowercase40-hex str. Reject directory arrays, explicit target or
submodule_git_url fields, other type/encoding, bad size/type/hash. Size greater
than max_bytes -> limit. Strip only CR/LF from Base64, then validate canonical
standard Base64 including padding (no spaces/tabs/other alphabet/noncanonical
pad bits). Decode bytes, enforce max_bytes, require declared size equals actual
bytes, and decode strict UTF-8 preserving empty text, Unicode and line endings.

blob_sha is provider metadata, not a commit SHA or verified provenance. No Git
object hash checking, repository lookup, download_url following or actual read.
The host later owns pinned commit/path provenance, grant, observation time and
operation receipt. Raw transport and decoded limits are both enforced; Base64
overhead means not every1MiB decoded file fits a1MiB JSON response budget.

Primary source: https://docs.github.com/en/rest/repos/contents#get-repository-content
GitHub describes a Base64 file object, directory arrays, symlink/submodule cases
and limited large-file media behavior. Initial helper supports only the specified
small text file object; future executor must handle other responses explicitly.
Fixtures must be synthetic, not copied private repository/file responses.

Cases: known wrapped Base64/UTF-8 text, empty file, exact bytes/metadata, CRLF/
normalization preservation; array/type/encoding rejection, submodule/target;
duplicate keys/nonfinite/raw UTF-8; invalid Base64/pad bits/whitespace/size;
raw and decoded bounds, binary non-UTF-8; bounded errors with no decoder context.
Verify unittest discover -s tests -p test_github_file_payload_v5.py -v.

## E — EXE02-bytes/1, SWE-2 High implementation

Write only pal/bounded_payload_v5.py and tests/test_bounded_payload_v5.py.
Public PayloadBuffer(*, max_bytes=1048576), append(chunk:bytes)->None,
getvalue()->bytes and read-only byte_count:int. PayloadLimitError has fixed code
invalid_input or limit and message. Same exact positive int hard maximum as D.
append accepts exact bytes only, including empty. Before retaining or joining,
reject cumulative bytes above max_bytes with limit; rejection leaves the buffer
unchanged. getvalue returns an immutable snapshot; later appends do not change
earlier snapshots. Zero-copy optimization, iterators/callbacks, stream reading,
timeouts, process cleanup and backpressure are out of scope. No second task state
machine, shared state or engine: this is only an in-memory byte accumulator.
The executor later owns reads/termination and feeds chunks while respecting time.

Cases: split multibyte characters preserved exactly as bytes; empty chunks;
1/exactmaximum and excess by1; cumulative overflow after prior accepted chunks;
invalid chunk/type/bool/bounds; rejected append cannot poison subsequent valid
append; immutable snapshots/read-only count; fixed errors without input echo.
Verify unittest discover -s tests -p test_bounded_payload_v5.py -v.

## F — VER01-integrity/1, Opus implementation and separate review

Write only pal/artifact_integrity_v5.py and tests/test_artifact_integrity_v5.py.
Public check_bytes(data, expected_sha256, expected_bytes) -> frozen IntegrityCheck
with status:met|unmet|unknown and reason:fixed str. This checks saved-body integrity
against expected metadata supplied by the host, unlike preparing a new content
value. No Condition/Ref issuance, saved verification, semantic evaluation or
completion. Host must later prove expected metadata came from canonical storage.

Invalid metadata (non-exact str/hash not lowercase64-hex, non-exact int/negative/
>1048576) or non-exact bytes data -> unknown with fixed reason, no exception/raw
echo. Data exceeding1048576 bytes or length/hash mismatch -> unmet. Match -> met.
Zero expected bytes is valid empty content. Compare byte length before hashing;
do not hash an over-limit body. No UTF-8/media/source/ownership judgment: those
belong to other checks; byte integrity alone is not all C09 acceptance.

Cases: known SHA256 vectors/empty body, multibyte byte count, correct body with
wrong expected hash or count, same-length tampering, invalid/bool/subclass metadata,
limit/excess, immutable check and fixed bounded reasons. Verify unittest discover
-s tests -p test_artifact_integrity_v5.py -v.

## Integration and milestone

D/E/F have no dependency on one another during implementation. SOL later connects
synthetic chunked file-response bytes -> bounded buffer -> decoded text -> existing
ART01-content -> integrity check. Include corruption/overflow failure paths. This
is a deterministic local preparation path, not a real GitHub/DB/Goal workflow.
Run targeted tests and the required full unittest suite, inspect exact diffs and
source hashes, and obtain one Opus milestone review of the final combined source.
Only useful work raises parallelism; capacity status and actual call intervals are
reported separately. Common services still await INT00, real CT/E2E/user value unmet.
