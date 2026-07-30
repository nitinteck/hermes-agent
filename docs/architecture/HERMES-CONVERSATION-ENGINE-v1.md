# Hermes Conversation Engine v1

Last updated: 2026-07-30

## Purpose

Donna Executive Conversation Engine v1 addresses owner WhatsApp testing
failures without adding external capabilities. It is a request-time layer
inside the existing Executive Orchestrator path.

It owns:

- conversational intent interpretation;
- transient working-set construction;
- current decision-frame preservation;
- Executive Context grounding;
- evidence-summary construction;
- answer-mode guidance;
- response truthfulness checks;
- useful refusal framing.

It does not own:

- durable Executive State;
- Business Knowledge;
- participant identity;
- approvals;
- execution;
- connector access;
- external action receipts.

## Flow

```text
Inbound message
-> ConversationIntentClassifier
-> ConversationWorkingSet
-> ExecutiveContextGroundingBuilder
-> EvidenceSummaryBuilder
-> Reasoning / Planning
-> ExecutionClaimGuard
-> Executive response
```

The implementation is intentionally narrow. It adds typed contracts and
deterministic guards around the existing orchestrator rather than creating a
second orchestration stack.

## Intent Categories

The v1 classifier recognises:

- discuss;
- ask_information;
- analyse;
- compare;
- recommend;
- plan;
- draft;
- prepare_action;
- request_execution;
- confirm_execution;
- challenge;
- correct_context;
- provide_evidence;
- status_query;
- capability_query;
- unsupported_or_unsafe.

The legacy `request_classification` values remain as compatibility labels for
existing reasoning and planning code. Safety-critical execution classification
fails closed, but planning, drafting, preparation and capability questions are
not treated as execution.

## Why Before Business Knowledge

Owner testing showed that behaviour quality was blocking useful evaluation of
future EDP features. Business Knowledge would make responses richer, but it
would not by itself fix:

- planning-versus-execution confusion;
- dropped option sets;
- weak evidence labelling;
- repetitive refusals;
- false action-completion claims.

This milestone improves the conversation contract first so later Business
Knowledge can be used coherently instead of amplifying generic answers.

## Relationship To Existing Layers

Conversation Engine prepares the turn. Executive Context resolves authorised
context. Intelligence interprets supplied evidence. Reasoning analyses and
recommends. Planning creates proposals only. Execution remains disabled.

## Relationship To PR #27

PR #27 remains open and unmerged. This milestone reused only compatible ideas:

- proposal-only execution status language;
- safe diagnostic metadata;
- explicit non-execution trace posture;
- stricter unsafe-disclosure phrase coverage.

Deferred:

- expanded planning registry fields;
- broader planning contract shape;
- synthetic planning complexity;
- durable planning lifecycle decisions.

Rejected for this milestone:

- moving conversation memory into Planning;
- registry expansion unrelated to owner-test failures;
- any approval or execution semantics.

## Known Limitations

- The working set is reconstructed from recent bounded history.
- Recommendations still depend on the LLM following the supplied response
  contract.
- Grounding is concise and selective; it is not Business Knowledge retrieval.
- Operator diagnostics are safe summaries, not raw prompts or raw context.
