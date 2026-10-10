# PAL v5 selected contract excerpts

Source: private thattor/personal-agent-lab, baseline02ff5a6156f6511bd7cff5a8155f1a703123a253. v5 is a candidate; bounded preparation only.

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


### C02 候補・現在状態の照会（TSK-01）
入力：{session_id,query?:str,goal_ids?:[str],limit:int}。
出力：{works:[{work_ref,brief_summary,expert_id,state,open_questions:[{id,text,revision}]}]}。
get_work入力：{goal_id,revision?}→{work_ref,brief,grant,state,current_artifact_refs,open_questions}。VERはこの窓口から固定条件と現行成果物集合を読む。過去revisionの読出しは履歴であり現行完了には使えない。
読取り専用。別セッションの仕事も本人の同一アカウント内で検索できる。候補からの意味選択はPrimary、ID/版の有効性はTSKが確認。候補なしと曖昧を混同しない。

### C03 作成・継続入力の結合（TSK-01）
create入力：{key,session_id,origin_record_ref,brief:DraftBrief}。
出力：{work_ref,expert_id,state:queued,grant}。仕事・条件・grant・入力参照を一度保存し、通知も同じトランザクションで作る。
attach入力：{key,work_ref,session_id,record_ref}。
出力：現在のWorkRefとstate。attachは本人入力なのでgoal_id/revisionを照合しepochを無視する。追加発言を元仕事へ結び付けるだけで停止を解除しない。目的変更や質問回答はC10で明示する。実行中に新発言をattachした場合はepochを無効化し、現行の一手が終了してから新入力付きで再評価する。黙って既に走っているモデル入力へ適用済みとしない。running以外のattachは状態を変更せず次のclaimへpending_inputsとして渡す。waiting_inputで回答ではない発言は待機を維持する。終端の継続依頼は新しい仕事へ渡す。


### C14 表示と通知（TSK→PRI/UI）
入力：{session_id,after_event_id?:str}。
出力：{events:[{event_id,work_ref?:WorkRef,kind:accepted|progress|question|state|result|error,text,refs:[Ref]}],next_cursor}。
TSK.append_event{key,session_id,work_ref?:WorkRef,kind,text,refs}→{event_id}をホスト向けに提供する。work_refは雑談・記憶操作では省略可。PRIのTurn確定とC05記憶変更は各所有者が同じ共有トランザクション内でappend_eventを呼ぶ。質問の一手はC04で確定するので二重finish_stepをしない。report/lookup等はC13.finish_stepで通知と一手を確定する。イベントは関連する状態更新と同じトランザクションで保存。UIはevent_idで重複を除く。再接続で取得し直せる。外部pushや定期起動は不要。状態バッジはTSKの値、文章はモデルの説明で、文章が状態を上書きしない。

