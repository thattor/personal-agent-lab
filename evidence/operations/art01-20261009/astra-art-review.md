Independent native Astra exact1afcfbe5eaac41721d63c0f12c71e60dae33661a: REFINE.
Two contract mismatches: size >1MiB invalid_input instead of C08 limit; duplicated
selected source_refs rejected despite shared ComposeAction preserving input arrays.
Author17 targeted PASS encoded both wrong restrictions. Independent probes retained.
Nonblocking savepoint leak on inspect gate exception was also reproduced.
Author98b8f12 fixes all three; targeted20 red3 ->20 green. Root fa40b66 cherry-pick is
byte-identical. Independent exact rereview is pending. Root actual duplicate-input
connection reproduced failed Goal before correction, now succeeds under fixed code.
