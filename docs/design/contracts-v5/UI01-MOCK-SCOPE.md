# UI01/1 — fresh current-v5 local mock connection

Root frozen source scope, 2026-10-10. Base fff19cc022c6845fdfde4236cbda349d1513d82d.
Current owners and their adopted scopes/PAL-contracts-v5 govern behavior. Source
work is independent of modern model diagnostics. No old implementation reuse or
backwards compatibility, native model call, existing DB adoption, deployment,
OAuth/account/credentials/billing/service purchase, CO/runtime/state edit.

## Small usable local slice

One process,127.0.0.1 only,default ephemeral port and new disposable SQLite DB;
one user session per application. Mock-only status is visible. No native launch
option or automatic provider fallback. The UI accepts a turn, displays pending/
committed/failed/interrupted, shows current work/question/result, supports bound
answer and structured pause/resume/cancel/source-reference stop, and reads saved
results using current public owners. Model decisions are explicitly injected mock
fixtures. Default fixture reply must label itself as a test and must not pretend
to understand arbitrary input; include a documented deterministic local example
create->ask->answer->compose->structural VER/complete->readback. Prototype routing
is not natural language capability or authentic usefulness proof.

## Public application and HTTP surface

New files only: pal/http_v5.py, pal/web_v5/index.html, app.js, style.css,
scripts/demo_http_v5.py, tests/test_http_v5.py and independent
tests/test_http_v5_independent.py. No current owner source/test changes.
Application class LocalMockApp(primary_invoke=None, expert_invoke=None) owns a
fresh TemporaryDirectory/DB/MockHostSession, single session_id and bounded worker.
Constructor opens the fresh managed host to ready. None selects explicit
documented built-in fixtures; injection stays mock and refuses bound NativeProfile
invoke as existing owners do. Expose session_id; support context manager returning
self. close(timeout=5.0) returns bool: true only after worker/connections/guard
cleanup, false leaves held guard/DB and status. wait_idle(timeout=5.0) returns bool
without executing/pumping a model. create_server(app, port=0) returns a stdlib
ThreadingHTTPServer bound127.0.0.1; it never starts on import. Existing public
owners perform actual memory/task/artifact/verification/turn persistence; no
duplicate application state machine or SQL status edits.

Exact APIs: POST /api/turns {client_key,text} supplies application session_id to
PrimaryHost.submit; GET /api/turns?turn_id=... calls get_turn. GET /api/works calls
TaskStore.list_candidates({session_id,limit:20}); GET /api/inspection calls
inspect_session with EventReader/tasks/HostReader. POST /api/controls exact
{key,work_ref,command} forwards TaskStore.control; POST /api/source-stop exact
{key,source_ref} calls MemoryStore.stop_reference(session_id=app.session_id).
GET /api/status returns mode='mock',native_available=false,session_id and current
worker status; no private path/PID/credential. No caller-selected session/DB/repo,
GET mutation, arbitrary-file route or unsupported method. HTTP responses use owner
Result JSON for owner operations; status has closed primitive values. Errors are
bounded generic Results, not raw exceptions/paths/SQL. Return clear4xx transport
validation/404 route errors; refused owner Results stay actual owner errors.

submit returns the stored receipt promptly and enqueues only a new pending turn.
An owned worker runs PrimaryHost.run_turn then at most one MockRunner.run_once
for that task progression. Same-key replay/conflict never starts a second inference.
No unbounded automatic inference loop/retry. Control/source-stop uses a separate
connection so a blocked inference does not block those operations. Each thread
creates/uses/closes its own SQLite connection and owners; one shared lifetime
MockHostSession, no check_same_thread=False. DB transactions/locks never span
model callback waits. Actual owner currentness/source gates fence late output.
At initialization register/recover/finish_startup using current managed APIs.
No new-epoch reinference of old unknown; only fresh DB supported by this scope.

Owned queue max16; refusal leaves clear stored pending state with no claimed run.
Shutdown stops new enqueue, signals built-in worker, waits owned threads and closes
connections before releasing guard/deleting disposable data. With a caller-injected
unresponsive fixture, report incomplete close/hold and keep guard/DB; never delete
while worker runs or claim forced cancellation. No unrelated process operation.
Expose deterministic worker wait/idle helper for bounded tests, not model pumping.

## Bounded HTTP and UI

Content-Type application/json for POST, exact Content-Length required (no Transfer-
Encoding), body <=65536 bytes, strict UTF8/JSON, reject duplicate keys/NaN/infinity,
closed input keys. Text<=32768 UTF8 bytes; IDs/keys nonempty UTF8<=512; owner parsers
validate WorkRef/Ref/command. Do not accept bool as integer port/revision. Bound
query/value size and socket read timeout; malformed/oversized requests change no
owner state and invoke no model. Validate exact127.0.0.1:<boundport> Host; reject
Origin unless absent or exact same server origin. No CORS/OPTIONS allowance. This
combined JSON-only/Host/Origin boundary must have cross-origin rejection tests.

Serve only the three fixed static files. Use textContent/createElement for all
user/model/artifact/error content. No eval/innerHTML from data, inline event attrs,
external scripts/fonts/assets, or filesystem/log secrets. Display mock notice,
questions, pending state, actual owner errors and saved results in plain Japanese;
implementation details only where a provenance/availability choice matters.
Same client_key persists during a retry. Refresh reads state and does not submit
or run a model. Structured controls use currently displayed WorkRef. The local
entry script prints the actual URL, owns serve_forever and finally closes the
server/app on interrupt. No background/autostart or persistent existing DB.

## Done and review

Source author Native Sol isolated branch; independent tests/review by Astra/other
Sol context as available. Independent meaningful HTTP tests include fresh startup,
submit replay/conflict/polling, actual saved readback, question/answer bound to
same work, in-flight pause/cancel/source-stop plus late-result fencing, limits/
UTF8/duplicate JSON/closed keys/cross-origin/static traversal refusal, owned clean
shutdown and honest native unavailable. Root connects small example early and
checks rendered UI through available browser only after local HTTP passes.
Use Python stdlib only, no package install. Return source commit/diff/hash/tests
and unresolved limits; Root final suite and independent review required before
integration/publication. UI mock completion is not native/model/semantic/human
usefulness/whole-goal completion. Opus milestone design review remains separate.
