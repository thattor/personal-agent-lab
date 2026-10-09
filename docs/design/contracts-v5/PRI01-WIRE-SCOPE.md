# PRI01-WIRE/1 — frozen pure Primary output parser

This independent prerequisite implements the closed grammar/target rules in the
completed actual Opus5.5 PRI01 F4/F6 and Root's concrete R4/R6 shapes. No model,
owner dispatch, grant, transaction, source body, provenance adoption, completion,
host activation or usefulness assertion. Additional Opus refinement was refused
by session limit and yielded no adopted report. Root owns this wire freeze; a
separate Sol owns fixed tests, SWE-2 High preferably implements the new module,
another context independently reviews exact source. Python standard library only.

New module `pal/primary_wire_v5.py` exports
`parse_primary_output(text, *, current_record_ref, candidates, allowed_record_refs)`
and `PrimaryProposalError`. Reuse public contracts_v5 values/strict JSON, never
change shared parser or Expert grammar. Read only this scope, actual
contracts_v5.py, fixed tests and package init. Sole source write is the new module.

## Trusted inputs and bounds

text is exact str, strict UTF8, <=32768 bytes; decode exactly one JSON document,
reject duplicate keys at any depth, NaN/Infinity, invalid UTF8/surrogates, trailing
text, scalars/arrays and malformed JSON. No markdown-fence stripping or fallback.
Closed top-level `{reply,proposal}`. reply exact str strict UTF8 <=8192 bytes,
including empty; never interpret a claim in reply as authority.

current_record_ref is exact public Ref(kind=record). allowed_record_refs is a
list/tuple of exact record Ref values and includes current_record_ref; duplicates
are harmless. candidates is the C02 `works` list, <=20 closed entries
`{work_ref,brief_summary,expert_id,state,open_questions,dependency_refs,text_withheld}`.
Entries contain plain JSON WorkRef/Ref dictionaries as returned by C02; validate
with public WorkRef/Ref.from_json. Validate UTF8 summary/expert/state, strict bool
withholding, list of record Ref dictionaries, list of closed `{id,text,revision}` questions: nonempty UTF8
id, UTF8 text, strict positive revision matching its candidate WorkRef revision.
Each Goal appears once and question IDs are unique per candidate. Withheld entries
have empty summary/all question text; no hidden body. Allowed states are existing
TSK queued/running/waiting_input/paused/completed/cancelled/failed, never superseded.
No input mutation or aliasing in the returned normalized plain JSON dict.

This parser checks exposure membership, not source usability, snapshot freshness,
intention, ambiguity or authorization. Trusted caller establishes same-session
allowed records and source gating. A wrong-but-listed target is structurally
valid; fixed tests retain this practical limit. Fingerprint/owner checks follow
in PrimaryHost rather than this parser.

## Closed proposals

- `{kind:"none"}`.
- `{kind:"new_work",brief:<DraftBrief>}`. Use public DraftBrief parser and require
  all selected context_refs to be exactly in allowed_record_refs. Conditions are
  draft descriptions/checks with no minted IDs. No model origin/grant/scope fields.
- `{kind:"answer",work_ref,question_id,record_ref}`. WorkRef must equal a disclosed
  candidate in full (including snapshot epoch), question_id must match one of its
  open questions at that revision, record_ref must equal current_record_ref. A
  text_withheld candidate returns denied before an answer can be adopted.
- `{kind:"control",work_ref,command:"pause"|"resume"|"cancel"}`. Full snapshot
  WorkRef membership; metadata-only controls may select withheld/terminal works,
  with actual state permission left to TSK. No inferred latest Goal or ordinals.
- `{kind:"control",work_ref,command:{kind:"change",brief:<DraftBrief>,
  origin_record_ref}}`. Same exact target membership, selected refs as new_work,
  origin must equal current_record_ref; withheld target denied. No model grant,
  Condition IDs, replacement Goal IDs or completion claims.
- `{kind:"memory",operation:{kind:"stop_reference",source_ref}}`. Source is a
  record Ref exactly in allowed_record_refs; no note/source/artifact/verification
  substitution. Same-session disclosure is the trusted caller's obligation.

Unexpected/missing fields, types, invalid public contracts, unknown tags and
out-of-set selectors return invalid_input. Recognized future top-level
continue/attach tags, control complete and memory remember/correct yield
unavailable; they cannot become none/new_work. Malformed future commands may
return invalid_input. These are no-op parse errors, never owner calls.

Successful parse returns normalized `{reply,proposal}` retaining model-selected
original IDs/Refs and order/duplicates in Brief context_refs. The host later
closes actual exposure provenance; parser must not invent or silently replace
record_ref/origin/work targets, dedupe source selection or attach authority.

## Bounded failures and verification

PrimaryProposalError is a ValueError with `.code` equal to invalid_input, denied,
unavailable or limit; fixed safe message only. Size excess is limit. Error text,
args/attributes/context contain no raw JSON, reply, exception, path, secret canary
or offending field value. Raise outside caught ContractError/JSON handlers so
their source-bearing context is not retained. BaseException propagates.

Independent fixed tests cover every supported proposal, full WorkRef/revision/
question/current-record checks, wrong-but-listed and withheld distinctions,
extra capability/grant/ID/complete injection, duplicate/nonfinite/UTF8/deep bad
JSON, exact byte boundaries, allowed record kind confusion, no mutation/aliasing,
no fallback and bounded no-source errors. Initial absent-module RED is preserved.
CO verified covers only these unchanged tests; separate exact-source review and
Root regression/Primary connection are still required afterward.
