# C049 — browser restriction investigation, 2026-10-08 JST

Outcome: the original artifact failure is a browser-rendered client block. The exact
policy or client defect remains UNKNOWN. A documented read-only owner check and private
OpenAI Support route are now identified. Access is not cleared; Stable-1 is incomplete.

## Authority and version

The persistent human window contains direct owner message `はい 送ってください。`
in turn `01a1188d-3eb8-7513-b4ee-ef00ce651726`, message
`01a1188d-3f6b-7ec2-8565-b25288585c6c`, authorizing the preceding concrete investigation
request. Source thread: `01a1137a-8de3-7890-b874-cdd0a7125711`.
No new access/authentication/payment/public reporting/bypass is authorized.

Initial clean HEAD/origin/main: `83767f33e84f44a19bf169af57d2b81990527844`.
Product: `content:sha256:53a616572229072f80feea032b133b714b19627938c16568705b8700a4b436ad`.
Goal card still reports BLOCKED; this explicitly requested investigation did run.
HR-ACCESS-002 remains resolved.

## Facts, inference and unknowns

- Original C045 ABS-A2 host interval: 2026-10-08 05:13:34–05:17:56 JST, port49957.
  This is the incident window, not the exact error timestamp.
- [Original screenshot](../reviews/judgment-boundary/ui-c045-partial/ABS-A2/artifact-browser-block.png)
  shows `ERR_BLOCKED_BY_CLIENT`, `127.0.0.1 はブロックされています`, and
  `このページは ChatGPT によってブロックされています`. Only reload is visible.
  SHA256: `0fef27c0efb6d74e474dd075590e4d94d02dfb9723ad80ef0d98de19046be2e7`.
- That run's ordinary UI showed completion and an artifact link. Its body was not
  obtained. ABS-A1 succeeded earlier on another owned port. This does not establish
  a blanket localhost ban or permission for every port.
- `pal/server.py:23-34,70-74` serves text/plain with no-store, nosniff, frame and CSP
  protections. Host mismatch returns JSON403, not the saved ChatGPT error page.
  `pal/web/app.js:48-52` uses a relative link, target=_blank, rel=noopener. Both files
  are identical to the C045 candidate. This does not prove the denied request reached
  the server or exclude every response/browser interaction. Request logging is disabled.
- Visible site rules, managed-policy values, installed app build and the original
  navigation initiator's effect remain unverified. The error alone cannot distinguish
  a user rule, managed rule, internal check, extension or client defect. No PAL patch
  is justified by these observations.

## Attempted supported diagnostics

1. Read allowed checkout source and retained evidence; view the saved error screenshot.
   No denied artifact bytes, runtime DB contents or global configuration were read.
2. `cua.getApp("Codex")` returned: `Computer Use is not allowed to use the app
   'com.openai.codex' for safety reasons.` No shell/native substitute was attempted.
3. Official MDM guidance documents chrome://policy. One attempt through the supported
   IAB API was refused: its URL policy permits only http/https. The tool expressly
   prohibits indirect execution, raw CDP, alternate surfaces or policy circumvention
   to achieve that denied diagnostic. No workaround/retry/policy reload followed.

These are separate diagnostic-tool limitations, not proven causes of C045. No successful
diagnostic-tab creation was returned. No old host was restarted, blocked page retried,
browser switched, settings changed, or denied body obtained. Original evidence is intact.

## Official sources checked on 2026-10-08

- [Settings — Browser](https://learn.chatgpt.com/docs/reference/settings#browser):
  Settings → Browser → Agent permissions offers default/per-site Browse, Download and
  Upload controls. Labels include Requires approval, Always allow and Block. Managed
  restrictions can apply. These are documentation labels, not installed-build observation.
- [Built-in browser](https://help.openai.com/en/articles/20001277-using-the-built-in-browser-in-the-chatgpt-desktop-app):
  local development is supported, subject to site/workspace restrictions. Personal
  approval does not override applicable management restrictions.
- [Managed browser policies](https://help.openai.com/en/articles/20001535-manage-chatgpt-desktop-browser-policies-with-mdm):
  names chrome://policy for administrator inspection. Our transport denies this scheme;
  no policy change or developer-access enablement is a diagnostic prerequisite here.
- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference):
  origin rules distinguish scheme/port and applicable denies win. This is possible
  policy behavior, not this machine's effective configuration.
- [Troubleshooting](https://learn.chatgpt.com/docs/reference/troubleshooting#feedback-and-logs):
  `/` in the composer exposes feedback; sharing the current session is optional.
  Logs require sensitive-data review. No feedback was submitted.
- [Private OpenAI Support](https://help.openai.com/en/articles/6614161-how-can-i-contact-support):
  use the lower-right help.openai.com chat bubble with error, time zone, environment and
  sanitized screenshot. No message sent. Desktop HAR capture is documented unavailable;
  do not enable developer access or repeat/switch the denied request to produce a HAR.

## HR-ACCESS-003 — one read-only owner observation

Needed fact: visible Browse default and any exception for `127.0.0.1` or
`http://127.0.0.1:49957`. This is inaccessible environment evidence, not a design preference
or permission request. Target version/product and original evidence are bound above.

Recommended owner operation:
1. Open Settings → Browser → Agent permissions in the desktop app.
2. Report Browse default and matching local-site exception: Block / Requires approval /
   Always allow / no matching entry / screen unavailable. Note managed/locked if shown.
3. Change nothing. Do not remove rules, grant access, reload the failed page or restart.
   If the screen differs, report that fact; this installed build is not verified.

Impact: read-only; no permissions or PAL/model activity change. Reason: distinguish a
visible deny from a condition requiring administrator/vendor investigation. Non-Block
does not itself clear the original error. A matching rule requires its source and smallest
supported remedy to be assessed before any permission change. If absent/nonblocking or
the settings are unavailable, use the [prepared private support draft](c049-support-draft.txt).
App/account details should be entered only in private Support, not the repository.
No public GitHub report or full-session sharing without separate authorization.

Release condition: establish a supported permitted path, then verify remaining frozen
actual UI coverage. Settings/report submission alone is not clearance/PASS. Preserve
C045 ABS-A2 NOT_VERIFIED and historical caps. Deliver this handoff once to the persistent
human window, then respond to the actual returned facts.

## Verification and process correction

Documentation/evidence only; source/tests/harness unchanged from full268 PASS24.048s
(`evidence/reviews/judgment-boundary/c047-full.txt`). No redundant suite/provider call.
Check diff formatting, local references and unchanged source/screenshot hashes.

C048 stopped at access wait without completing safe official-guidance/diagnostic
investigation. Refusal to access content still leaves documented diagnosis/support as
independent work. Record this distinction in DEFECTS.md; no new permission, product
design, acceptance or review gate is adopted.
