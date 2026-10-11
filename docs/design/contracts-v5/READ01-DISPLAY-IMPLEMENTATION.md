# READ01-N1/1 display correction

The independent READ01 Opus finding N1 (evidence/operations/read01-20261009/opus-final-review.md:81–84) identified multiline owner/model strings that could print apparent host status lines. The public inspect_session/render regression reproduced this before correction: six tests ran, five failed. Original log: /private/tmp/pal-read-display-red.log.

Cause: renderer labels interpolated owner strings directly; only draft body lines had indentation. Condition descriptions, reasons, event text and errors could introduce unprefixed lines. The structured inspection was unaffected.

The correction adds one final display helper to the assembled render lines. Each embedded LF continuation receives six spaces plus `| `; existing multiline draft indentation remains readable. Unicode control/format characters (Cc/Cf) and Unicode line/paragraph separators (Zl/Zp) become visible `\uNNNN` sequences. This includes ESC, CR, backspace, C1 controls and bidirectional formatting controls. Japanese text and normal labels remain unchanged. No stored content, hash, C11 result, inspection JSON, parsing, routing or authority changes occur. The renderer does not mutate its input.

Six new public-boundary tests cover event/condition/reason/error spoofing, envelope strings, inactive terminal controls, Japanese/multiline readability and exact inspection/content/hash preservation. They depend on explicit owner doubles in tests/test_read_consumer_v5.py; these are unit display evidence, not live/product proof. Existing tests are unchanged.

Validation:

- `/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_read_display_v5.py -v`: 6 PASS, 0.002s; /private/tmp/pal-read-display-focused.log.
- `/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p 'test_read*.py' -v`: 32 PASS, 0.152s; /private/tmp/pal-read-display-existing.log.
- `/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_verification_read_v5.py -v`: 10 PASS, 0.023s; /private/tmp/pal-read-display-ver.log.

The initial broad `-I -S` read discovery had 23 passing methods and one import error: existing test_read_connection_v5.py does not insert the project path before importing pal. Retained log: /private/tmp/pal-read-display-green.log. No existing fixture was changed; the normal existing command passed all 32.

Prevention: when adding renderer fields, retain the final display boundary and check both injected line breaks and terminal controls while comparing serialized inspection bytes. Root owns full-suite/integration verification and a separate reviewer owns exact-commit review. No live DB, external model, service or UI activation was used.
