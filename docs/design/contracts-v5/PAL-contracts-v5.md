# PAL 接続仕様・実装分担 v5

2026-10-09。設計専用のレビュー候補。v3のOpus 5.5再レビューとv4の接続照合を反映。v1/v2を統合し、この文書だけで接続の意味が読める形にした。旧版の追記による上書き規則は使用しない。製品実装・正本更新・GitHub更新はしていない。本人による計画確認後、別の開発チャットで実装する。

## 1. 目的と範囲

仕事を頼むと、必要な情報を探し、Expertが仕事を進め、結果を返す。同じ仕事に対して途中で止める・続ける・変えることができる。本人の背景説明・手順指示・進捗管理の負担を減らす。
モジュラーモノリス、コントラクトファースト、小さな単機能の開発単位、並列実装。会話や作文の品質はモデルに任せる。既存コード・DB・APIへの後方互換は不要。合う実装は再利用し、新規が簡単なら新規に作る。旧履歴・成果を削除する指示ではない。
最初の実接続案は指定GitHub repositoryの読取り。書込み・追加認証・追加費用・公開を含めない。GitHub限定は最初のコネクターの範囲で、PAL全体を開発Issue要約専用にするものではない。

## 2. モジュールと唯一の所有者

| ID | 責務 | 担当しないこと | 所有データ・提供契約 |
|---|---|---|---|
| PRI-01 | 発言の意味を解釈し、返答と一つの意図案を返す | 実操作・直接状態変更・独自の文体採点 | C01、UI受付と表示 |
| PRI-02 | 候補の中から新規/継続/回答/制御の対象を結び付ける | 曖昧な時の最新仕事への決め打ち | C02利用、選択はPRI-01と同じ推論で可 |
| PRI-03 | 目的・制約・参照を仕事受付へ渡す | 再度の意図推論、工程計画 | C03利用 |
| PRI-04 | 質問・進捗・結果を本人へ返す | 独自の完了判定 | C14利用、言換え推論は必須でない |
| EXP-01 | 仕事の次の一手を選ぶ | ID発行、DB変更、実行ループ | C12の行動案 |
| EXP-02 | 不足情報を調べ、必要な質問を組み立てる | 既知の情報の再質問 | EXP-01のlookup/askを支援する内部機能 |
| EXP-03 | 参照した情報から成果物候補を作る | 実保存、外部操作 | C12 composeの内容生成 |
| EXE-01 | 許可を確認し、操作を受付・実行・記録する | 仕事の計画 | 操作台帳・実観測・取得本文。C07/C11 |
| EXE-02 | GitHubの指定情報を読む | 任意shell、書込み、別repo | EXE-01からだけ呼ぶ固定adapter |
| VER-01 | 固定された条件に照らして達成を確認 | 文体採点、仕事状態変更 | 検証記録。C09/C11 |
| MEM-01 | 会話原記録を保存する | 要約で原文を置換 | 原記録。C05/C11 |
| MEM-02 | 出典付きの記憶・要約を作り更新する | 推測を本人の事実にする、自動モデル訓練 | 記憶・要約。C05 |
| MEM-03 | 関連要約と原記録を検索する | 無制限な全履歴投入 | C06 |
| MEM-04 | 訂正と参照停止を適用する | 原記録の物理削除 | 出典の利用可否。C05/C11 |
| TSK-01 | 仕事・セッション・担当を対応付ける | 意味解釈、モデル呼出し | 仕事brief、grant、関連セッション。C02/C03 |
| TSK-02 | 仕事の状態・実行権を変更する | 意味の達成判定 | 状態・epoch・制御。C04/C10/C13 |
| TSK-03 | 進行記録と再開位置を保つ | 外部本文やreceiptを重複保管 | step記録・通知。C13/C14 |
| ART-01 | 成果物を保存し読み出す | 作文・達成判定 | 内容・版・hash。C08/C11 |
| RUN-01 | Expertを一手ずつ呼び各機能へ渡す | 仕事の意味を決定する、独自の状態機械 | C12/C13を利用。永続データは所有しない |

モデル呼出し口MOD-01とDB接続/トランザクションは小さな共有基盤。MODは指定済みモデルと既存承認範囲・有限利用上限を守る。モジュールごとにプロセスやモデルを増やさない。Primary/Expertの製品用モデル選択は設定で行い、レビュー用Opus 5.5を製品の必須モデルへ転用しない。

## 3. 型・権限・参照の共通定義

以下は実装言語に依存しない契約表記。str/int/boolは厳密な型、?は省略可、[]は配列。IDは空でない不透明文字列。モデルはホストが入力に渡した参照だけを選べる。新しいIDや権限は生成しない。

