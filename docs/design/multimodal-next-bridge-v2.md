# 次版の画像・音声対応への接続計画

本人の2026-10-08指示により、現在のStable-1はテキストで完成させます。画像理解・録音入力・保存済み返答の読み上げは次版の計画として保持し、実装は未着手です。P-001や既存の将来段階を、この記録で採用しません。

[接続計画v2の正本](../../evidence/research/multimodal/2026-10-08/bridge-v2/BRIDGE-PLAN.md)に、MM0–4の目的、依存、出口と30件の担当をまとめています。[原設計v1](multimodal-qwen38-v1.md)と[補足契約](../../evidence/research/multimodal/2026-10-08/bridge-v2/CONTRACT-ADDENDUM.md)を合わせて次版の準備資料とします。動画・常時録音・ストリーミング会話は含みません。

Opusは計画を34.233秒、SWE-2 Highは修正契約を62.452秒で終端までレビューしました。[原文と採否](../../evidence/research/multimodal/2026-10-08/bridge-v2/REVIEW-DISPOSITION.md)には、途中終了した旧回答、全文再送のtimeout、対象を絞った完結回答、追加指摘の具体的反映と再レビュー未実施の範囲を残しています。全30製品ケースはNOT_RUNです。

MM0は資料・レビュー・計画登録の準備単位です。実機の品質、速度、音声再生や製品完成を意味しません。次版専用milestoneと親・MM0–4の実在Issueは登録readback後に下へ記録します。MM1–4はDEFERREDのままです。現在のN1条件・本人の総合有用性評価・最終監査は変更しません。

## 登録結果

[次版milestone8](https://github.com/thattor/personal-agent-lab/milestone/8)を、既存の[開発Project](https://github.com/users/thattor/projects/1)に所属するIssueで管理します。

| 作業単位 | Issue | 状態 |
|---|---|---|
| 次版全体 | [#13](https://github.com/thattor/personal-agent-lab/issues/13) | DEFERRED |
| MM0 設計・計画の準備 | [#14](https://github.com/thattor/personal-agent-lab/issues/14) | 完了 |
| MM1 原本・受付・復旧 | [#15](https://github.com/thattor/personal-agent-lab/issues/15) | DEFERRED |
| MM2 画像契約 | [#16](https://github.com/thattor/personal-agent-lab/issues/16) | DEFERRED |
| MM3 録音・読み上げ | [#17](https://github.com/thattor/personal-agent-lab/issues/17) | DEFERRED |
| MM4 実機統合評価 | [#18](https://github.com/thattor/personal-agent-lab/issues/18) | DEFERRED |

保存commit `e4ac3b2a428ad6a2a4df19482d1f92437a20dac8`とGitHubの実在本文・依存・milestone・Project所属を[照合](../../evidence/research/multimodal/2026-10-08/bridge-v2/REGISTRATION.json)してMM0だけを閉じました。次版全体と実装は完了していません。
