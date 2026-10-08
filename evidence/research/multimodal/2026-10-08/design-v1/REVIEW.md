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

プロジェクトの実装設計相談方針に沿って準備した。以下は承認前の履歴であり、その後の本人承認と実行結果は後段に記録する。

1. 実リポジトリをcwdとするauto/sandbox起動が、自動承認審査で拒否された。理由は、設計を超えるコード変更・外部実行の可能性と今回の明示承認の不足。
2. 公式資料を確認し、全ての読取・書込・shell・fetch・MCPをdenyし、subagentを無効にする一時設定を作成した。恒久設定やworkspace trustは変更していない。
3. その限定構成も自動承認審査で拒否された。二回目の理由は、非公開資料・ソース抜粋のDevinへの送信が具体的に承認されていないこと。
4. 本人に「今回の資料を既存Devin公式のSWE-2 High Freeへ、一度、ツール利用なしで送信する」範囲の承認を提示した。承認なしに送信しない。

承認前の二回はレビュー本体が起動していない。この待ちを現在のPAL開発全体へ転用しない。設計資料の整理とOpus指摘への対応は独立して進めた。

公式の設定根拠：[Devin permission rules](https://docs.devin.ai/cli/reference/permissions)、[configuration file](https://docs.devin.ai/cli/reference/configuration/config-file)。これらは審査拒否を上書きする権限ではない。


### 本人承認後の一回の実行

本人が本チャットで「明示的に承認いたします。」と回答したため、今回の資料と必要なPALソース抜粋を既存Devin公式SWE-2 High Freeへ一度送った。[承認と固定入力](reviews/swe-authorized-input.json)、[送信した全文](reviews/swe-question.txt)を保存した。承認はこの限定レビューに限り、他の送信や恒久設定変更へ広げていない。

既存認証と、実行直前のSWE-2 High **Free** 表示を確認した。ファイル読取・編集・shell・fetch・MCPをdenyし、subagentも無効とした一時設定を使い、既存workspace trustは維持した。[実行前確認](reviews/swe-access.json)。追加課金や別モデルへのfallbackは使っていない。

**結果は一部受信、レビュー全体は未完了。** [原文](reviews/swe-response.txt)は4,601 bytesで、600.016秒の打切りにより実装ノート9の途中で終わった。[終了記録](reviews/swe-completion.json)。冒頭の判定「条件付き引継ぎ可能」とブロッカー2件、実装ノート1〜8は読めるが、要求した最終節までの回答は取得できていない。改訂後をSWEが再レビューした事実もない。

### 受信した指摘の採否

| 指摘 | 現行コードの確認と反映 |
|---|---|
| B1 キー予約の保存場所 | store.pyの_dedupe/_rememberと_finish_primary_outcomeを確認。予約はmedia_inputsだけに置き、dedupeのprimary行は終端確定時だけ書くと明記。終端確定は通常完了だけでなくrecoverからのinterruptedも同じ関数を使う |
| B2 通常textへの再送での混同 | prepare_primaryが既存primary_turnsを先に返す経路を確認。この早期returnより前にmedia予約を検査。受付hashをmedia-v1:付き形式にして通常textのhexと区別する。ASR結果を後から受付hashへ混ぜる提案は採らず、再送照合を不変にし、認識文hashは派生情報へ分離 |
| JSON・画像選択・保管・CAS | 重複JSONキー検査、選択画像付き文字入力のimage_ref経路、入力ごとのBLOB複製、UPDATE件数1による成功判定を明記 |
| 結果の対応付け | ASR送出時のoperation/asset/hashをhostで束縛し、Qwen adapter封筒のrequest_idをホストの呼出しへ照合。モデルの自己申告を権限根拠にしない |
| 完了通知のmanifest | store.py:670–675でdeliverの監査Recordにmanifestが付かないことを確認。v1はPrimary outcomeに束縛された返答だけをTTS対象とし、raw監査通知は拒否。通知音声化はsourceを持つ人向け文章を保存できる段階へ分ける |
| 音声区間失敗・画像展開 | TTS区間失敗時はplayback全体を終了。画像decoderの割当制限と実デコード結果の検査、view一つ10MiBの上限を明記 |
| 枠枯渇についてのノート9 | 原文は途中で終わっているため残りを受信済みとは扱わない。controller側で、利用不能な処理枠しかない場合は新規依存入力を拒否し、保存済み待機を終端化すると具体化 |

評価ケースMM-S01/S05/S06/S10/S15へ条件を加え、30ケースのまま全てNOT_RUNを維持した。資料とコードの照合は設計上の解消であり、未実装の動作確認ではない。

### 途中終了の記録と次回への反映

終了の直接原因は呼出し側の600秒上限である。上流の回答がこの時間を超えた理由は未確認で、入力89,959 bytesの大きさが原因だとは断定しない。stderrは空で、取得できた原文を修復・補完して完成した回答に見せない。今回の一回という範囲を守り、再送はしていない。

次にレビューが必要な変更が生じた場合は、差分と判断に必要なソースに絞り、受信完了・必要な節の有無を確認してから完了扱いにする。今回の受信欠落を未確認事項の合格へ置き換えない。追加レビューを一律の新しい実装gateにはしない。

controllerとしては、受信した具体的な問題を修正した**将来設計の引継ぎ候補**として整理した。SWEの全文未取得という制約を含めて渡し、実装時の正式な採否は開発側の最新の案件判断へ結び付ける。