- WorkRef = {goal_id:str, revision:int>=1, epoch:int>=0}。
- Ref = {kind:record|note|source|receipt|artifact|verification, id:str}。IDは不変版を指す。可変のURLは参照の正本にしない。
- DraftCondition = {description:str,check:semantic|artifact_saved|source_fetched}。DraftBriefはBriefと同じ項目だがconditionsは[DraftCondition]。モデルはDraftBrief、TSKが正式Condition IDを付けたBriefを保存する。
- Brief = {purpose:str,target:{repository:str,issue_numbers:[int],files:[{path:str,ref:str}]},constraints:[str],conditions:[Condition],context_refs:[Ref]}。
- Condition = {id:str,description:str,check:semantic|artifact_saved|source_fetched}。正式IDは受付時にTSKが付ける。条件配列は空不可。意味判定の条件文を決定論的に品質保証する設計は置かないが、依頼より権限を広げる提案は拒否する。意味は依頼からモデルが提案し、本人に条件票の入力を要求しない。
- Grant = {capabilities:[str],repositories:[str],limits:{max_operations:int,max_steps:int,max_model_calls:int}}。ホスト設定と依頼制約の共通範囲。変更で拡大しない。
- Result<T> = {ok:true,value:T} または {ok:false,error:{code:str,message:str,refs:[Ref]}}。codeはinvalid_input/not_found/ambiguous/stale/denied/unavailable/limit/conflict。操作を開始した後の失敗はC07のOperationで返す。
- 設計版は全担当でv5に固定。実装中の変更は提供側・利用側・契約例を一緒に更新する。旧版の互換コードを必須にしない。
- client_keyはUIが送信ごとに保持する再送キー。原記録IDはMEMが生成。構造化ボタンはclient_keyを使う。内部keyはホストがrecord_id又はstep_idとコマンド種別から生成。外部readの再取得はretry_index(初回0、再取得1)も含める。同じkey＋同じ正規化入力は保存結果を返し、違う入力はconflict。

全ての状態変更は現在の状態と期待対象を同一DBトランザクション内で照合する。C10の本人操作はgoal_idとrevisionを照合し、epochだけが進んでも拒否しない。別revisionになった場合は更新された対象を表示して再解釈する。ホスト実行結果(C04/C07/C08/C09/C13/complete)はrevisionとepochの両方を照合する。DBトランザクション中にモデルや外部I/Oを待たない。単一ユーザー・単一実行プロセス/枠から開始し、別プロセスの同時起動は起動ロックで拒否する。

## 4. 接続契約

### C01 発言→意図案（PRI）

受付の公開口：submit{client_key,session_id,text}→{turn_id,status:pending|committed|failed|interrupted}、get_turn{turn_id}→{status,reply?,effect_refs:[Ref],error?}。PRIがTurn台帳を所有し、C05の原記録・入力内容hash・入力snapshot・モデルcall_id・提案適用結果を結ぶ。単一入口内で同じclient_keyの二重モデル呼出しを防ぐ。
内部推論入力：{record_ref,session_id,candidates:C02結果,context:{summaries:C06.summaries,records:[C11本文結果]}}。原文はrecord_refをC11で読出して必ず含める。
出力：{reply:str,proposal}。proposalはnone / new_work{brief:DraftBrief} / continue{work_ref,record_ref} / answer{work_ref,question_id,record_ref} / control{work_ref,command} / memory{operation}。
意味解釈とbrief作成は一回のモデル呼出しでよい。UIは最初にC05で原文を保存し、ホストが提案の対象・出典を確認してC03/C05/C10へ渡す。効果は保存後に通知する。効果適用keyはturn_idから導出し、受付結果の保存前に落ちても同keyで既存効果を回収する。全提案のget_by_keyを提供者が持つ。モデル回答文を未確定の効果として先に表示しない。構造化ボタンの停止等は推論を待たずC10へ渡す。
モデル失敗はエラー表示し、推測操作を行わない。同じclient_keyの再送で推論を二重起動しない。未確定のまま再起動した入力は中断表示し、勝手に再推論しない。

### C02 候補・現在状態の照会（TSK-01）
入力：{session_id,query?:str,goal_ids?:[str],limit:int}。
出力：{works:[{work_ref,brief_summary,expert_id,state,open_questions:[{id,text,revision}]}]}。
get_work入力：{goal_id,revision?}→{work_ref,brief,grant,state,current_artifact_refs,open_questions}。VERはこの窓口から固定条件と現行成果物集合を読む。過去revisionの読出しは履歴であり現行完了には使えない。
CHANGE01/1では、旧revisionのstateは履歴専用のsuperseded、open_questionsは空とする。最新revisionの状態領域にはsupersededを加えない。回答済み・閉鎖済み質問、旧成果物・Step・受付結果は履歴に残し、旧C04/C10再送の保存応答を最新状態へ書き換えない。
読取り専用。別セッションの仕事も本人の同一アカウント内で検索できる。候補からの意味選択はPrimary、ID/版の有効性はTSKが確認。候補なしと曖昧を混同しない。

