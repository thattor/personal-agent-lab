Current UI02 admission source repair

Root reproduced the existing source fault on base d1639a5fa4a6229fddcd08d53b805cafa10efb9c, then ported the exact earlier v5 repair and frozen four tests. The complete typed owner envelope, closed turn ID/status reply and token/status must validate before retention or enqueue. An ordinary owner exception now returns pathless unavailable/503, latches held, preserves saved input and releases an untransferred admission reservation. Valid replay still dispatches only once.

Independent Astra APPROVE_SOURCE_ONLY: fixed4 and five separate methods/fifteen cases pass. Probes include invalid tokens/envelopes, saved missing ID, pre-save exception, close racing durable admission then exception, and terminal replay statuses. Independent Sol6.1 preservation checked3196 bindings with zero differences. Root recomputed actual report/log/source/contract hashes and passed full1107 without skips. Exact hashes and counts are in verification.json; private original logs/reports remain retained.

Cause and prevention: status-only submit handling differed from the complete-owner validation already required by UI02-NATIVE-FIXTURE/1. The fixed admission tests now preserve this rule. The prior repair was absent from the latest public source even though an isolated historical checkpoint had passed. Resume checks must reconcile exact source/diff inclusion, rather than rely on D075/D076 labels reused in separate histories. The historical histories and their evidence are preserved.

Scope: source/fixture proof only; no contract change, actual provider trial, hosted CI on this port, current genuine browser qualification, old unknown retry/release, Issue22 adoption or whole-product acceptance.
