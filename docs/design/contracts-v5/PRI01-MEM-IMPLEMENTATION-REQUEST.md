# PRI01-MEM/1 implementation assignment

Implement only pal/memory_v5.py against frozen PRI01-MEM-SCOPE and independent
tests/test_memory_primary_v5.py (13 methods). Existing methods/schema keep their
behavior. Add list_recent closed same-session usable metadata and original
C05.stop_reference receipt lookup; validate stored closed input/result and original
record binding without reapplying stop, callbacks, writes or source/body-use grant.
Read methods preserve caller transactions and propagate BaseException. Use bounded
Result invalid_input/not_found/unavailable, with no exception/path/body leakage.

Exact base is the CLI --base containing this request and fixed tests. Needed inputs
are listed by CLI: scope/tests/current memory, intake, common contracts, sanitizer
and package. Write memory_v5 only; separate native context authored the fixed tests.
SOL integrates the returned diff and owns full verification. Return one complete
module-file change; no test edits, private-owner SQL outside MEM, TSK/PRI/RUN/ART,
old/live DB/migration, services, provider, new auth/cost or CO runtime/state edits.
In-memory real MEM/Intake fixtures are the declared metadata-unit verifier; managed
restart/Primary connection and usefulness are separate. CO verified covers that
command/files alone. The models execute no nested tools or tests themselves.

Plan exactly one implement step focused coding, <=2000 UTF8 instruction bytes;
refer to this request. Source worker is exact devin/swe-2-high on the existing Free
route. Planner is exact Claude Opus5.5. Scope follows the completed PRI Opus design
consultation; do not create another design gate or user permission request.
