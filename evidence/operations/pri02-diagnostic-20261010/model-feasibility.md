# C087 model observation feasibility — diagnosis, not qualification

Basis: PAL source69c6e226ba14da881f0ed11670601b1b5e854c48; installed CO0.4.5,
Devin3000.11.3. Separate Native Astra researched official protocol and public
callbacks; separate Native Sol traced PAL validation. Root checked cited source
and official pages. No provider/init/config command or CO/state change occurred.
Original N2 remains UNKNOWN and its unsaved frames/text cannot be reconstructed.

## Supported and unconfirmed

Current [ACP config options](https://agentclientprotocol.com/protocol/v1/session-config-options)
can expose a model selector's current value; initial exposure is optional. Updates
may change it during generation. Categories describe presentation rather than
identity authority. These facts support collecting observations, not claiming the
Devin server actually supplied them or used an exact model in N2.

[Devin's ACP command reference](https://docs.devin.ai/cli/reference/commands)
and [Zed integration](https://docs.devin.ai/cli/acp/zed) describe model selection.
The requested CLI argument is not an exact effective-model acknowledgement.
Version3000.11.3's exact option UID, response UID, timing and generation-level
guarantee are unconfirmed. Installed vocabulary alone does not prove wire data.

Installed CO `devin_selection.py:52–86` recognizes legacy models/currentModelId/
availableModels. `adapters/devin.py:841–858` processes configOptions for mode only.
If a model is exposed only by configOptions, this observer cannot mark it verified.
That is a compatibility hypothesis, not the unique original N2 exception cause.

The existing public callbacks retain enough information for bounded diagnostics:

* `adapters/devin.py:730–740,807–827`: full session result reaches observe_model.
* `:877–891`: verify(session) receives a distinct effective preprompt snapshot.
* `:905–934`: session identity is checked before update reaches the observer;
  the callback lacks the outer session ID and an independent prompt RPC ID.
* Config updates can invoke the observer twice. Pre-session updates are replayed
  before initial result observation. Callback counts/order are not wire counts/order.
* `devin_host.py:225–272`: the original owner binds request/session/prompt and
  proves its own ending/EOF/wait. Its original model null/false fields stay intact.

## Contract consequence

Current NativeTextBuffer.finish and NativeReturned.validate both require the
original exact effective-model/verified fields. Primary and durable TSK replay
reuse that validation. Attaching a diagnostic ACK cannot qualify them.

An additive authoritative ACK would need a separate explicit version/profile,
closed original observations, exact UID semantics, request/session/attempt binding,
later-change rejection and validation through storage/history/recovery. Preserve
the unchanged original cessation and its hash; never synthesize verified fields.
Such a profile is not adopted here. Optional category, display names, fuzzy UID,
duplicate callback and an unbound snapshot are insufficient substitutes.

The smallest next candidate is fixture-only bounded model-observation retention
through existing public hooks, separately labelled unqualified. Observe the
original initial result, preprompt snapshot and updates without altering them or
granting new lifecycle/qualification authority. A later finite actual feasibility
case requires a separately reviewed freeze; N3/T2/real Expert remain unauthorized.
If only invocation binding is practical, present the guarantee choice to the
existing human-design lane rather than silently lowering current acceptance.

## Current implemented slice

PRI02-DIAGNOSTIC/1 preserves valid bounded text after the original supported stop.
It discards poisoned text, preserves strict rejection, emits no adopted output,
and keeps the new private file local. Separate Sol buffer and wrapper reviews
APPROVE; Root full1210 PASS32.581s/exit0. These are fixtures, not real model proof.
