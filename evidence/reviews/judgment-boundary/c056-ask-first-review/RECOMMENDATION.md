# 明示された事前確認を保持する最小修正の相談

対象: `46bd418c9e5ed96d2c17fd0b7ec1808f7fc89ffc` / product53a616、現行Stable-1 N1-09/10。共有repo/GitHubは変更していない。開発による固定入力UI-CLARIFYの初回FAILを扱い、本人の入力や有用性評価とは称さない。

## 結論

公式Opusは、Primaryのdraft-clarification段落へ明示的な事前確認条件の優先順位を加える最小案を推奨した。既存のモデル解釈・host検証・状態・schema・予算・UI契約を維持する範囲で採用候補とする。正式な採否・実装・正本更新はPAL開発が行う。新しい人間判断は不要。

原文は [opus-response.txt](opus-response.txt)。既存公式Pro認証と追加利用OFFを直前確認し、ツール/MCPなし・1turn・240秒上限・1callだけで実行。33.236秒、exit0、4,036 bytes、stderr0、末尾REVIEW_COMPLETE。失敗再試行・fallbackなし。レビューの成功は製品の合格ではない。

## 観測と原因の範囲

実際のPrimary specは「日付・開始時刻・場所は私に確認してから使う」を「明示的な空欄プレースホルダーのまま」に書き換えていた。質問をせずGoalが作られ、成果物が完成した。710 bytesとhash/receiptは一致するが、意味の条件はFAIL。根拠のない「もうすぐ」も別の成果物誤りとして保持する。Primaryの修正だけでその時期表現まで直るとは主張しない。

一般的な下書きの即時作成を促す現在の段落と、明示的な事前確認の優先順位不足は、実記録に整合する寄与原因候補。単一runからsamplingやモデル能力との因果は確定しない。旧FAILの再ラベル・同candidateのresampleは行わない。旧ABS-A2には一切触れない。

## 採否と最小の文言調整

Opusの挿入場所は `For an actual local draft request, use available context and memory first.` の直後。他のC038/C040/C042規則、native/Expert、decoder、Store、harnessをこの根拠だけで変えない。

採用候補は、明示的な「先に確認」を一般文や空欄に変換しない、未解決事項だけ一つにまとめて聞く、文脈の既知情報と明示blank templateを保持するという方針。原文の2点をcontrollerとして明確化する。

1. **既知内容の明示再確認**: 「既知なら再質問不要」と「既知の値でも再確認してから使え」という本人指定を区別する。後者では、既知の値を示して一つの確認を返す。原文の`only the still-missing named details`だけでは、この場合の質問対象が空になる可能性がある。
2. **回答後の継続**: 原文の`and asking to proceed`を、追加の明示的な着手承認を常に要求する条件として採らない。元の依頼がその確認だけを前提に委任され、後続回答が前提を満たし、別の取消し・制限がなければ、通常の現在意図の解釈で続ける。単なる日付等の回答を受けて改めて「作ってよいか」と聞く必要はない。本人が回答と同時に範囲を変えた場合は、既存の現在意図優先規則に従う。

上記を反映した挿入文候補（追加モデル再レビューはしていない）:

```text
An explicit user condition to confirm named details before using them takes priority over drafting with general wording or placeholders; do not replace that condition with blanks or unspecified details. Use available context to resolve those details without asking for known facts again, unless the user explicitly requires reconfirmation. If reconfirmation is explicitly required, use none and one grouped question presenting the known values for confirmation. Otherwise, if any named details remain missing, use none and one natural grouped question for only those details. While that condition is unresolved, do not draft, start or promise the work. When a later answer satisfies the condition, continue the original authorized request under the user's current intent without asking again for permission or already-known facts. Merely unspecified details do not create such a condition, and a requested blank template keeps its placeholders.
```

これは自然文の意味解釈をモデルへ与える規則であり、キーワード分岐や新しい承認stateを作る提案ではない。引用中の確認指示は引用内容として扱い、record-only/not-yet等の制限と利用不能な行為を含む複合依頼の既存規則を優先する。

## 回帰と有限再検証

凍結済みUI-CLARIFYを新candidateの別runで1回。入力2件、3slots、費用条件・通常browser/receipt観測・stop条件を維持する。第2入力は期待するまとめた質問が得られた後だけ1回送る。旧FAIL、未使用の1slot、旧DB/hostの証拠を引き継いで再利用しない。

Opusが再検証の初回を「Primary質問、Goal0」とした点は、この修正の期待する経路として扱う。**元の受入契約はPrimary pre-Goal質問とpersisted Expert質問の双方を許容するので、そのoracleをPrimary限定に変更しない。** 各経路の既存の束縛、1Goal、cap3、回答前に成果物を完成しない条件を守る。Primary質問の有無はreply本文で見る。`questions`の行数0だけでは質問なしと判定しない。

成果物では指定した日付・時刻・場所、捏造しない条件、時期表現を実際の本文で独立に確認する。hostのbytes/hash PASSを意味のPASSへ転用しない。

局所的な構造/契約テストでは、挿入位置と既存指示の保持、none/後続回答の通常経路、重複・sourceの保護を確認する。mockや指示文字列assertだけでモデルの意味理解を合格にしない。回帰の対象は、通常generic draft、既知文脈、明示blank template、引用/record-only/not-yet、不能行為との複合依頼、明示事前確認、既知値の明示再確認、回答後の重複Goal/不要な再質問。

Primaryの製品指示が変わるため、既存fixed40/独立12の以前の結果は旧候補の証拠として保持する。今回のUI1件だけで新candidateのN1-01/02や受入全体をPASSにせず、開発が既存の凍結契約・許可済み有限予算に従って変更の影響を再検証する。新しい無制限回数や評価条件は作らない。FAILなら原文と状態を保存して原因を再評価し、同場での反復や条件緩和をしない。

## 保存と次の作業

この一時packetをprivate repoの既存judgment-boundaryレビュー記録へ保存し、本人の既存案件判断正本から採否と根拠に到達できるようにする。保存先/commit/hashを返す。PAL開発が採否を記録してから最小修正へ進む。設計chatは共有コード・正本・GitHubを並行編集しない。
