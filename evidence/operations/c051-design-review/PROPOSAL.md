# C051 ブラウザー観測の最小代替案

対象は main `2abe33909b5a8a8a63cf62f2be18e97eaa049a75` / product53a616。設計相談のみ。共有コード・正本・Git・DBを変更せず、fixtureや新harnessも生成・実行していない。Support送信を進めないという本人回答を確認した。

## 提案

**A0を先に完了し、接続できた場合だけAの小さな経路診断を行う。Bは現時点で保留する。受入条件の変更や新しい本人判断は今は不要。**

1. 開発側で既に依頼したHR-ACCESS-005の実際の応答・表示変化を待つ。本人はPAL開発を表示し、通常のbrowser paneで公開説明ページを開くだけ。可否や設定値を重ねて質問しない。変化後に正規inventoryと対象tabの実URL/表示を一度確認する。`queued`は契約上の表示時open待ちであり、今回表示済みか、未接続の原因がhiddenかは未確認。IABが引き続き無ければ、fixtureもproductも起動しない。
2. IABが利用可能なら、事前に固定した一回のknown fixtureでtop-level HTML、同一tabのリンク、new-tabのリンクを確認する。短い公開済み固定文字列のみ、単一loopback host、静的route allowlist、有限時間、provider/旧DB/既存artifact参照なし。製品と同じ種類の安全header/link属性を比較に使っても、旧artifactのroute/id/bodyは使わない。最初の拒否・新しい許可要求・想定外転送で全体を止め、port・header・browser等を変更して再試行しない。採用・実装の具体化は開発側が行う。
3. 成功時に証明できるのは、その時点のfixtureと固定した各navigationの成立だけ。陽性のaccess記録はfixtureへのrequest到達の証拠。記録が無いことだけで送信前blockと断定しない。元ABS-A2の原因、許可解除、PAL実成果物の表示、N1合格は証明しない。header/target変更の製品patchの根拠にもならない。
4. 未実行9件は、別の未実行sampleとして残っている。正式な接続・通常のアクセス許可が成立し、開発側が現行契約と出力先を確認した場合だけ、既存の順序・独立cap・最初の失敗で停止する規則を維持して初回実行する候補になる。fixture成功だけを包括的なアクセス許可にしない。A0/Aはprovider proof取得前に済ませ、診断で900秒/600秒の枠を消費しない。元ABS-A2はNOT_VERIFIEDを保持し、取得・再実行・別sampleでの置換はしない。
5. 9件はCREATIVE-PARTICULARS、SUPPLIED-FOLLOWUP、ABS-B1/B2、ABS-C1/C2、UI-CLARIFY、TARGET-C、COMPOUND-LOCAL-CONTINUATION。ABS-A2は含まれない。原契約は必要な有限sample/probe全部の確認を要求するため、9件を終えても元の未検証sampleは埋まらない。N1-05/06/09/10の残り、N1-07本人総合評価、N1-08最終監査を合格へ繰り上げない。

## Opus原文との照合

公式Opusを一回、ツール/MCPなし・1turn・240秒上限で実行。既存公式Pro認証、使用クレジットOFF、自動再読み込みOFFを直前確認。71.460秒、exit0、回答6,199 bytes、stderr0、完了。新しい認証・課金・fallback・SWE呼出しなし。原文は `opus-response.txt`、固定質問は `question.txt`、確認と終了は `access.json` / `completion.json`。

- A0先行、fixtureの限定的価値、未実行9件と元ABS-A2の区別、Bの証拠同等性未立証は採用候補。
- 「Aは独立診断ではない」は狭める。拒否内容を一切使わない別の診断であることと、元障害の原因を特定できないことは別。固定matrixだけで権限や非迂回性が保証されるわけではない。
- `claim_limits[0]` はcontroller実行を本人入力・有用性評価等と称さないという主張の上限であり、本人の観測参加の全面禁止ではない。Bを保留する根拠に、その誤読は使わない。
- 別の観測者や別のbytes取得者という事実だけで証拠水準低下とは断定できない。同じ実UI/実出力/Goal/Attempt/revision/epoch/manifest/receiptへの対応と許可された取得が必要。現時点ではその具体的な同等性と許可経路がないためBは実行しない。将来同等性を満たす方法の選択は技術判断であり、自動的な本人承認gateを作らない。実UI義務の削除や未検証sampleの免除など実質的な受入緩和なら別の本人判断になるが、今その変更を提案していない。
- 「恒久的に未知」は採らない。原因・当時の到達有無は現時点でunknown。`queued`の契約上の意味は既知で、実表示が未確認。Opus質問の固定後にHR005送信済みの連絡を受けたので、原文の新たな可否確認も追加しない。
- 原文でunknownとされた9件の範囲は、契約のhostsとC045実績を照合して上記に特定した。原文を改変・補完してレビュー済みの回答に見せない。再相談は行っていない。

## 禁止事項と引継ぎ

拒否されたartifactを別browser/URL/DB/ファイル/本人中継で読むこと、旧hostの再開、chrome://policy/native設定/CDPによる迂回、許可・認証・課金・定期実行の変更、resampling、元ABS-A2を他の成功で置換することは禁止のまま。今回Chromeで開いたのは公式Claude利用状況だけで、PALへのChrome接続はしていない。確認用tabは閉じた。

資料はこのチャットのtool出力から開発側へ渡す。正本への採否記録とprivate repositoryへの保存は開発側が担当する。追加の本人質問や共有repoへの並行書込みは不要。

出典: 現行ACCEPTANCE.md、expert-commitment-ui-contract.json、C045 README、C049/C050記録、C051の開発側tool報告、確認済み本人回答。公式資料は https://learn.chatgpt.com/docs/browser と https://help.openai.com/en/articles/20001277-using-the-built-in-browser-in-the-chatgpt-desktop-app 。公式資料はlocal preview/通常操作と管理制限を説明するが、当該環境の実効許可や元block解除を証明しない。
