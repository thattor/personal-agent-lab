# C050 — answered access check and continuing development, 2026-10-08 JST

HR-ACCESS-003 is answered. Original browser access is unresolved. Remaining real-provider
artifact/UI verification is stopped; this checkpoint performed authorized diagnosis and
recording, not a model run. Stable-0 remains released; Stable-1 and overall PAL incomplete.

## Authority and response provenance

The latest direct owner instruction in development chat
`01a11113-f829-75c1-b728-3298aa3359b5` authorizes continuing Stable1 and three cooperating
lanes. Canonical roles/IDs/waits are in [STATE.md](../../STATE.md); no parallel source of
truth is introduced. The existing design-change chat is
`01a11837-e1e3-71f0-8ff8-bbaf8dc14527` (マルチモーダル対応設計を確認). Its owner explicitly
described a continuing design-to-development role and requested retaining reusable
materials in the repository. This discovery registers that route, not future scope adoption.

Human thread `01a1137a-8de3-7890-b874-cdd0a7125711`, exact title `PAL人間判断`, contains
the authorized handoff in turn `01a118df-d5a2-7502-84b7-7008eb4683cc`, item
`fco_01a118df-d5c9-7e10-bc90-2196eb7fe8d5`. It reports the owner's explicit instruction
「そのまま伝えて」 in settings-help chat `01a118dd-7b75-7e92-9ab1-ca8c4243a7ff`.
This development turn also received the owner's explicit instruction to consume that
answered check. Reading the settings-help thread itself returned host unavailable;
the human-window handoff and supplied screenshot are the available provenance, not
an invented direct transcript. Original screenshot was viewed, not changed or published:
`codex-clipboard-de69a653-1304-45b5-85e5-7e0ecbd35d49.png` (hash in validation.json below).

Observed facts:
- Browser → エージェントの権限 → ウェブ閲覧 default: 常に許可 (Always allow).
- Original `http://127.0.0.1:49957` has no displayed individual exception.
- Displayed unrelated local-site entries4301/4173/4174 all show Browse Always allow.
- No visible target Block/managed-lock indicator in that image. CDP full access is off.
- No settings changes are reported or performed. The image does not establish every
  effective rule or the installed app build.
- Human-window handoff separately reports ERR_CONNECTION_REFUSED on the stopped URL.
  It is not ERR_BLOCKED_BY_CLIENT and is not evidence of access clearance.

Original C045 candidate: `814638db3e8742e68b2fe675c6abc41632d21a5e`.
Current checkout at start: `5e7c76c24dd8bf700d2811c7188739cdc77d9aa8`.
Product: `content:sha256:53a616572229072f80feea032b133b714b19627938c16568705b8700a4b436ad`.
[C049 investigation](c049-browser-block-investigation.md) and original denied screenshot
remain unchanged. Exact winning restriction/cause is UNKNOWN. No request-log evidence
proves whether the denied request reached the host. A narrow lsof check observed no
listener on49957; no old host was restarted or page retried. Host macOS version is27.0;
installed desktop app build remains unknown.

## HR-ACCESS-004 — one concrete external-send decision

Background: visible owner settings do not explain the original client block; native
settings and chrome://policy diagnostics are unavailable through the allowed tools.
No documented supported self-service remedy is established by the checked evidence.
Product source does not justify a PAL patch or permission workaround.

Recommendation: privately submit [this exact text](c050-support-draft.txt) to OpenAI
Support through help.openai.com's chat. Initial submission contains only the error,
incident interval, generic localhost route, observed permission facts and safe diagnostic
questions. It contains no repository name/source, conversation history, generated
artifact, credential, account identifier or screenshot attachment. The previous draft
is retained. Support may request app/account details later through its private channel;
do not turn that possibility into several pre-emptive owner questions.

Only needed owner decision: authorize that narrow submission by development, or submit
the same prepared text personally and return the case/reply. The latest development
instruction expressly excludes external-support sending from inter-chat permission;
this is the reason for the approval boundary. No support message has been sent and no
vendor case exists yet. Do not imply OpenAI is already investigating.

Waiting work: artifact-dependent remaining frozen UI/Expert cases, current complete-flow
human usefulness and final release audit. Independent work completed here: answered
check incorporation, source/evidence review, concrete support text and scheduler inquiry.
No other independent required product slice identified. No provider/access-proof renewal.

