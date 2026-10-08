# 画像・音声対応の設計資料 v1

2026-10-08保存。**Qwen3.8-27Bを基準にした将来設計の引継ぎ候補。製品への採用・実装・実機評価は未実施。** 保存判断は [D-030](../../DECISIONS.md#d-030--retain-multimodal-research-and-design-materials-2026-10-08) に記録した。現行開発の継続点は [STATE.md](../../STATE.md) を参照する。

## 設計の範囲

本人の要望は、現在の開発を継続しながら画像理解・音声入力・音声出力を将来要件として具体化すること。動画も将来の拡張対象に含む。モデル探索を広げず、推論・画像理解の基準を **Qwen/Qwen3.8-27B** に固定する。「3.8」は世代、「27B」はモデル規模である。

- 画像：原本を保存し、質問とともにQwenへ渡す。初回は画像1枚を扱い、過去画像は本人が選択する。
- 音声入力：録音終了後に文字起こしし、確定した認識文を一度だけPALのPrimaryへ渡す。最初の試験候補はQwen3-ASR-0.6B。
- 音声出力：Primaryの処理結果に結び付いた保存済み返答を読み上げる。最初の試験候補はQwen3-TTS-12Hz-0.6B-CustomVoice。

動画、常時録音、連続音声会話、監査用の完了通知の読み上げは初回実装へ含めない。実行エンジン・量子化・実用速度の合格値は、実機がある段階で検証する。

## 読む資料

| 用途 | 正本となる保存資料 |
|---|---|
| 全体像と制約 | [設計概要](../../evidence/research/multimodal/2026-10-08/design-v1/README.md) |
| 受付・保存・重複防止・取消し・参照停止・再生の契約 | [設計書](../../evidence/research/multimodal/2026-10-08/design-v1/DESIGN.md) |
| HTTPとモデル接続の入出力例 | [CONTRACT-EXAMPLES.json](../../evidence/research/multimodal/2026-10-08/design-v1/CONTRACT-EXAMPLES.json) |
| 期待動作・必要な証拠・評価30件 | [ACCEPTANCE.json](../../evidence/research/multimodal/2026-10-08/design-v1/ACCEPTANCE.json) |
| レビュー原文への参照と指摘の採否 | [REVIEW.md](../../evidence/research/multimodal/2026-10-08/design-v1/REVIEW.md) |
| 開発へ伝える文章の候補 | [HANDOFF.md](../../evidence/research/multimodal/2026-10-08/design-v1/HANDOFF.md) |
| 類似製品・公開設計の比較と取得ソース | [調査報告](../../evidence/research/multimodal/2026-10-08/REPORT.md)、[保存資料の案内](../../evidence/research/multimodal/2026-10-08/README.md) |
| 保存範囲と照合結果 | [IMPORT.json](../../evidence/research/multimodal/2026-10-08/IMPORT.json)、[ARCHIVE-VALIDATION.json](../../evidence/research/multimodal/2026-10-08/ARCHIVE-VALIDATION.json) |

## 評価と引継ぎの状態

評価30件はすべて `NOT_RUN`。公開コードの確認、文書の整合検査、モデルによる設計レビューは、PAL上の機能・品質・速度の合格証拠ではない。

Opusの初回設計レビューは完了し、指摘への対応を記録した。SWE-2 Highは本人が承認した一回の呼出しで回答の一部を受信したが、600.016秒で打ち切られ、全文は未取得。受信した指摘を現行コードと照合して設計へ反映した。改訂後の独立した再レビューは行っていない。

調査初期の比較範囲より、後に作成した `design-v1/` の固定モデル・初回実装範囲を優先する。原本内の絶対パス、「リポジトリ変更なし」「未送信」などは作成時の記録として保持した。今回行ったのはリポジトリへの資料保存と参照の追加であり、PAL開発チャットへの送信や製品への取り込みではない。

実装を選ぶ際は、その時点のコードと案件判断へ照合して採否を決める。今回の保存でStable-1の完了条件や優先度を変更せず、設計レビューの履歴や過去の一回限りの承認を新たな実行権限として扱わない。
