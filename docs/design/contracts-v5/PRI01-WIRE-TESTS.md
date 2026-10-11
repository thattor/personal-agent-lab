# Independent PRI01-WIRE fixed tests

Pinned base745a149a7f66b026afaa8227d7fda085443c48d4. Latest Root scope supplement
3b4fe6c read separately: C02 candidates are plain JSON dicts; current/allowed
record refs are exact typed public Ref objects. Shared scope is not edited here.
Only tests/test_primary_wire_v5.py and this note are authored.

25 methods, 13231 UTF8 bytes.
SHA256 acd76510b73ae0636607fe9149c9330f1aeb8b57e83ea568ce2615e3071962ef.
Runtime dependency: pal/contracts_v5.py; future pal/primary_wire_v5.py loaded in
setUp so module absence yields genuine RED. No other TestCase/fixture dependency.
Explicit root sys.path supports isolated discovery.

Coverage: every supported proposal, reply as data, full WorkRef membership,
current-record binding, question/revision and withheld restrictions, wrong-but-
listed structural acceptance, terminal/withheld metadata controls, allowed refs
and kind confusion, draft source order/duplicates, no model grants/origin/Condition
IDs, future/unknown/Expert tag distinctions, closed top/nested shapes, no markdown
fallback, duplicate keys at depths, nonfinite/malformed/deep JSON, exact str/UTF8,
8192 reply-byte and32768 input-byte inclusive bounds, candidate20 bound/unique
Goals/questions/states, no hidden text in withheld entries, input immutability and
nested returned-work alias isolation, bounded safe error args/attrs/context.

This is pure grammar/membership acceptance. It deliberately accepts a wrong but
listed target and leaves state permission to TSK. It does not prove source
usability, same-session disclosure, snapshot freshness, provenance closure,
owner dispatch, budget, model/semantic quality, PrimaryHost or overall activation.
No DB/model/service/provider invocation or parser stub/skip is added.

Baseline command:
`/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_primary_wire_v5.py -v`
Observed25 errors, all ModuleNotFoundError for pal.primary_wire_v5. Log
/private/tmp/pal-primary-wire-fixed-red.log. No parser behavior PASS claimed.
AST/diff checks PASS; the DraftBrief fixture separately parses with actual public
contracts under Python3.13. Assertions remain unexecuted until separate source
implementation. Root owns freeze/source dispatch and separate reviewer; fixed
file must remain unchanged after dispatch. Full integration remains later work.

Root clarification before dispatch: bare continue/attach, control command string
complete and bare memory remember/correct are fixed unavailable. Added/malformed
future fields may be invalid_input; tests do not loosen the recognized bare forms.
