# HOST01/1 independent fixed tests

Binding: base06aed96225a9c857a1101846e771937753427b04 and RECOVERY01-SCOPE.md, adopting the retained Opus REFINE through design-disposition.json. Proposal/preparation wording is not normative. Only test_mock_host_v5.py and this note are owned; no implementation or TaskStore integration.

13 methods cover canonical DB/permanent sidecar, fresh identities, readonly phases/properties, idempotent registration, startup activation, same-process duplicates and strong registry retention after GC, actual two-process contention/normal close, SIGSTOP and direct process death, forked guard refusal, inherited FD after parent death, nested operation/activity close refusal, BaseException permit release, context-manager close, closed/fake/wrong/blank connections, memory/blank/URI refusal, symlink/hardlink sidecar and DB hardlink, and DB/sidecar replacement (original paths restored in finally).

Process tests own fresh temporary files and subprocesses, use pipe/select readiness with5-second bounds and waitpid stopped-state acknowledgments; no timing sleeps or lock retry. Cleanup kills only owned test children. The inherited-FD test asserts retained occupancy after parent death; it does not confuse parent explicit flock unlock with descriptor inheritance. POSIX/macOS local files only; no network-FS or escaped product callbacks are qualified.

Root clarified open refusal taxonomy: (RuntimeError,ValueError,OSError) is accepted because the freeze specifies refusal rather than OS exception taxonomy. check_connection/permit/close remain exact RuntimeError. mark_registered/activate are trusted test fixture calls, not model enrollment authority.

Exact baseline command:

`/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_mock_host_v5.py -v`

**RED:13 methods,13 errors,0 failures, exit1**, each setUp raises ModuleNotFoundError for pal.mock_host_v5. No behavior test executed and no HOST pass is claimed. Original log retained at /private/tmp/pal-host-fixed-red.log. AST syntax parses. This RED is source absence, not a broken fixture proven against an implementation. Independent author execution/review after source remains required. Full845 not rerun.

Test SHA256: bd5aa6c9c6b9c4b0874c55b190e6aeaecf4b7b64f8128ec416fb9cbdc21892b8 (11337 UTF8 bytes). No existing test fixture dependency. Root owns actual managed TSK/RUN/ART/VER/MEM/C14 connection and subprocess recovery demo; no enrollment, interrupted-call settlement, held ART/external tail, budget, real provider/service or whole-goal proof follows from this HOST file.
