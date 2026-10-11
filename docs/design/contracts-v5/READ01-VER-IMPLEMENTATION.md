# READ01/1 VerificationStore.read implementation

## Scope

- `VerificationStore` accepts optional `clock`; non-callable values raise `TypeError`, and the default emits a timezone-aware UTC `isoformat()` value.
- `read({ref}, *, purpose)` accepts only `model_context`, `verification`, or `user_view`; invalid purpose raises `ValueError` before connection-state checks or dispatch.
- The request is closed. Malformed input is `invalid_input`; a valid non-verification Ref is `unavailable`; only an absent verification row is `not_found`.
- One deferred read transaction validates the stored record, derives current status through existing trusted callbacks, then calls the guarded clock. The clock must return a nonempty ISO-8601 UTC string (`Z` or zero offset).
- A `not_found` reported by the trusted status/owner callbacks means current status cannot be established and maps to `unavailable` in `read`.
- `content` is `contracts_v5.dumps` of exactly `work_ref`, `conditions`, `artifact_refs`, `artifacts`, `source_refs`, and `checks`; each artifact exposes only `{artifact_ref,hash,bytes}`. `media_type` is `application/json`, and `hash` is SHA-256 over the returned UTF-8 content.
- `observed_at` is read-observation time, not creation time, and neither it nor current status appears in content/hash.
- Valid records return `usable=true` for all purposes, including unknown checks. Invalidated records return the same history with `usable=false` for `user_view`; `verification` and `model_context` receive `denied`.

## Boundaries and limits

- `get_verification` and `inspect` are unchanged; a read does not grant completion, dispatch, semantic, or re-input authority.
- Ordinary reads leave the durable dump and `total_changes` unchanged. Rolled-back injected writes may still increase `total_changes`.
- A trusted callback/clock `COMMIT` cannot be undone; the implementation reports failure and never claims rollback after such a commit.
- This change adds no schema, state, model/context, service, auth, cost, host reader, consumer, or real SQLite/demo integration. Synthetic in-memory coverage only; no whole-product completion is claimed.
