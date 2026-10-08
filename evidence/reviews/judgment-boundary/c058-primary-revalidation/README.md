# C058 — first-attempt qualification exposes unsupported Primary commitment

Candidate `f00f3dcbecc6ed5fb85e912530259ea4025ff30c`, product
`content:sha256:8f0f5b75c9b5c1e6fe6d4ee488c6c3aa8c1bae6fb46f79f1d1f6c28b65664bcb`.
The authoritative product value is the unchanged [17-file freeze](../primary-ask-first-candidate-freeze.json);
all calls were synthetic development inputs through official Claude/Opus under existing
Pro authentication, extra usage OFF, single-use proof, no paid fallback. No Expert,
worker, UI interaction, artifact or human evaluation belongs to these Primary-only runs.

| Run | Actual result | Closure |
|---|---|---|
| initial N01–24 launch | 0 generations; stdin was accidentally supplied by a completed heredoc | operator_closed, exit0, 0.098s |
| N01–24 launch2 | N01–22 in-run PASS; N23 captured before deadline and independently audited PASS afterward; N24 never called | PARTIAL, wall_deadline, 899.888s |
| R01–08 | eight cases PASS; 11 actual calls and one justified conditional-answer skip | qualification.finished, exit0, 228.911s |
| R09–16 | R09–14 PASS; R15 spec-grounding FAIL; R16 unexecuted; nine calls and two justified skips | stopped after first failure, exit0, 226.062s |

The 43 actual calls are all unique first attempts on this product. N23's original
journal remains unjudged/PARTIAL: [independent read-only audit receipt](n23-independent-audit-receipt.json)
is a separate observation, not an appended or backdated journal judgment. Its proposed
N24-only supplement was **not implemented or run**: the later R15 failure requires
repair before continuing this candidate. No timeout extension, proof renewal,
same-sample retry or canonical repair occurred. New independent12 and remaining UI
flows are NOT_RUN on this candidate. This is not N1-01/N1-02 or release PASS.

## Actual defect

R15's source says only: `まだ日付は決まっていませんが、招待文の下書きを作って。`
The first Primary response correctly chooses `local_draft` and leaves the date undecided,
but instructs Expert to say `後日あらためて連絡する旨を自然に伝える`.
No source supplies that future action by the sender. The accepted rule already forbids
invented commitments; this repeats C044's grounding defect at the earlier specification
boundary. The controller recorded FAIL and stopped without a worker or artifact.
Intent recognition and Goal integrity are distinct from semantic specification validity.

The smallest repair is under official Opus review through PAL設計. No new owner question,
schema, semantic keyword routing, payment or access permission is needed. The initial
ask-first repair has a real UI PASS in C057; that does not erase this subsequent failure.

## Evidence and limitations

Each subdirectory preserves the original fsync journal and every actual prompt/response
blob, sanitized access observation when present, and existing verifier result. `audit.json`
binds retained runtime DB/sidecar files and records all native supervisor PIDs absent at
audit. `MANIFEST.json` hashes retained bytes; proofs/credentials are not committed.
DBs and unused fixtures remain in their original runtime directories.

Product/scripts/tests are unchanged from the C056 full270-test PASS. Chain/blob checks
pass for all four journals; only the English cohort completed its frozen plan. N23
has independent semantic/Store/lifecycle audit, while other in-run judgments remain
controller judgments. Additional current-candidate qualification and final audit are
required. No Qwen, owner usefulness, unrestricted language coverage or long-term
reliability claim follows these measurements.