### C03 作成・継続入力の結合（TSK-01）
create入力：{key,session_id,origin_record_ref,brief:DraftBrief}。
出力：{work_ref,expert_id,state:queued,grant}。仕事・条件・grant・入力参照を一度保存し、通知も同じトランザクションで作る。
attach入力：{key,work_ref,session_id,record_ref}。
出力：現在のWorkRefとstate。attachは本人入力なのでgoal_id/revisionを照合しepochを無視する。追加発言を元仕事へ結び付けるだけで停止を解除しない。目的変更や質問回答はC10で明示する。実行中に新発言をattachした場合はepochを無効化し、現行の一手が終了してから新入力付きで再評価する。黙って既に走っているモデル入力へ適用済みとしない。running以外のattachは状態を変更せず次のclaimへpending_inputsとして渡す。waiting_inputで回答ではない発言は待機を維持する。終端の継続依頼は新しい仕事へ渡す。

### C04 質問の保存（TSK-02）
入力：{key,work_ref,step_id,question:str,missing_fact:str,source_refs:[Ref]}。
出力：{question_id,state:waiting_input,work_ref}。一つの仕事に未回答質問は一つ。複数の不足は一つの質問にまとめてよい。質問本文・版・参照・待機状態・step結果を同一トランザクションで保存する。
回答はC10.answerへ。get_question_by_key(key)で保存済み質問/一手を照会できる。
質問前にMEMと許可範囲の情報を調べるかはExpertの意味判断であり、固定回数の探索を義務にしない。

### C05 会話・記憶の変更（MEM）
append入力：{client_key,session_id,role:user|assistant,text:str}→{record_ref}。ホスト時刻と順番を保存し、秘密除去は既存方針を適用する。
remember入力：{key,text,source_refs:[Ref]}→{note_ref}。派生要約には必ず出典を持つ。本人原文とモデルの推測を区別する。
correct入力：{key,old_ref,new_record_ref}→{replacement_ref,affected_refs}。
stop_reference入力：{key,source_ref}→{affected_refs}。
correct/stop_referenceは派生noteの利用可否も同じ処理で更新する。RUN/ART/VERが現在利用している出典に当たれば、共有トランザクション内でTSKの公開窓口から実行権・検証を無効化する。TSKは仕事の利用出典集合を所有し、briefの出典と各stepへ渡す出典、採用した成果物・観測のsource_refsを記録する。モデル呼出し前に依存参照を登録し利用可否を再確認する。MEMは派生noteを含むaffected_refsをTSK.invalidate_by_refsへ渡す。runningはepoch無効化とdrainingを経てqueued、queuedは再評価、pausedは維持、waiting_inputは質問の出典も確認して必要なら旧質問を閉じqueuedへ。completed等の履歴状態は遡って書き換えず、成果物の出典利用停止を表示する。C11とcompleteでも現在の利用可否を確認する。原本文を他モジュールに複製してこの確認を逃れない。外部送信済みのモデル入力を取り消せるとは約束せず、以後の入力と結果採用に適用する。

### C06 関連情報の取得（MEM-03）
入力：{query:str,session_id,work_ref?:WorkRef,limit:int}。
出力：{summaries:[{ref,text,source_refs}],record_refs:[Ref],truncated:bool}。
最初に小さな関連要約を返し、必要な原本文はC11で取得する。初版は直近記録＋検索索引で候補を作り、必要ならモデルが候補を選ぶ。日本語の検索方式は代表的な固有名・言い換えの例で選ぶ技術判断。高度なベクトル基盤を前提にしない。取得なしは空配列、利用停止は除外する。

### C07 外部操作（EXE-01）
prepare入力：{key,work_ref,step_id,capability:str,arguments:object,source_refs:[Ref]}。
出力：Operation。Operation = {operation_id,work_ref,step_id,status:prepared|running|succeeded|failed|unknown,data_refs:[Ref],receipt_ref:Ref?,error:str?}。
prepareは現行状態/grantを確認し、ホストIDで操作意図を保存する。execute入力は{operation_id}のみ。実行開始時に再確認し、runningを確定してから外部I/Oを行う。同じIDを二度実行しない。get入力{operation_id}は保存済みOperationを返す。
取得本文・receipt・Operation結果はEXEが一緒に保存する。停止/変更後でも実際に得た観測は台帳へ保存できるが、TSKの現行step成果へは採用しない。
EXE-01→EXE-02の内部契約：read{operation_id,capability,arguments,timeout_seconds,max_bytes}→{status:succeeded|failed|unknown,body?,media_type?,locator?,observed_at?,version?,error?}。EXE-01が権限と予約を確認してから渡す。EXE-02はIDやreceiptを発行せず、EXE-01が内容hash・source/receipt参照を付けて保存する。
初版capabilityはgithub.issue.read{repository,number}、github.file.read{repository,path,ref}。repositoryはthattor/personal-agent-labのみ。fileは実取得commit SHA、issueは取得日時・更新日時・本文hashを保存する。指定ref/pathは入力を検証し、固定API又は固定argvの既存公式CLIで読む。文字列をshellコードとして実行しない。
初期上限案：1操作30秒、本文1MiB、仕事全体10操作。EXE.recoverは所有していた呼出しの終了を確認してからrunningをunknownにする。preparedは未実行なので同じoperation_idを一度executeできる。起動ロック取得だけでCLI子プロセスの終了証明とせず、ホストが所有子を終了・回収する。終了を確認できなければ対象操作は保留し理由を表示する。readだけなので、失敗/不明時は先行呼出し終了確認後にretry_indexを増やした新key/new operationとして1回まで再取得可。仕事全体上限にも数える。自動再試行不可の書込みは初版にない。

