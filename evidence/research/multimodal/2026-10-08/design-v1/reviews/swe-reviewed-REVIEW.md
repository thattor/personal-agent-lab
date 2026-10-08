# 設計レビューと採否

2026-10-08。対象は将来のマルチモーダル設計であり、PAL製品の合格判定ではない。

## Opus

既存の公式Claude Pro経路、追加利用OFFを確認して一度実行した。201.001秒、exit 0。ツールなしで同封資料を評価した。元の設計と評価計画、具体的なPALソース抜粋を渡し、回答は [reviews/opus-response.txt](reviews/opus-response.txt) に保存した。レビュー対象のhashは [input-freeze.json](reviews/input-freeze.json)、元文書はreviewsのreviewed-*に保持する。改訂後を再レビュー済みとは扱わない。

| 指摘 | 本資料での対応 |
|---|---|
| B1 メディア受付が未確定 | `/api/media-input`、有限JSON/base64、16MiB、復号後の種類別上限、同時受信2件を明記。独自のバイナリフレーム提案は、独自parserを増やすため採らない |
| B2 pendingキーと派生キーの衝突 | `_dedupe`とoperation投影の変更を明記。MediaInputから同じキーを内部トランザクションで引き継ぐ。新しい公開派生キーを作らず、終了状態の再送でも再推論しない |
| B3 過去画像をどう選ぶか不明 | 本人が画像カードで選び、入力欄へ表示する。元Recordをsourceとして束縛し、未提供画像はmetadataで明示する |
| B4 TTSのsource一覧が不足 | コピーしたsource配列を権限根拠にしない。response_idから既存manifestを再帰的に検査。boot_idとsession epochを追加 |
| B5 認識誤りを常に防げるという過大な条件 | 固定試験の正解照合と、通常利用の誤認識検出能力を区別。前者の重要条件誤りはFAILのまま。全発話確認や自動検出の保証は追加しない |
| B6 保存容量と未受理録音 | 永続メディアの1GiB論理quota、予約量・容量不足・監査経路を定義。TTS本体は有限の揮発キャッシュ |
| 入力世代、並行処理、由来 | 再利用しない入力キーには世代番号を置かず状態CASで処理。ASR等をPrimaryのpoolから分離。Recordへvoice_transcript由来を追加 |
| reasoningとmedia取得口 | final channelだけdecodeし、不正出力を勝手に修復しない。GETの無副作用、CORP等、通常のAI利用と本人監査を区別 |
| Expertから画像を外す提案 | 一律には採らない。文章へ落とした初回解釈だけに依存すると、重要な条件の原本再確認ができない。既存Expertが必要な場合に同じQwen・許可済み同一原本を読む契約は保持し、別モデル/別エージェントは増やさない |

指摘の根拠は現行のserver上限、Storeのdedupeとsource再帰検査、Runtimeの受付lock、Recordの由来情報の不足と照合した。修正はcontrollerによる設計上の解消であり、実装・fault試験の合格ではない。

## SWE-2 High

プロジェクトの実装設計相談方針に沿ってレビューを準備したが、まだ実行していない。

1. 実リポジトリをcwdとするauto/sandbox起動が、自動承認審査で拒否された。理由は、設計を超えるコード変更・外部実行の可能性と今回の明示承認の不足。
2. 公式資料を確認し、全ての読取・書込・shell・fetch・MCPをdenyし、subagentを無効にする一時設定を作成した。恒久設定やworkspace trustは変更していない。
3. その限定構成も自動承認審査で拒否された。二回目の理由は、非公開資料・ソース抜粋のDevinへの送信が具体的に承認されていないこと。
4. 本人に「今回の資料を既存Devin公式のSWE-2 High Freeへ、一度、ツール利用なしで送信する」範囲の承認を提示した。承認なしに送信しない。

二回ともレビュー本体は起動しておらず、Devinレビュー済みとは表示しない。この待ちを現在のPAL開発全体へ転用しない。設計資料の整理とOpus指摘への対応は独立して進めた。

公式の設定根拠：[Devin permission rules](https://docs.devin.ai/cli/reference/permissions)、[configuration file](https://docs.devin.ai/cli/reference/configuration/config-file)。これらは審査拒否を上書きする権限ではない。
