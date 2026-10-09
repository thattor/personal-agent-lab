# READ01 fixed public acceptance inputs

Base `468a3a4da647e5f1717040a70d7a82db581cf9f5`; frozen READ01-SCOPE Root
contract governs these tests. Test author owns only the two new modules and this
note, not VER/reader code or canonical records. Different context reviews the
implementation; Root owns actual MEM/TSK/ART/VER/C14 demo/connection evidence.

## VER read input

`test_verification_read_v5.py`:10 methods. Uses existing
`tests/test_verification_v5.py` **as an explicit dependency** by importing its
fixture module (not inheriting its tests). Include that file and existing
`pal/contracts_v5.py` and `pal/verification_v5.py` in the code owner's inputs.
Each constructed read store wraps callbacks to assert exact saved WorkRef request,
status purpose, active same connection, artifact request identity and record gate.

Assertions cover the exact historical six-key JSON projection, Unicode/UTF-8
SHA-256, ordered public ART hash/bytes and exclusion of private/time/current fields;
all three purposes; current usable with unknown checks; epoch/set/source
invalidation and unchanged historical content/hash; changed read-at time; strict
request/Ref/purpose; missing identity and uncertain/malformed owner errors;
default UTC and invalid clocks; mutating/committing/raising clock and interruptions;
ordinary read total_changes/durable dump unchanged. Injected rollback mutations
correctly increase total_changes while durable dump stays unchanged. A trusted
COMMIT's persistent mutation is explicitly observed, never claimed rolled back.

The reopen variant copies the saved database into a **second in-memory SQLite
connection** with backup and reconstructs the owner. No file/disk reopen is claimed.
Private schema corruption and actual disk/connection ordering remain Root probes;
the corrupt-owner fixture returns malformed public ART evidence instead of choosing
VER storage columns. No conditional skip or new implementation stub is present.

Root read-specific disposition: only absence of the requested verification Ref
returns not_found. Context(status) not_found maps to unavailable in VER.read,
because the current WorkRef status cannot be established. Existing typed
get_verification behavior remains unchanged; this does not invent history.

## Host/consumer input

`test_read_consumer_v5.py`:11 methods, standalone explicit public owner doubles.
No fixture dependency beyond `pal/contracts_v5.py`. Its strict doubles assert
closed C02 `{goal_id,revision}`, C14 `{session_id,after_event_id?}`, and C11 `{ref}`
with the explicit purpose keyword. Only user_view is allowed throughout consumer
calls. Host dispatcher tests separately prove exact propagation of every valid
purpose to each owner.

Assertions cover recognized/unsupported/malformed kinds without fallback, owner
exception/non-Result/malformed Result and BaseException propagation; advancing
unselected pages, initial cursor, ordered multi-work result refs and separate
states; exact notice+Goal/revision+dependency intersection for source-stopped cause;
unknown cause stays not current; per-work/per-ref errors and missing WorkRef visible;
bounded max_pages with truncation, malformed/stalled/repeated cursor rejection;
mock/structural/read at labels and fixed Condition/check content. Host page limits
must reject out-of-bounds values before event access; the freeze does not assign
a Result-versus-ValueError convention to that trusted host argument, so either
explicit invalid_input or ValueError is accepted there only.

## Author evidence and limits

Both AST parsers and `git diff --check` PASS. Commands:

```
/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_verification_read_v5.py -v
/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_read_consumer_v5.py -v
```

Current RED: VER10/0.007s/exit1, all10 constructor errors for absent clock argument;
consumer11/0.001s/exit1, all11 setUp import errors for absent pal.host_read_v5.
Logs `/private/tmp/pal-verification-read-tests-red.log` and
`/private/tmp/pal-read-consumer-tests-red.log`. VER saved fixture setup already
runs the existing public verify; new read behavior and consumer bodies are NOT_RUN.
No full regression is claimed. Explicit sys.path supports isolated discovery.
Only in-memory databases and trusted synthetic callbacks are exercised; these
acceptance inputs are not proof of actual source stop, product/UI activation,
semantic evaluation, cross-owner atomic snapshots or completion authority.
