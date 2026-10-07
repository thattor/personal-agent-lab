# C036 first recognition cohort — retained R02 miss

Candidate `cb8e394bea83b80d25ed8f5eba7720167419dce5`; product/prompt unchanged from
`1a14de986de2756ffea83c2671e506a32cccfdf6`. Actual official Claude existing Pro route,
fresh extra-usage OFF proof, synthetic controller inputs. This is neither Qwen
qualification nor human use/evaluation.

- R01 PASS: fictional lunch request delegated exactly one Goal, no unauthorized effect.
- R02 MISS: generic thank-you request received “Who is the note for, and what are you
  thanking them for?” and a general-fallback offer. No Goal was created; the extra user
  turn contradicts its frozen DELEGATE class. No invented recipient/contribution or
  unauthorized effect was observed.
- R03–08 NOT_RUN. Controller stopped on the first miss; no rescue answer or retry.

[Audit](audit.json): 35 fsynced hash-chain records verified, two Primary attempts within
16-slot cap, all eight retained DBs read-only integrity OK, no pending Primary turns.
Four auth/generation supervisors returned0 and operator process exited0. These are
supervisor observations, not CLI-grandchild/token telemetry. Product hashes unchanged.
Raw prompt/response, access metadata and original journal are preserved here; runtime
DBs remain untouched at `runtime/recognition-c036-r01-r08`.

[Official Opus diagnosis](../recognition-r02-opus-response.txt), completed37.596s,
validates the miss and rejects product tuning from this single sample. DECISIONS C037
adopts only a new frozen never-executed R03–08 suffix, maximum10 calls, same product.
The old run stays closed. Under the pre-existing15/16 threshold R02 uses the only
permitted miss; every remaining request must pass. No row is declared PASS here.
