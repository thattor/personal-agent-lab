# CHANGE01/1 final milestone design review

One bounded report task for exact qualified Opus5.5 through existing CO0.4.5.
The CO planner must keep step instructions within 2000 UTF-8 bytes: reference
this request rather than copying its sections (runtime hard limit is 4096).
SOL integrates; Astra authored TSK; separate Sol reviewed exact repaired source.
You did not author the implementation. Produce a milestone design verdict, using
the supplied proofs as attributed evidence, without claiming you ran their tests.

Goal: evaluate same-Goal saved correction's value, responsibility separation,
CHANGE01/1 and C02/C10/C13/C14 consistency, connection and abnormal-case proof,
and the smallest next authorized dependency. Root full845 and actual demo passed;
the original consistent-ID corruption was independently reproduced and repaired.
Code author b4baae24; tasks source SHA256
498b06ca6033c980bfdfe24b54195f247dbc7a46d267c67a1a54b0028f5c3e8f.
CLI `--base` is the exact input commit. Source excerpts are complete selected
methods generated verbatim; omitted methods are not claimed inspected. The full
implementation already received a separate exact-source Sol review.

Read only listed files. Write only
`evidence/operations/change01-20261009/opus-milestone-review.json`.
One report-producing step, no source changes, nested agents, second review task,
installation, network, state edits, real service, DB migration or product rollout.
No speculative PRI authority/semantic-usefulness acceptance. Dependencies and
connections are MEM/TSK/RUN/ART/VER/C14, all exercised with fresh temporary SQLite
and mock callbacks. Existing root/contract source is fixed; no new authority grant.

Return JSON with schema `PAL.CHANGE01.milestone-review/1`, contract `CHANGE01/1`,
source_sha256 as above, verdict `ALIGNED`, `REFINE` or `BLOCKED`, and nonempty
strings `value`, `responsibilities`, `contract_alignment`, `evidence_limits`,
`findings`, `next_dependency`. Describe severity and location for any finding;
say none if no finding. Recommend scoped C13 restart recovery/host lock versus
PRI routing from actual unmet contracts; identify technical work versus a real
human judgment, without turning routine technical choices into an approval gate.
Include `input_sha256` mapping of the actual supplied SCOPE, OWNER-EXCERPTS and
MILESTONE files. The public scope removed an operational conversation identifier;
its normative requirements are unchanged. Original local frozen-scope hash and
public hash are explicitly distinct in public-export.json.

The declared verifier checks this report schema and three input hashes only;
ALIGNED is not forced, and CO verified is not whole-PAL acceptance. SOL will read
the findings, adopt or repair them and update the canonical record. Report any
truncation or insufficient input; do not substitute model guesses for execution.