### C08 成果物保存（ART-01）
入力：{key,work_ref,step_id,content:str,media_type:text/plain|text/markdown,source_refs:[Ref]}。
出力：{artifact_ref,hash:str,bytes:int}。
ARTは現行WorkRefと出典可用性をトランザクション内で確認して不変内容を保存する。同じkeyは同じ参照を返す。差替えは新artifact_id。保存しただけで仕事完了にしない。保存後のstep結合で落ちてもkeyで同じ結果を取得して復旧できる。最大本文は初版1MiB、超過はlimit。

### C09 達成確認（VER-01）
入力：{key,work_ref,artifact_refs:[Ref]}。
出力：{verification_ref,checks:[{condition_id,status:met|unmet|unknown,reason,evidence_refs:[Ref]}]}。
TSKから当該revisionの固定条件を読み、C11で本文・観測を読む。保存/存在/hash/出典/実操作はコードで確認し、意味条件だけ別モデル呼出しで評価する。Expertの成功宣言を証拠にしない。モデルが返す参照は入力集合内だけ許可する。VERが判定を保存し、その際も現行版・出典を再確認する。変更ならstale。モデル利用不可ならunknownを返し、成功にはしない。
get_verification{verification_ref}→{work_ref,artifact_refs,checks,source_refs,status:valid|invalidated}をVERが提供する。C10は共有トランザクション内でこの保存結果を読む。
条件を緩めたり自分で仕事完了を設定しない。検証対象artifactの集合と条件revisionを記録する。RUNはC13.finish_stepで成果物をTSKの現行artifact集合へ結び付ける。新成果物の結合は過去の検証を失効させる。同じrevisionで成果物を更新した後は前の判定を完了に使えない。

### C10 状態・回答・変更（TSK-02）
入力：{key,work_ref,command}。commandはpause / resume / cancel / answer{question_id,answer_record_ref} / change{brief:DraftBrief,origin_record_ref} / complete{verification_ref}。
出力：{work_ref,state,control_status:none|pause_requested|draining,open_question_id?,reason?}。
answerは質問/版/原回答の可用性を照合し、回答結合と質問解消を一度で保存する。回答済み再送は同じ結果。paused中は回答を保存するだけでpausedを維持し、resumeでqueuedへ戻る。
changeは新briefをそのまま無条件に信頼せず、元依頼と差分・既存grant範囲を確認する。条件を変える場合も新revisionで明示する。旧質問はsuperseded、旧artifact/verificationは履歴になる。取得事実は対象・鮮度・参照可否を再確認して再利用できる。
CHANGE01/1の閉じた入力・grant交差・出典義務・原記録重複・履歴・lease解放は[固定スコープ](CHANGE01-SCOPE.md)に従う。公開APIはcontrol(request)のまま。信頼されたホストが保存済み修正原文を結び、導出・再利用した全記録をcontext_refsへ含める。TSKは意味の権限判断を代行しない。新grantは最新の既存grantと現在のホスト上限の交差であり、Goal/host予算をリセットしない。
completeはVERの保存結果を読み、全必須条件met、現在のWorkRef、現行artifact集合、出典可用性を一つのトランザクションで照合する。照合中に変更があればstale、未達ならconflict。Expertが渡す任意判定JSONは受け付けない。

### C11 本文と保存結果の読出し（各所有者）
入力：{ref:Ref,purpose:model_context|verification|user_view}。
出力：{ref,content:str,media_type,hash,observed_at,version:str?,work_ref:WorkRef?,source_refs:[Ref],usable:bool}。
contentはUTF-8本文、media_typeは本文の型。receipt/verificationの表示本文はJSON文字列でもよいが、C10の状態確認は文字列を解析せずVER.get_verificationの型付き結果を読む。
kindはrecord/note→MEM、source/receipt→EXE、artifact→ART、verification→VERの公開readへ振り分ける。モデルはpurposeやアクセス権を指定しない。model_context/verificationは参照停止を拒否する。user_viewは本人UIだけが利用でき、停止済み原記録を表示できる。成果物に停止済み出典があれば履歴表示に留め、モデル入力には戻さない。参照が無ければnot_found、権限/参照停止ならdenied。

