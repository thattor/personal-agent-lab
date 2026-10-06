# Defects and prevention

## 2026-10-06 — correction stranded an in-flight slot
Failure: new deterministic test showed conversational correction disabled the old Record/notes but left its consuming Attempt running. Publication fencing worked, but the global slot could remain occupied.
Cause/evidence: `record(supersedes=...)` and `forget()` used separate invalidation paths; [regression test](../tests/test_controls_memory.py) failed with `running != queued` before fix.
Fix: both operations invoke the same host transactional source invalidation helper, fence current attempts, and requeue incidental context or wait on explicitly required sources.
Prevention: keep correction/reference-stop publication and slot-release checks in the full suite. Next boundary changes must exercise both paths with an in-flight Attempt. 20 tests green after fix, including 18 real SIGKILL crash boundary subcases. No runtime DB repaired.

## 2026-10-06 — startup checkout mismatch
Observation: supplied cwd had no HEAD/remote and lacked required new root documents. Initial AGENTS lookup followed its old project-document pointer before identifying the mismatch. No old implementation code was read/reused.
Correction/prevention: clone only the named GitHub repository into an independent checkout, read its ordered root documents and current master Issue. For this greenfield project, reject a checkout without the mandated root STATE/SPEC/DESIGN/ACCEPTANCE/DECISIONS before following other project pointers. Preserved original workspace unchanged.

## 2026-10-06 — transitive memory reference stop
Review-driven finding: disabling a source alone still left an assistant reply derived from it eligible as later context. Fix: shared read boundary recursively verifies Record manifests and MemoryNote sources; raw derived records remain inspectable. Regression covers source→assistant→note propagation. This prevention is verified by the full 33-test suite.
