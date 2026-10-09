# C13 current-lease uncertainty correction

Root reproduced an existing release defect identified during CHANGE01 design
preparation: status NULL/unknown/unrecognized passes the admitted-only guard and
can close an occupied lease. The present C13 contract already requires ended
calls before release. This correction rejects uncertain status as unavailable
before writes, preserving latest pause/cancel and slot occupancy. Recognized
admitted remains conflict; returned/raised/not_entered keep existing behavior.
It adds no C10.change, old-revision release, recovery or new authority semantics.

One Root regression method covers18 subcases (3 invalid statuses, plain/pause/
cancel, yield/failed). Initial corrected discovery:1 method,18 failures; after
the guard, related test_task*.py93 PASS0.815s. Original37-method invocation also
discovered the directly imported fixture TestCase; module-qualified import
removes those36 duplicate methods, without weakening the18 failure assertions.
Both original logs are retained. Next composed fixture tests use module imports
to avoid discovery of imported TestCase classes.

Evidence: evidence/operations/release-integrity-20261009. Separate source review
and Root full regression are pending. This narrow defect fix aligns an existing
contract; Opus consultation for CHANGE01 remains required before adoption.