### C12 次の一手（RUN→EXP）
入力：{work_ref,brief,grant_summary,context:[C11結果],steps:[Step],remaining_budget,pending_inputs?:[{question_id,step_id,answer_record_ref}]}。
ASK01/1では、回答と質問Stepが両方この呼出しへ渡される場合だけpending_inputsへ関連を含める。空なら省略する。本文を複製せず、C11で読んだ回答と保存済みStepをIDで結ぶ。停止・除外された関連はホスト診断に保持し、モデルへ渡さない。
出力：Action = lookup{query,source_refs?:[Ref]} / operate{capability,arguments,source_refs} / ask{question,missing_fact,source_refs} / compose{content,media_type,source_refs} / verify{artifact_refs} / report{summary}。
既知のRef選択は可、正式IDの新規発行は不可。composeはEXP-03、ask/lookupはEXP-02が支援し、別モデル呼出しを必須にしない。lookupはC06で候補を取得し、指定済みsource_refs又は返った候補の原文をC11で読み、次のC12へ渡す。切詰めは明示し、読んでいない原文を読んだ扱いにしない。RUNは各ActionをMEM/EXE/TSK/ART/VERへ渡す。reportは表示候補であり完了命令ではない。検証でmetならRUNがC10.completeを呼ぶ。未達なら残予算内でExpertへ返す。

### C13 実行権・一手・復旧（TSK、ホスト専用）
claim入力：{runner_id}→{lease_id,work_ref,brief,grant,checkpoint,steps,pending_inputs}又はempty。lease_idは実行枠取得ごとにTSKが発行する。queuedを一件runningにしepochを増やす。所有枠が残る間は次をclaimしない。
begin_step入力：{key,work_ref,action}→Step。Step = {step_id,work_ref,index:int,action,status:started|finished|abandoned,result_refs:[Ref],error:str?}。現在性を確認し、モデル出力の構造と権限を検証したホストが一度保存する。C12推論前のcall_idはlease_idと次step indexからホストが確保し、begin_step前のモデル予算と中断状態を追えるようにする。begin_stepの同key再送は同じStep。
finish_step入力：{work_ref,step_id,result_refs,error?}→Step。外部I/Oから戻った結果を照合して確定。step書込み前に落ちた時はstep_idから導出したkeyでEXE/ART/VERのget_by_keyを照会して復元し、済んだ操作を再発行しない。各提供側はget_by_key(key)→保存結果又はnot_foundを提供し、keyは仕事/step/操作種別の範囲で一意とする。
release入力：{lease_id,work_ref,outcome:yield|paused|failed,reason}→保存済みstate。yieldはqueuedへ戻す。failedは予算切れ又は解消不能を理由付きで保存する。停止要求時は進行中呼出しを回収してpausedへ。現行権限を失った呼出しの結果は台帳にだけ残す。releaseは古いepochでも、現在の占有lease_idと一致し呼出し回収済みなら占有枠だけ解放できる。保存状態は最新のcancel/pause/change意図を優先し、古い要求で戻さない。異なるlease_idは拒否する。
CHANGE01/1では、新規claimは各Goalの最新queuedだけを選ぶ。保持された旧leaseは診断値を返すが旧revisionの実行権を与えない。旧leaseの解放は呼出し・予約・Stepの所有結合と終了状態を確認し、旧startedだけをabandonedにする。最新revisionのcancel、pause、その他queuedの順に確定し、応答は最新WorkRef。旧failed結果で置換後の仕事をfailedにしない。
recoverはホスト起動時だけ実行。起動ロックで旧runner不在を確認し、EXE.recoverで所有呼出しを照合してからTSKのrunningを無効化。未完了stepを照合して再開可能ならqueued、情報待ちはwaiting_input、paused/cancelledは維持する。モデル推論が中断したstepは未確定として同じ出典から再計算できるが、完了済み操作を繰り返さない。復旧で回収した旧epochの確定観測は、現revisionの目的・出典可用性・鮮度を確認して新しいstepへ参照として結合する。ARTの旧epoch保存結果も同revisionかつ有効出典ならホストが復旧採用を記録できる。VERの旧epoch判定はC10.completeへ流用せず現epochで再確認する。これは旧実行の遅延結果を無条件に採用する経路ではない。
RECOVERY01/1のmanaged in-process mock起動・回収は[固定スコープ](RECOVERY01-SCOPE.md)に従う。終了まで保持したPOSIXロックと登録済みsession/lease/claim epochの結合が揃う場合だけ、admitted/no-Stepを独立したinterruptedへ回収できる。returned/raised/not_enteredへ置換しない。started compose/operateは理由付きheldとして占有とstartupを保持し、後続のART/EXE採用なしに全C13完了とはしない。
checkpointは最後のfinished stepのindexと未解消question参照。内部思考の保存は要件にしない。

