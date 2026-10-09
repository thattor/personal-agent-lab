# Independent recovery display connection review

Verdict APPROVE, user_view discovery only.
Root's exact dirty source SHA256:
`ebbd03b1fa4a8d5cd2047ef6e08deff8aa26022fb6d2344f8a4e24f052c2aea0`.
Prior base 23312e83c21707e7103f4d472a402805cc0e9cd2.
Review isolated exact source overlay is an uncommitted read dependency; only this
note is committed. No Root source/test/shared-doc edits.

The change adds one fixed notice constant and selects a C14 state event only when
its text exactly equals `mock saved draft recovered`. This matches Root's clarified
RECOVERY02/READ01 display disposition: TSK emits the state event with the adopted
ART Ref, and ordinary display must discover that body despite no result event.
No parsing, source authority, typed TSK proof, completion grant or model_context
path is added. Owner APIs still determine current Work state and C11 body validity.

Selected notices traverse the existing strict C14 page validator, C02 request
{goal_id,revision}, and HostReader C11 {ref}, purpose=user_view. Arbitrary matching
text can only make an event discoverable: owner work/read results still supply its
state/body; it cannot mint adoption, producer proof or completed status. Missing
work, malformed/unsupported Ref and owner errors retain the same per-item handling.
The source-stop notice collection/correlation is unchanged; current versus history
verification labels still depend on C11 usable and matching Goal/revision/source
notice. Render escaping, body/hash/inspection JSON and other state exclusion are
unchanged. No mutable owner API is called.

Independent checks:
- `/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p 'test_read*_v5.py' -v`: 32 PASS, 0.164s, including source-stop/history, errors and display-control escaping.
- Inline public inspect_session strict-doubles probe: exact state phrase selected
  and artifact read only as user_view; queued owner state remains queued and no
  verification validity is invented. Trailing-space phrase, matching progress
  phrase and other state text excluded (4 PASS cases).
- Exact SHA and git diff --check confirmed.

Logs /private/tmp/pal-recovery02-read-review.log and
/private/tmp/pal-recovery02-read-probe.log. Existing tests remain unchanged.
Root's unchanged real-process4 PASS is reported separately, not rerun or claimed
as independent here. This narrow review approves display connection, not recovery
integrity/TSK authority, full C13, Primary/provider or product usefulness. Root
owns exact source integration/full suite and canonical qualification.
