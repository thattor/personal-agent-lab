# 次版マルチモーダル: 設計準備の最終引継ぎ

2026-10-08。現行版はテキストをゴールにし、マルチモーダルの正式採用は次版とする本人の直接指示に基づく。設計資料、レビュー、接続計画、GitHub用本文をまとめた。**実装は未着手、製品30ケースは全てNOT_RUN。**

- 方針・段階・完了条件: [BRIDGE-PLAN.md](BRIDGE-PLAN.md)
- 本人指示の出典: [OWNER-INSTRUCTION.md](OWNER-INSTRUCTION.md)
- v1へ追加する正確な契約: [CONTRACT-ADDENDUM.md](CONTRACT-ADDENDUM.md)
- レビュー原文と採否: [REVIEW-DISPOSITION.md](REVIEW-DISPOSITION.md)、`reviews/`
- 実在GitHubの事前確認と登録本文: [github-before.json](github-before.json)、[ISSUE-DRAFTS.json](ISSUE-DRAFTS.json)
- 30ケースの割当・原文完結・現行製品hash照合: [VALIDATION.json](VALIDATION.json)
- 受渡し時の転記訂正と再発防止: [HANDOFF-CORRECTION.md](HANDOFF-CORRECTION.md)

SWEの元の不完全回答は既存 `design-v1/` に保存済み。今回の全文再送は本文未受信で上限終了し、`reviews/swe-attempt1/` に記録した。その後、修正契約へ確認対象を絞った公式SWE-2 High Freeレビューは62.452秒で完結。旧B1/B2/ノート9を解消確認し、追加指摘を補足へ反映した。これは省略部分の全面再監査ではない。Opusの計画レビューは34.233秒で完結し、明確化3点を採否付きで反映した。修正後の追加モデル再レビューは行っていない。

## PAL開発への依頼

共有repo/GitHubの唯一のwriterとして、manifestを確認して本資料を `evidence/research/multimodal/2026-10-08/bridge-v2/` へ保存し、入口 `docs/design/multimodal-next-bridge-v2.md` と既存v1入口・STATE・DECISIONS・Issue #6から参照できるようにする。原レビューの履歴や旧NOT_RUNを上書きしない。

`ISSUE-DRAFTS.json`の1 milestone・親+MM0–4の計6 Issueを同目的の重複がないことを確認して登録し、依存は実在番号/URLへ置換する。MM1–4と親はDEFERRED、期限なし。P001v2や既存将来milestoneを採用・変更しない。現在のStable-1/N1へ追加gateを入れない。実装PRは今回作らない。

MM0は両レビューの終端・全指摘の採否、保存commit、実在GitHub readbackを確認した時点で閉じられる。レビューの原文・設計を読んで完了基準へ対応付けるだけでよく、同じ入力でレビューや製品試験を反復しない。採用は次版設計・準備の範囲だけで、製品実装/機材導入/モデル接続の開始ではない。現在のテキスト版の開発を継続する。

人間判断が必要な新しい事実・権限は今回の準備で発生していない。既に回答された現行テキスト/次版方針を再質問しない。将来、対象端末、追加費用/権限、本人総合有用性が実際の依存になったときだけPAL人間判断へ具体的に渡す。

## 記録の読み方

`registration-stage/` は最終SWE回答前に渡した中間snapshotで、`MM0 IN_PROGRESS`という当時の状態を保持している。現在の採否はこのREADMEと最終BRIDGE-PLAN/REVIEW-DISPOSITIONを参照する。中間版を現在判断にしない。

`prepare-review.py`、`run-*-review.py`、`run-swe-compact.py`は今回の入力生成/実行の記録用ソースで、実行済み条件や端末固有pathを含む。新しいレビューを許可する自動実行手順ではない。特に既存認証・Free/Pro・追加利用OFFの証拠は今回だけの観測で、将来は新たな本人範囲と直前確認が必要。アカウント値を含む一時configはプロセス終了時に削除され、ここへ保存していない。不要なCLIアカウント表示だけを明示してマスクした。

`MANIFEST.json`はこの最終packetの各fileのhash/size。repo保存とGitHub登録の結果はPAL開発が別のreadbackに記録する。manifestだけで保存完了や製品完成を主張しない。