### C14 表示と通知（TSK→PRI/UI）
入力：{session_id,after_event_id?:str}。
出力：{events:[{event_id,work_ref?:WorkRef,kind:accepted|progress|question|state|result|error,text,refs:[Ref]}],next_cursor}。
TSK.append_event{key,session_id,work_ref?:WorkRef,kind,text,refs}→{event_id}をホスト向けに提供する。work_refは雑談・記憶操作では省略可。PRIのTurn確定とC05記憶変更は各所有者が同じ共有トランザクション内でappend_eventを呼ぶ。質問の一手はC04で確定するので二重finish_stepをしない。report/lookup等はC13.finish_stepで通知と一手を確定する。イベントは関連する状態更新と同じトランザクションで保存。UIはevent_idで重複を除く。再接続で取得し直せる。外部pushや定期起動は不要。状態バッジはTSKの値、文章はモデルの説明で、文章が状態を上書きしない。

### C15 モデル呼出しと予算（MOD-01）

呼出し側はPRI(C01)、RUN/EXP(C12)、VER(C09)、MEM-02の要約。入力：{call_id,reservation_id,role:primary|expert|verifier|memory,work_ref?:WorkRef,messages:[{role:system|user|assistant,text}],source_refs:[Ref],output_kind:primary_proposal|expert_action|verification|memory_summary}。
出力：{call_id,status:succeeded|failed|interrupted,content?:str,model_id:str,error?}。MODは生のモデル結果と呼出し状態を保持し、業務提案の型検証は各呼出し元が行う。同じcall_idの同入力は実行中状態又は保存結果を返す。別入力はconflict。未知のモデル・fallbackは許可しない。資格情報はmessagesへ含めない。
予算予約の唯一の入口はTSK.reserve_budget{key,work_ref?:WorkRef,kind:step|operation|model,role?}→{reservation_id,remaining}。仕事付きは仕事上限と共有ホスト上限の両方、仕事なしは共有ホスト上限を確認する。consume{reservation_id,call_or_operation_id}で一つの呼出しに束縛し、別IDへの再利用は拒否する。予約消費は失敗でも返さない。ホスト上限は運用設定として実装開始時に有限値を必須入力とし、設定なしは起動時エラー。
C07.prepareはoperation予約をEXE-01が確保してOperationへ保存し、executeは保存済み予約だけを使う。C12はRUN、C01はPRI、C09はVER、記憶要約はMEMがmodel予約を取得してMODへ渡す。上位と下位で二重予約しない。step予約はC13.begin_stepが確保する。
出典依存の登録と可用性確認はreserve前にTSK.register_sources{work_ref,refs}で行う。仕事なしの呼出しはMODがsource_refsを保存し、呼出し前/結果採用前にC11で確認する。利用停止済み結果を後からモデル入力へ再利用しない。
初版は仕事の実行枠と別にPrimaryの受付を処理できる。MODが逐次処理しかできない場合でも構造化制御はMODの待ち行列を通らず動作する。具体的なスレッド構成は担当の裁量。

## 5. 状態遷移と競合の決着

revisionは目的・対象・制約・条件の変更で増やす。epochはclaimと即時無効化(cancel/change/参照停止/復旧)で増やす。値の連続性に意味を持たせず、等値だけで現行性を照合する。
CHANGE01/1の新revision/epochは直前の最新値それぞれ+1とし、新Condition IDを発行する。旧行はsuperseded、旧制御フラグは解除し、新行が最新意図を所有する。running置換は旧leaseを保持してdraining、pause意図を引き継ぐ。参照停止はその時点の最新revisionの登録出典に作用する。旧専用出典の停止で独立した新修正を拒否せず、新修正自身の出典停止または終端確定は拒否する。既存DBの移行・復旧をこの固定スコープから推定しない。

| 操作 | 状態 | 結果 |
|---|---|---|
| claim | queued | running、新epoch |
| ask | running | waiting_input、質問と一手を確定、枠を解放 |
| answer | waiting_input | queued、同じ仕事へ回答結合 |
| pause | queued/waiting_input | paused、元の待ち理由保持 |
| pause | running | pause_requested。新しい一手/保存/検証完了を始めず、進行中呼出し終了後paused |
| answer | pausedかつ未回答質問あり | pausedのまま回答を保存 |
| resume | paused | 未回答があればwaiting_input、他はqueued |
| cancel | 非終端 | cancelled、epoch無効化。残る呼出し終了まで枠は解放しない |
| change/追加入力 | running | 旧epoch無効化、draining。呼出し終了後queuedで再解釈 |
| change | paused | 新revisionでもpausedを保持 |
| change | waiting_input/queued | 旧open質問をsuperseded履歴にし、新revisionをqueuedへ |
| complete | runningかつ停止要求なし | 保存検証が全条件metならcompleted |
| 上限/解消不能 | running | failed、理由と途中成果を保存 |
| recover | 孤立running | 旧epoch無効化、step照合、queued又は失敗理由を表示 |

