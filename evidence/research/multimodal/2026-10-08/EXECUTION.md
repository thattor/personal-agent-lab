# 取得・レビュー記録の再利用範囲

この文書は、保存した資料の由来と読み方を説明する。過去の承認・端末設定を再実行用の権限として引き継ぐ手順ではない。

## 公開ソースの取得

[fetch_sources.py](fetch_sources.py) はPython標準ライブラリによる公開GitHubソースの取得用スクリプト。`inventory` は5リポジトリのdefault branchのcommit、metadata、treeを取得し、`capture` は保存済みmetadataのcommitと [selected-files.json](selected-files.json) で指定したファイルを取得する。取得URL、commit、SHA-256、バイト数は [source-receipts.json](source-receipts.json) に残る。

スクリプトは自身の配置ディレクトリへ書き込む。当時のhashを保持するため、凍結済みのこのフォルダ上で再実行しない。将来同じ版を取り直す場合は、新しい作業先へスクリプト、選択一覧、各repoのmetadata.jsonを複製して `capture` を使い、今回のreceiptと照合する。新しい版を調べる場合は、新しい作業先で `inventory` から別の調査記録を作る。`inventory` を再実行すれば同じ版になるとは限らない。

今回の保存ではネットワーク再取得や取得コードの実行を行わず、既存の実ファイルとreceiptを照合した。5リポジトリの各LICENSEを取得コードと同じ場所へ保持した。

## レビュー記録

| 対象 | 実際の結果 | 証拠 |
|---|---|---|
| 初期調査のOpus | exit 0、38.357秒 | [問い](review-question.txt)、[確認](review-access.json)、[回答](opus-review.txt)、[終了](review-completion.json) |
| 設計初稿のOpus | completed、exit 0、201.001秒 | [固定入力](design-v1/reviews/input-freeze.json)、[問い](design-v1/reviews/question.txt)、[確認](design-v1/reviews/opus-access.json)、[回答](design-v1/reviews/opus-response.txt)、[終了](design-v1/reviews/opus-completion.json) |
| 設計改訂案のSWE-2 High | 本人承認後に一回実行。600.016秒でtimeout、4,601 bytesの一部回答 | [承認と入力](design-v1/reviews/swe-authorized-input.json)、[問い](design-v1/reviews/swe-question.txt)、[確認](design-v1/reviews/swe-access.json)、[回答](design-v1/reviews/swe-response.txt)、[終了](design-v1/reviews/swe-completion.json) |

既存の公式経路を使用し、追加課金・paid fallbackを有効にしなかったことは各確認記録の範囲で読む。SWEの当時の制限はツールdeny、subagent無効、workspace trust維持。承認前の拒否2件も `design-v1/reviews/` に残している。今回の保存を理由に拒否を迂回したり、一回限りの承認を再利用したりしない。

受信した指摘と現行ソースの照合、設計への反映、途中終了の原因と次回の確認条件は [REVIEW.md](design-v1/REVIEW.md) にまとまっている。レビューで参照したPALのcommitは `5e7c76c24dd8bf700d2811c7188739cdc77d9aa8`。改訂後の独立した再レビューや製品試験を完了扱いにしない。

## 収録しない一時ファイル

[IMPORT.json](IMPORT.json) に除外対象のhashと理由を記録した。原本は元のローカル作業先に保持している。

- `run_review.py`：当該端末のアカウント結合を含む調査レビュー起動用。
- `review_runner.py`：当該端末のアカウント結合と、一回の承認を対象にした実行ガードを含む設計レビュー起動用。
- `swe-review-only-config.json`：当該端末のhooks/settingsを含む一時設定。再利用する恒久設定にはしない。

再利用に必要な問い・モデル・制限条件・実行時間・終了状態・回答・固定入力は安全な記録に残っている。資格情報、実行用の認証情報、不要なアカウント情報を保存対象へ足す必要はない。

## 保存済みファイルの照合

repositoryのrootから次を実行すると、保存時のmanifestに記録したファイルを再照合できる。ネットワークやモデルは使わない。manifest自身は自己参照を避けてhash一覧から除外している。現在の開発文書や将来の製品動作を検証するものではない。

```sh
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

root = Path('evidence/research/multimodal/2026-10-08')
record = json.loads((root / 'ARCHIVE-VALIDATION.json').read_text())
for name, expected in record['files_sha256'].items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit('hash mismatch: ' + name)
print('verified', len(record['files_sha256']), 'files')
PY
```
