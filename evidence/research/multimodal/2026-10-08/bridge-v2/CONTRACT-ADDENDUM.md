# v1契約への補足 — 未完了SWEレビューの収束

この補足と元の `design-v1/DESIGN.md`、`CONTRACT-EXAMPLES.json`、`ACCEPTANCE.json` を合わせて次版の引継ぎ契約とする。元の資料は履歴として変更しない。現行版へ実装したことを意味しない。

## キーの予約と終端保存

`media_inputs`予約との競合検査は、新しい受理を検証する`_dedupe`のlookup経路と、`prepare_primary`の既存turn早期returnの前に適用する。形式検査用の共通`_validate_key`へ予約検査を混ぜない。既に受理した同じmedia turnの終端確定を行う`_finish_primary_outcome`→`_remember`はこの予約競合検査の対象外であり、通常完了・拒否・再起動中断のdedupe primary行を書ける。外部へこの例外を選択する引数やAPIは公開しない。

予約は引き続き`media_inputs.client_key`だけに保存する。`_remember`を新しい受理の回避路に使わず、終端行は既存turnに束縛して一度だけ書く。MM-S10でmedia turnの通常完了・回復中断・終端再送と、他チャネルからの同キー拒否を確認する。

## 原子的な受理とDB制約

非公開`admit_media`は、処理中の期待状態・不変受付hash・sourceを検証し、状態CAS→admitted、user Record INSERT、`primary_turns` INSERTを一つの書込みトランザクションでcommitする。Primary行には同じ`client_key`、不変な`media-v1:`付き`request_hash`、`status='pending'`を格納する。commit前の障害では全体をrollbackする。

`media_inputs.client_key`と`primary_turns.client_key`の両方をDBのPRIMARY KEYまたはUNIQUE制約で一意にする。現行`primary_turns.client_key`は既にPRIMARY KEYであり、その保証を保持する。新規受付時の全テーブルのキー検査と挿入は、既存Storeの書込みトランザクションと同等の`BEGIN IMMEDIATE`内で行う。キーのUNIQUE違反は当該受理をrollbackしてConflictへ正規化し、別種のDB障害をConflictとして隠さない。

MM-S01で同キーのtext/media初回競合を、MM-S04で各書込み点のcrashを確認する。各入口を通る場合も、Recordだけ・admittedだけ・Primary行だけの不完全な受理を残さない。

## 再送、満杯、lock順序

- 同じ操作の通信再送は元のキーで行い、保存済み状態・結果を返す。failed/cancelled/interruptedを含め、終了したキーを別操作に再利用しない。本人が明示的に新しい処理を依頼する場合だけ新しいキーを使う。サーバーが自動でキーを替えてASR/Primaryを再実行しない。
- 永続化された未終了MediaInputが8件に達しているときは、新しいキーの受付を`media_queue_full`/HTTP503で拒否し、Record/MediaInput/容量予約を部分的に残さない。既存の同キー再送と取消し・状態取得はこの新規受付上限から除き、満杯でも保存済み結果へ到達できる。枠の取得・受付件数検査・保存は競合時にも上限を越えないようにする。MM-S06へ対応づける。受信同時2件の503、故障枠の`provider_unavailable`/503と区別して記録する。
- admissionとFuture公開のlock順序は既存`_reply_lock`→Store書込みトランザクション。Storeトランザクション保持中に逆順で返信lockを取りに行かない。推論、ASR、decoder、TTS、外部I/Oは両方の外で行う。MM-S01/S04/S07の競合・障害・応答性の確認に含める。

## 既存条件の維持

15件のMM-Sの期待する振る舞いを具体化したもので、新しい評価IDや製品PASSは作らない。実装fixtureは未実施、30件は全てNOT_RUN。SWE本文末尾のquota表現`<1GiB`は上限を狭める決定として採らず、原設計の「予約量を含む合計が1GiB以下」を維持する。