操作はDBの確定順で直列化。pauseより先にcompleteが確定していれば「既に完了」。pauseが先ならcompleteは拒否する。重複操作はkeyで同じ応答。実行中の外部読取りを即座に取り消せない時も、新しい操作の開始は止める。
終端(completed/cancelled/failed)への単純resumeは拒否し理由を返す。新しい続きの依頼は元仕事参照を持つ新Goalで扱う。paused/waiting_inputの継続は必ず同じGoal。変更/追加入力でdrainingになった仕事へのpause/cancelはその場で記録し、旧呼出し終了後も最新の停止意図を優先する。

## 6. 上限と不足情報

初版技術値案：仕事全体10外部操作、20手、20モデル呼出し。予約の入出力・所有者はC15に統一する。既存provider/host上限が小さければ小さい方を使う。pause/resume、回答、再起動ではリセットしない。上限到達は途中成果と理由を返す。これらは受入の時間・入力数ノルマではない。
モデル呼出し口は、失敗・利用不可を返し、別モデル/課金経路へ自動切替しない。ここで製品用認証やモデルを新規設定しない。
必要情報が記憶から見つかれば使い、許可された探索で見つかれば使う。それでも仕事を進められない不足だけ本人へ質問する。一般的な文章品質の改善を必須質問にしない。

## 7. 接続を確かめる契約例

これは製品試験結果ではなく、各提供側・利用側が共有する期待動作。提供側がfakeを用意し、同じ例を実物にも通す。

| ケース | 呼出し | 期待結果 |
|---|---|---|
| CT-01 | 同じclient_keyで同じ発言を再送 | record/仕事/推論を二重に作らず既存結果 |
| CT-02 | 同じkeyで異なる入力 | conflict、変更なし |
| CT-03 | prepare→execute→C11→compose→C08→C09→complete | 保存成果と実観測を読め、判定IDで完了 |
| CT-04 | succeeded操作の返答前に停止・再起動 | get(operation_id)で結果回収、再実行なし |
| CT-05 | data_ref読出し | 取得本文・hash・取得時点が一致。存在しない参照はnot_found |
| CT-06 | ask→遅れてanswer | 同じGoal/質問に結合しqueued |
| CT-07 | ask→pause→answer→resume | 回答時には動かず、resume後に同じ仕事が進む |
| CT-08 | running→pauseとcompleteが競合 | DB確定順に従い、停止受付済みなのに完了させない |
| CT-09 | running→change→旧結果 | 台帳保持、現行成果には不採用。旧呼出し終了後に新revision |
| CT-10 | 間違ったGoal/旧質問へのanswer | stale/not_found、他の仕事は無変更 |
| CT-11 | 検証後に成果物差替え/出典停止→complete | 旧判定を拒否。必要な再検証へ |
| CT-12 | モデルが架空ID/成功/権限を返す | host検証で拒否、効果なし |
| CT-13 | paused/cancelled状態で再起動 | 自動再開しない |
| CT-14 | 外部readがtimeout | failed/unknown記録、先行終了確認後のみ有限再取得 |
| CT-15 | 関連する古い記憶と訂正済み/停止済み記憶 | 有効な関連原文だけモデルへ。本人履歴表示は可能 |
| CT-16 | 無関係な雑談 | 返答だけ、Goalなし |
| CT-17 | 意味判定不能/予算切れ | unknown/failedと不足、PASSにしない |
| CT-18 | UI切断後に再接続 | event_idで重複なく質問/結果を再表示 |

## 8. 並列実装と小さな統合地点

A：EXP-01〜03。B：EXE-01/02。C：MEM-01〜04。D：TSK-01〜03とRUN-01。E：PRI-01〜04。F：ART-01/VER-01。実働人数に応じて担当を兼ねるが、接続仕様は同じ。共有MODとDB接続、起動配線、契約ファイルの編集は統合担当が管理。各モジュールのテーブル/データ実装はその所有者が行う。
共有トランザクションが必要なC05出典停止とTSK無効化、C10完了とVER/ART読戻しは公開窓口にトランザクションを渡して連携する。単一SQLiteなので分散トランザクションは不要。I/Oを含まない共通結合部分だけ統合担当が直列で反映する。

