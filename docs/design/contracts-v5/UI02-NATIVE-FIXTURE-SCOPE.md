# UI02-NATIVE-FIXTURE/1 — explicit current native-owner HTTP connection

Root freezes a source/fixture-only slice under D067. It connects current native
Primary, Expert, controls and saved readback through the existing loopback HTTP
surface. Mock remains the default. It authorizes no genuine provider call,
qualification, current C094 lane operation, new attempt root, auth/service/fee,
old DB migration or actual usefulness judgment. No prose/intelligence grading.

## Trusted application boundary

Add pal/native_http_v5.py with this exact keyword-only interface:

```python
LocalNativeApp(*, provider, request_scope: Grant, host_limits: Limits,
               session_id: str | None = None)
```

The provider is a non-callable object with concrete NativeProfile and callable
preflight/invoke. For this fixture-only slice require its explicit
fixture_only attribute to be exactly True; official real-provider wrappers lack
that attribute and are rejected before any preflight/invoke. This marker declares
the trusted fixture caller's scope; it is not a transport attestation. Snapshot
the profile and reject changed profile/fixture marker before progression. Both
owners use that same provider object. Do not create a callback/native downgrade.

Require concrete Grant/Limits, empty capability tuple and max_operations0. Step
and model-call limits are integers0..20 in both request scope and host limits.
The constructor alone fixes them and the session identifier; validate supplied
session strings as nonempty UTF8 identifiers up to512 bytes. No HTTP parameter
may choose profile, executable, path, attempt root, grant or qualification.

Create a fresh owned0700 directory and private SQLite DB; do not accept an old DB
path. Retain a host-only read-only database_path property for local fixture
retention checks; never expose that path through HTTP.
Compose existing public TaskStore/MemoryStore/ArtifactStore/VerificationStore
and MockHostSession lifetime guard. Guard naming does not replace native owners.
Register host, construct NativePrimaryHost with the fixed provider/scope, call
recover_turns, then finish_startup. No constructor/poll/read preflight or invoke.
Startup failure/held response prevents progression. No SQL from the HTTP layer to
read or repair native call state; existing public owners remain the only writers.
If a changed profile/marker prevents native-host construction, retain the core
public owners for controls/source-stop/works/inspection/status. The owners tuple
may have host=None in that invalid configuration; a turn read then fails closed
with pathless UNAVAILABLE. Do not construct a proxy/mock provider or block saved
ART/core reads merely because a native host cannot be rebuilt.

## HTTP and worker behavior

Reuse UI01/2 endpoints and app interface: session_id, owners(), submit(), status(),
wait_idle(), close(), plus its bounded reservation/enqueue interface used by
controls. Keep request/idempotency/host-origin/size/security-header contracts.
Owners use separate SQLite connections; never hold the app mutex or DB transaction
across provider callbacks. No external file operation or send is in this scope.

One accepted pending turn schedules run_turn once. Inspect the returned public
turn status: only committed permits at most one NativeExpertRunner.execute_next
slice. Result.ok/HTTP200/queue-empty alone grants no Expert entry. Failed,
interrupted, pending, held or unavailable/unrecognized outcomes do not advance.
Poll/read/pause/cancel/source-stop schedule no entry. Explicit successful resume
or structured answer may schedule one Expert slice, preserving UI01/2 idempotency.

Primary held or unavailable/unrecognized owner response latches application held.
Expert UNAVAILABLE or unexpected/exceptional owner response likewise latches held,
because public owner information cannot establish a safe ending. Known DENIED or
INVALID_INPUT is not converted into a returned action. No further progression
while held, including already queued items; pending durable turns remain saved.
Controls/source-stop/read remain available with separate connections. Never infer
an ending, release/refund an unknown call, or clear held from queue emptiness.

Bound queue/admissions to16. Local worker quiescence may satisfy wait_idle, while
status remains held. close is bounded; active worker/handlers/admissions retain
the DB and guard and return False. After local activity ends it may close the
guard but always retain this native fixture DB/directory, including UNKNOWN.
Closing a guard is not provider cessation or native lane release. No cleanup of
old cases or automatic reopening/progression is included.

status is a closed seven-key object:

```json
{"mode":"native_fixture","native_available":false,"qualification":"NOT_RUN",
 "profile_id":"declared fixture profile","model_id":"declared fixture model",
 "session_id":"fixed session","worker_status":"idle|running|held|closing|closed"}
```

No path/hash/account/raw provider output is returned. Preserve existing mock
status and native-callback rejection. Minimal web_v5/index.html/app.js changes
show mock versus native fixture explicitly; native_available:false and NOT_RUN
must never be displayed as a qualified real model. Render content literally.
Common HTTP errors may use a generic pathless local-request message.

## Assignment, inputs and fixed completion

Baseline Root67c93db is C095's integrated usage correction with independent Sol
APPROVE; Root full is running separately. Current source APIs are
NativePrimaryHost/NativeExpertRunner, UI01/2, PAL-contracts-v5 and native typed
fixture endings. Input request/output bodies remain synthetic.

Astra first owns only new tests/test_native_http_v5.py and, if necessary, a new
tests/native_http_fixtures_v5.py. Freeze10 methods: config/type/marker/profile
refusal; startup order/no entry; submit/replay/conflict; committed Primary/Expert
same-provider sequence; noncommitted no Expert; Primary/Expert UNKNOWN hold and
DB retention; concurrent controls/source-stop during callback; late-output fence;
ask/answer/ART/fresh VER/user_view; queue16/poll/pathless status/bounded close.
Import fixture TestCase modules by module name, without duplicating their test
classes into discovery. All current test bytes/expectations remain unchanged.

Root freezes fixed commit efd6c0134505cd69bee845876e79af6620d2fb62 on67c93db:
tests/test_native_http_v5.py SHA256
5c62bc57a28605388d729a4a11ebf551798e8012605ad900db9439f95b345662;
tests/native_http_fixtures_v5.py SHA256
a5c1022c9fd70c412d53d7063b29c3927a83a83cdae939222fd2f1bd8c3c3322.
AST has10 methods, without duplicate imported cases. Original RED ran10 tests
with10 missing-module errors/exit1; log SHA256
fc2ab225341a1462507e2c13441caada95149fd3f41bd84dc940803d6610890b.
Root read the exact test/fixture bodies and their original API dependencies.
The missing-module RED is not an executed HTTP/assertion verdict; fixed bodies
must be exercised after source exists. The standalone typed fixture is validated
against the current12-field schema, with no CLI. Existing test bytes are unchanged.

After Root freezes the exact fixed tests, separate Sol owns only new
pal/native_http_v5.py and necessary pal/http_v5.py, pal/web_v5/index.html,
pal/web_v5/app.js changes. Preserve mock behavior and all underlying owner/wrapper
bytes. Separate Astra reviews that Sol source; disclose its fixed-test authorship.
Root alone updates shared contracts/canon, integrates and verifies the full suite
and an owned disposable native-fixture browser path before acceptance. Authors
return exact commits/diff/file hashes, actual command/count/exit/log hashes and
remaining issues. Fixed local endings are not actual qualification.

HTTP/UI files are outside the existing17-file transport closure. Future whole-flow
operator scope must bind their exact bytes, admission/queue settings and authentic
provider qualification separately; this slice adds no qualified launch command.
