# INT00 independent review

Reviewer: separate native `gpt-6.1-sol` context `/root/int00_sol_review`.
Implementation: native `gpt-6-astra` context `/root/int00_astra`.
Authority: D036. No source author is their own independent reviewer.

## Shared wire values

APPROVE — exact commit `d286fe7f1adff074f67b0ae4406c41eac3da9e24`, base
`a6983916ce78714fd97ae2320be8e374924f4313`. No concrete blocking defects found
in the four scoped files. SOL cherry-picked this as `601df87`; byte identity is
recorded separately.

The reviewer checked exact fields/enums, strict types, Draft/Formal separation,
nonnegative budgets, raw UTF-8/duplicate/nonfinite/non-JSON rejection, bounded
errors without retained cause/context, exact Ref membership, immutable snapshots,
alias isolation, lossless numeric round trips and strict Result decoder behavior.
Ordinary content was not restricted by invented authority or semantic rules.
The fixture contains 119 unique cases. All15 targeted tests and independent
wrong-kind membership, overflowing float and nested typed-result probes passed.

## Consumer composition

APPROVE — exact supplementary commit
`88924401a9e82acec9cae375c1d7774f70472cb3`.
The harness passes the parsed Action's actual capability into prepare_read and
checks source membership before execution. Wrong-kind Ref, duplicate arguments,
denied repository and unsupported capability stop before transport. Six previous
tests remain, with five new synthetic composition tests. All11 passed.

## Existing probe deadline race

APPROVE — exact commit `92732afa3f4dcaf84ddf7c821e22b35be883ed54`.
The private _ProbeStopped subtype represents only closed/expired checks; pin and
ordinary RunRejected failures remain distinct. The operator catches only that
subtype. Idempotent close_run preserves the first reason and existing cleanup.
Deterministic expiry-before-watchdog and close-before-check cases preserve clean
closure, no saved effects and the first reason. Other rejection still propagates
and records operator.failed. All22 related tests passed in an approved localhost
mock run; the reviewer's initial sandbox socket failure did not exercise the race.
The reviewer did not repeat the full suite or change files.

All reviews were read-only. Approval covers the listed code and regression scope.
It does not establish provider access, saved references, grants, Operation ledger,
service transactions, Goal completion, live UI or human usefulness.