Release condition: official supported diagnosis/remedy or allowed access path, within
existing authority (seek a scoped decision if new authority is needed). Submission or
non-Block settings alone do not satisfy it. After actual supported clearance, re-read
the current source/decisions, establish a clean candidate freeze, and run only the
remaining approved cases with bounded fresh proof; then
one genuine current-version usefulness evaluation and final audit. Original failed,
NOT_VERIFIED and VOID results remain immutable.

## New 50-minute checkpoint — NOT_CONFIGURED

Latest owner request permits a NEW development-only recurring follow-up, conditional
on noninterrupting delivery. It does not permit restarting either old PAL automation.
Saved configs were read; both `pal` and `pal-stable-0-soak-audit` remain PAUSED. Supported
automation view calls only returned that cards were rendered, no delivery-policy metadata.

[Official Scheduled tasks](https://learn.chatgpt.com/docs/automations#schedule-a-task-inside-a-chat)
confirms minute-based follow-ups using the existing chat. It does not specify whether
an active turn is skipped, queued, steered or interrupted. The exposed automation tool
also lacks that guarantee/configuration. Goal idle-continuation documentation describes
a different mechanism and cannot prove heartbeat delivery. A changelog fetch failed;
no claim is based on its search snippet. Native app inspection/policy bypass is not used.

Thus no new schedule was created/saved/activated or tested on running work. No old
schedule changed. Pending question to official support is included in the same concrete
draft; this does not ask the owner to decide technical scheduler behavior. On supported
confirmation of noninterrupting delivery, create a new heartbeat at50-minute intervals,
use failed-runs-only notifications, preserve the current allowed checkout and stop on
completion or direct cancellation. Re-read saved config and tool result to verify actual
activation; record observed execution separately. No cache/session/crash/limit guarantee.

Exact requested checkpoint content (preserved as the user's request, not a configured task):

> 継続確認です。進行中の処理・ツール呼び出しを中断、再実行、重複起動しないでください。現在の作業を優先し、安全な区切りで既存のSTATE.mdに対象版、完了事項、作業中の内容、次の操作を必要な場合だけ反映してください。その後、承認済みの未完了作業を続けてください。新しい問題がなければ本人への通知は不要です。人間判断・外部条件待ちの場合は、同じ質問や拒否された操作を繰り返さず、待ち状態を維持してください。

Notification preference must be applied through the supported notificationPolicy field,
not relied on as scheduler semantics. No standalone cron substitute is authorized.

## Parallel design materials reconciled

Design turn `01a119c7-efdd-74e0-a4f7-3725d8a56364` contains the owner's retention
instructions (messages `01a119c7-f0da-7f92-b891-129f1171954e` and
`01a119c8-a03d-7822-88eb-ffcf0495e145`). The design chat copied the authorized archive
while this development checkpoint was in progress. A necessary coordination message
stopped further shared-document changes or stage/commit/push by that lane; the design
chat confirmed the archive checks and handed integration to development. Development
reads only the copied materials in the allowed repository, not their original task folders.

[D-030](../../DECISIONS.md#d-030--retain-multimodal-research-and-design-materials-2026-10-08)
records adoption of retention only. 80 original files, including 24 public-source files
with pinned provenance and licenses, are preserved with their historical outcomes.
The 30 proposed evaluations remain NOT_RUN; the SWE response remains partial. Source
snapshots and preserved helper scripts are research evidence, not runtime dependencies.

The first local-reference check ran before the parallel archive validator finished and
reported its missing receipt. The initial C050 validator also wrote an aggregate PASS
before all checks ended; that uncommitted claim is corrected. Final checks run after the
archive handoff, and the final aggregate result is written only after every check succeeds.
Old C049 current-state wording in the archive's shared-document additions is reconciled
with C050 without rewriting historical evidence. Future parallel work must keep the
development lane as sole canonical writer and hand off scoped artifacts instead.

## Verification and limits

[Validation](c050-validation.json) binds image/source/evidence/config hashes and actual
checks. Product/scripts/tests unchanged from C047 (268 PASS, 24.048s); no redundant suite,
new test, model generation, canonical database write or acceptance promotion. The
authorized research retention was integrated and independently verified without executing
downloaded code. No product design or substantial implementation change, hence no new
Opus/SWE call. HR-ACCESS-004 was delivered to PAL人間判断 and presented there as one
pending scoped decision; the chat agent's acknowledgement is not owner approval.