| ID | 到達点 | 依存・判定 |
|---|---|---|
| INT-00 | 契約版・所有者・例を各担当で共有 | 計画確認、必要な設計レビュー後。全内部アルゴリズムの完成は不要 |
| INT-01 | 仕事受付→Expertの一手→記録 | D/A並列で作成、CT-01/02/12。完了は実接続の証明ではない |
| INT-02 | 実GitHub読取り→参照読出し | B独立着手、CT-04/05/14 |
| INT-03 | 最小UIから一件依頼→実取得→分析→保存→確認→表示 | A/B/D/E/FとCのMEM-01 appendを接続。高度な記憶検索完成まではC06は空結果を明示できる。CT-03/08/18。最初の動く一連の結果 |
| INT-04 | 関連記憶の保存・検索・訂正・参照停止 | CはINT-00後並列、CT-15。要約キャッシュもここで確認 |
| INT-05 | 必須不足の質問→回答→同じ仕事の継続 | CT-06/07/10 |
| INT-06 | 停止・再開と途中成果再利用 | CT-07/08/13 |
| INT-07 | 変更・中止・クラッシュ後の回復 | CT-04/09/11/14。基本の旧結果拒否はINT-03から含む |
| INT-08 | 全経路を実UI・モデル・実接続で統合確認 | CT-16/17を含む機能確認。作文の採点なし |
| INT-09 | 本人が仕事を任せて負担が減るか評価 | 本人の評価を記録し未達だけ修正、全PAL完成と混同しない |

各モジュールの責務・契約・証拠をレビューし、到達点ごとにOpusと全体への効果を照合する。根拠のある未達は同じ小単位で修正する。既存のSWE実装境界レビューは開発側で必要箇所に限定する。設計案の採用はコードや実接続の合格ではない。

## 9. 今回の判断と残す裁量

Opus v1レビューの「必ず矛盾・破綻する」という断定は採用しない。IDの中継や質問の非同期性は未記載であり方式違反とは限らなかった。今回、誰が何を発行し保存し再開するかを明記して、複数の実装解釈をなくした。
新たに見つけた不足：モデルへの一手の契約、表示/再接続、claim/release、停止中の回答、完了との競合、出典停止中の結果、保存後クラッシュ、予算の継続。C12〜14と状態表・CT例で補った。
各モジュール内部の関数名、検索方式、索引、既存コード採否、ファイル分割は担当の裁量。契約に影響しない内部処理まで固定しない。
この文書は設計候補。Opus 5.5がv3を再レビュー済み。v5は指摘反映後の接続照合を加えた版で、v5の独立再レビューと製品動作検証は未実施。実装開始前の本人確認地点は維持する。

## 10. v3再レビューの採否と追加確認例

公式Opus 5.5、1 turn、90.96秒、exit0、REVIEW_COMPLETE。原文はopus-v3-review/response.md、入力固定版は同ディレクトリinput-v3.md。原文評価は「重大な方式破綻はない」「v1で問題になった解釈の分岐はほぼ消えた」。実装可否は設計上の判定であり、実装を始める許可や製品合格ではない。

R-01：本人操作からepoch照合を除外。revisionは対象変更の誤適用防止のため全本人操作で保持する。epoch変動だけで停止が失敗する問題を解消し、旧仕事仕様への制御は黙って転用しない。
R-02：単純なstep result_refs照合だけでは、その参照の出典まで到達しない場合があるため、TSKに明示的な利用出典集合を持たせた。MEMが派生noteを展開する。履歴の完成状態は書き換えない。
R-03：retry_indexとEXE先行復旧を採用。起動ロックだけで旧子プロセス終了を推測しない補足を加えた。
R-04〜06：非実行中attach、参照振分け、get_work、ボタンkey、予算予約、初期統合のMEM依存を補完。Primary/記憶の仕事予算除外は共有利用上限を必ず維持して採用。

追加契約例：CT-19 同じrevisionでepochだけが更新された後のpause→受付成功。CT-20 モデル入力の出典停止→TSK利用出典集合から対象実行だけ無効化。CT-21 running操作がクラッシュ→所有呼出し終了確認→unknown→retry_index1で一度再取得。CT-22 queued/paused/waiting_inputへのattach→勝手に状態変更しない。CT-23 予算予約の同一key再送→二重消費なし、別keyは残量を消費。

v2で旧表と追記を併存させたため解釈に負担が生じた。v3以降は接続本文を直接統合し、履歴は原版に残す。次回も契約番号、提供者、利用者、結果の保存先、競合時の期待結果を合わせて確認する。


## 11. v4からの接続照合による修正

1. モデルの条件案とホスト発行Condition IDをDraftBrief/Briefへ分離。
2. MOD入出力・予算予約・二重予約防止をC15で統一。
3. 原会話や取得参照から本文を得て推論入力に渡す経路をC01/C12へ追記。
4. 古いepochでも所有枠を正しく解放するlease_idをC13へ追加。
5. C11の表示本文と完了判定用の型付き読出しを分離。
6. 通常会話・記憶操作・reportの通知保存をC14へ定義。
7. 原発言から推論・効果適用までの中断/再送の所有者をPRIのTurn台帳へ固定。
8. EXE-01/02間の結果型とreceipt発行者を明記。

設計上の接続照合は別紙CONTRACT-AUDIT-v5.mdを参照。今回の「確認済み」は文書で送り手と受け手が対応していることを指す。コードが契約通り動くこと、実接続できること、本人に価値があることは未検証。
