# C045 corrected-candidate UI evidence — partial

Candidate `814638db3e8742e68b2fe675c6abc41632d21a5e`, product
`content:sha256:53a616572229072f80feea032b133b714b19627938c16568705b8700a4b436ad`.
The owner-selected Qwen3.8-27B capability reference remains unqualified. These runs used
the existing official Claude Pro route, with fresh authenticated/extra-usage-OFF proof
for each finite host. Controller-entered synthetic inputs are not human evaluations.

| Frozen case | Actual result | Native slots | Evidence |
|---|---|---:|---|
| ABS-A1 | PASS: missing recipient/date/time visibly unspecified; no invented follow-up promise; one actual artifact, receipt/hash/UI binding verified | 2/2 | [Independent audit](ABS-A1/independent-audit.json), [artifact UI](ABS-A1/artifact-ui.png) |
| ABS-A2 | NOT_VERIFIED: UI reported completion, but artifact navigation was blocked by the browser client | 2/2 | [Block screenshot](ABS-A2/artifact-browser-block.png), [limited finding](ABS-A2/controller-semantic.json) |
| TARGET-A | PASS: no current work; explains absence without creating or changing work | 1/1 | [Independent audit](TARGET-A/independent-audit.json) |
| TARGET-B | PASS: nonexistent/terminal targets untouched; only the named waiting work cancelled, its question closed and its existing Attempt fenced | 3/3 | [Independent audit](TARGET-B/independent-audit.json), [actual UI](TARGET-B/conversation-ui.png) |
| RUNNING-CANCEL | VOID: first metadata observation was already completed; no cancel sent, unfinished cancellation/fencing NOT_VERIFIED | 2/6 | [Metadata-only audit](RUNNING-CANCEL/independent-audit.json) |
| Other nine hosts | NOT_RUN | 0 | [Original frozen allocation and inputs](contract.json) |

Ten native slots consumed. No unused capacity transferred, retry, rescue answer, paid
fallback, new login, external sending or canonical repair. All five owned hosts exited
normally, ports closed, within their individual 600-second bounds. Product hashes
remained unchanged. [Full249 deterministic tests](full-after-live.txt) PASS20.122s after
TARGET-B, before the later unchanged-source RUNNING-CANCEL metadata probe.

The original C044 unsupported-promise FAIL remains immutable. C045 ABS-A1 is the first
affected regression on the corrected product, not proof of all six absence samples or
general model reliability. Independent source review is retained in
[c044-independent-diff-audit.json](../c044-independent-diff-audit.json).

The ABS-A2 page showed `ERR_BLOCKED_BY_CLIENT` and explicitly said ChatGPT blocked the
page. No reload, alternate browser/endpoint, HTTP artifact fetch or DB-body access was
used to obtain its contents. Existing server source was inspected; no product cause is
established. [Operational amendments](operational-amendment.json) and
[metadata-only cancellation scope](operational-amendment-02.json) allowed independent
checks while preserving this block. This was a browser-client restriction, not an
automatic shell approval rejection. Artifact-dependent work remains unverified.

Observer mistakes were corrected without new inputs or canonical writes: ABS-A1 summary
initially looked for a nonexistent Goal specification field; TARGET-B initially expected
all Attempts unchanged even though normal cancellation fences the target Attempt.
Reports retain both errors and their source-based corrections. The independent TARGET-B
audit also records correcting an overly narrow reply-manifest assumption. These are
observer corrections, not acceptance weakening or product repair.

[Copy audit](copy-audit.json) binds55 exact source-file copies. DBs, WAL/SHM/locks,
AccessProof files and unviewed artifact bodies stay excluded from Git and preserved in
`runtime/c045-ui-current/`. Nothing here completes Stable-1, N1-07 human usefulness or
the project. Next: reviewer-guided deterministic scheduling at the existing test fault
boundary for the remaining actual cancellation proof; resume artifact-dependent cases
only through an allowed browser path, with original outcomes preserved.
