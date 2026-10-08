# Personal Agent Lab

Private greenfield development repository for an open-sourceable personal AI assistant focused on:
- natural conversation;
- durable memory and recall;
- task completion without user-side task management;
- Primary/Responder and Expert/Executor delegation;
- evidence-based finish and restart-safe continuation.

## Current goal
**Stable-1 release candidate**, product `e851cae0`, is ready for its one whole-flow owner usefulness evaluation. Technical functionality is proven at the scope recorded in [C061](evidence/reviews/judgment-boundary/c061-target-function/README.md). It is not yet a Stable-1 release or overall project completion. D-031 ends additional prose-quality tuning; known editable-output imperfections are accepted for initial use.

**Stable-0 complete** under the D-019 functional-first definition. Version `stable-0`; [completion evidence and limits](evidence/final/stable0/README.md). All20 required acceptance rows and final66 tests PASS; master Issue #1 closed.

## Start here
- AGENTS.md — rules for Codex, Opus, and SWE-2 High collaboration
- CODEX-PROMPT.md — paste/run this as the Codex goal prompt
- SPEC.md — Stable-0 product scope
- DESIGN.md — accepted architecture
- ACCEPTANCE.md — definition of done and evidence gates
- DECISIONS.md — durable decisions and reviewer conclusions
- STATE.md — current implementation state and next action
- [Future image/audio design and research](docs/design/multimodal-qwen38-v1.md) — Qwen3.8-27B handoff candidate and retained evidence; not implemented

## Important
This repository is greenfield. Old PAL implementations and compatibility constraints are explicitly out of scope.

Stable-0 requires all structural and functional acceptance rows plus one direct human usefulness evaluation (D-019). The historical 72-hour soak is optional and remains unmet; functional acceptance makes no long-term stability claim.

## Run deterministic tests

Python standard library only; no dependency install required.

```sh
python3 -m unittest discover -s tests -v
```

The host canonical store is in `pal/store.py`. It is not an Executor capability. Draft bytes are bounded SQLite blobs and host receipts are verified by readback. The loopback UI defaults to mock. The explicit official live functionality and direct human evaluation are recorded in evidence/final/stable0/audit.json. See STATE.md for the current release state and completion record.

## Local conversation and inspect

```sh
python3 -m pal.server --db runtime/pal.db --port 8765
```

Open http://127.0.0.1:8765/. Ordinary chat/remember requests do not create Goals. “Make a draft …, do not send” creates a local draft; “stop that”, “pause that”, “resume that”, “correct that: …”, “answer: …”, and “forget that” apply to the current work/context. Inspect is read-only and shows Goal, Attempt, fixed criteria, receipts, rejected results and errors. No send/shell/remote write capability exists. Browser Session receipt contains accepted IDs, without message bodies; copy it before closing a test session when evidence is needed. Scripted receipts do not constitute human evaluation.

## Official native smoke

`scripts/live_smoke.py --help` documents the explicit proof-file route. Verify the existing signed-in official Pro account, quota, credits OFF and auto-reload OFF immediately before running. Access proof expires after 15 minutes and native authentication is checked again. Do not fabricate a proof or enable paid fallback. Existing successful proof is an historical smoke record, not continuing authorization for new model calls. Default UI and optional soak make no native calls.

## Explicit bounded real-provider UI

After the controller actually verifies the existing official Pro account, quota, credits OFF and auto-reload OFF, it may create a metadata-only proof file with exactly `verified_at` (current Unix seconds), `no_extra_charge` (true), and `route` (official_claude_pro). No credential or token belongs in that file. Then start explicitly:

```sh
python3 -m pal.server --db runtime/functional.db --port 58500 --provider official_claude_pro --access-proof runtime/fresh-proof.json --native-call-limit 16
```

The proof is consumed once per checkout and expires after 15 minutes by both wall and elapsed time. Failed startup burns a valid proof. Keep runtime/native-proof-use markers; copying a proof or changing its JSON formatting cannot renew it. This is a local operator guardrail, not cryptographic attestation or a global account limit. A trusted operator can forge/delete local metadata or use another checkout.

The shared conversation/task provider reserves at most 16 generation invocations (configurable 1–32). Failed calls consume a slot. This bounds host invocations, not unobserved CLI HTTP retries or token refreshes. Each auth phase has a 10-second bound; generation is rechecked for freshness after auth and has a 120-second deadline. A call admitted just before expiry can finish within 1020 seconds of proof verification. UI shows mode, remaining budget and closed failure codes; read-only provider status also exposes the expiry timestamp. Expiry/exhaustion/auth failure remains visible; no silent mock substitution, renewal or retry. Fresh verification and an explicit restart are required for new calls. Failed work requires a new request.

Cancel/pause fence work results without killing unrelated conversation. An already admitted call can consume its slot after cancellation; shutdown or host death terminates supervised auth/model processes. Fixed functional scenarios are in ACCEPTANCE.md. Content checks and actual provider outputs are separate from the user's single usefulness evaluation.

## Optional historical soak

The monitor in scripts/soak_monitor.py remains available for separately requested long-term observation. Earlier DBs, hash chains and human receipts are retained without repair or clock transfer. None of the stopped historical runs satisfies the original 72-hour criterion. D-019 removes only the mandatory time/turn/session quotas; all canonical, security and restart tests remain required.


## Stable-1の使い方と現在の制約

実モデルを明示して起動した画面では、日本語・英語で自然に依頼できます。
会話の文脈を使ってローカル下書きを作り、足りない情報を質問した場合はそのまま
回答してください。対象が複数あれば、どの作業かを選んでから訂正します。
作業中・一時停止中は会話か作業欄の「訂正」「中止」を使えます。
完了済みの本文を変更したいときは、変更点を添えて「新しい下書き」を依頼します。
成果物は「下書きを開く」で表示し、送信前には本人が必要な内容を確認します。
外部送信・公開・予約などはできません。

残して使いたい情報は「覚えておいて」と伝えられます。「AI参照を停止」は今後の
AIへの参照を止める操作で、保存済み履歴の物理削除ではありません。文脈は直近30記録・
先頭20記憶に制限されます。すべての過去の会話を覚えているとは限りません。

下書きの言い回しや補足には不完全さがあります。訂正と利用時の指摘を踏まえて
改善しますが、自動学習・自動モデル更新・経験から必ず改善する機構は未実装です。
追加の文章品質試験を続ける代わりに、初期版を使えることを優先しています。
権限・費用・誤対象の変更・参照停止・復旧の保護は維持します。

現在の実測モデルは既存の公式Claude/Opusです。Qwen3.8-27Bは能力基準の参照であり、
PALでの実動作は未検証です。画像・音声入力は将来版の設計準備で、現行版にはありません。
公式実モデルの利用は新鮮な既存契約確認後の有限セッションです。通常は16呼出し以内・
15分の利用証明で、1依頼がPrimaryとExpertの2呼出しを使う場合があります。
期限切れ・上限到達時に有料経路へ切り替えず停止し、保存済み結果は閲覧できます。
再開には開発側で現在の費用設定を確認して明示的に起動し直す必要があります。
常時自律実行・自動監視や停止済みスケジュールは有効化していません。
