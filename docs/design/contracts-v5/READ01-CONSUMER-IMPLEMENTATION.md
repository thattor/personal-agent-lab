Tests NOT_RUN (no execution allowed). HostReader validates purpose first (ValueError), then the closed {ref} request (invalid_input), dispatches by RefKind with owner.read({'ref'}, purpose=purpose); note/source/receipt return unavailable, and an owner Exception, non-Result or malformed C11 success becomes unavailable. BaseException propagates and owner failures pass through unchanged. inspect_session scans up to max_pages pages. It fails on malformed, stalled or repeated cursors and passes on a C14 page failure. It selects result events and the exact NOTICE progress events. After scanning, it calls C02 get_work and reader.read(purpose='user_view') per event and Ref in order. Validity is current when usable. An unusable verification is 'source stopped' only when a NOTICE has the same Goal and revision and names one of the body's source_refs. Otherwise it is 'not current'. render prints mock and structural labels, a Read at line, TSK state, fixed Conditions, checks and artifact bindings, usability, per-work and per-ref error codes, and page truncation. 'source stopped' is printed only when validity says so.

Unresolved: ["All tests NOT_RUN; Root must run both frozen suites and full regression.", "HostReader checks the C11 shape and lowercase 64-hex hash, but does not recompute SHA-256 of content because MEM/ART hash semantics were not supplied.", "work_ref is allowed to be null in a C11 body (record bodies might have none); tighten if Root's contract forbids this.", "Source-stop correlation uses the C11 envelope source_refs, not the content source_refs; they are identical in the supplied doubles.", "An empty C14 page must return the cursor it was given (as EventReader does); any other value is treated as malformed.", "Saved record/artifact content is rendered in full with no length cap.", "Root owns real MEM/TSK/ART/VER/C14 demo evidence, actual source-stop probes and review."]

## SWE correction — 2026-10-09

Root's actual-contract audit (immutable test_read_regressions_v5.py) found three
behaviors missing from the implementation above; corrected in read_consumer_v5.py
only. HostReader was already correct and is unchanged. Tests are run by the
coordinator; this worker did not execute them.

- _parse_event keeps event refs as deep-copied JSON values in original order and
  value; malformed or unknown-kind refs no longer fail the page. Each item still
  reads every ref in order via reader.read({'ref': value}, purpose='user_view');
  bad refs surface HostReader's per-ref invalid_input with validity null and keep
  their original value rather than producing a whole-page failure.
- _scan selects result events and progress events with the exact NOTICE text as
  visible items in scan order, including notices without work_ref (whose work is
  a visible unavailable). Only a notice carrying a work_ref plus its valid refs
  grants source-stop cause, correlated by Goal+revision and named-Ref
  intersection with the body's source_refs.
- render labels each selected event 'Event N (kind)'. Valid refs render 'Ref
  kind:id'; malformed refs render safely via dumps. The 'Read at' line is now
  per-kind: record/artifact bodies show 'Observed at: X (stored observation
  time)' and only verification keeps 'Read at: X (time of this read, not
  creation time)'.

All previously listed unresolved limits remain unchanged.
