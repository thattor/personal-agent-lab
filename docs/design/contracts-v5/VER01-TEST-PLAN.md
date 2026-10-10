# VER01/1 immutable author acceptance tests

Native test author source base: `6482d4c9c93209544757fb6c25d091a302064990`.
Adopted contract: VER01-SCOPE including its frozen SWE disposition following
consultation `e2477652c7ce43cbb9e20a91386fe2e1`.

Only `tests/test_verification_v5.py` and this note are authored. No implementation,
TSK/ART or canonical record changes. Every database is `:memory:`. Context, artifact
inspect and source gate are explicitly synthetic same-active-connection callbacks.
They are component fixtures, not actual MEM/TSK/ART or product proof.

The16 public tests cover:

- Fixed ordered Condition IDs: artifact_saved met, semantic/source_fetched unknown;
  empty complete artifact set gives unmet. Typed receipt/status shapes and bounded
  reasons; synthetic task state/budget remain unchanged.
- Closed shapes, strict integers/SQLite bounds and artifact-only caller refs;
  subset/superset/reorder/duplicate set conflict; unknown identities.
- Original canonical replay before current authority, changed-key input conflict,
  historical replay after epoch/set/source invalidation.
- Older artifact epoch of the same Goal/revision accepted; different Goal/revision
  stale. Status context uses required keyword purpose; unchanged pause remains valid.
- Explicit denied versus missing/transient evidence, unavailable versus invalidated;
  required current artifact missing cannot become an unmet check.
- Malformed context/ART/gate output, duplicate fixed Condition IDs, invalid hash/
  byte types and Ref mismatch; callback mutation and premature commit fail closed.
- Actual `v5_ver_` INSERT interception by a SQLite Connection subclass: ordinary
  post-write failure and KeyboardInterrupt/SystemExit roll back and permit key retry.
- Readonly inspect with preserved caller write/transaction; constructor and idle
  operations reject caller transactions; wrong inspect connection rejected.

Storage SQL layout is intentionally private: tests do not choose table/column
names apart from the adopted `v5_ver_` ownership prefix used for fault interception.
A synthetic `v5_tsk_test_state` sentinel checks accidental state/budget mutation,
not actual TSK authority. Root separately owns schema-tamper probes, disk reopen,
two-connection order, real source stops and actual consumer integration.

Validation executed:

```
/opt/homebrew/bin/python3.13 -I -S -B -c "import ast,pathlib; p=pathlib.Path('tests/test_verification_v5.py'); ast.parse(p.read_text()); print('AST OK')"
```

AST parse PASS; `git diff --check` PASS. Test execution is NOT_RUN because
`pal/verification_v5.py` does not yet exist. No fake implementation or skip is used.
The test module explicitly inserts its repository root before PAL imports for
isolated Python discovery. Once the owner module exists, the intended command is:

```
/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_verification_v5.py -v
```

These tests are fixed implementation inputs. Independent code review must be by
someone other than this test author; passing these tests alone does not establish
complete C09/C10, actual connected storage or personal usefulness.
