# Hermes Conversation Diagnostics v1

Last updated: 2026-07-30

## Purpose

Conversation diagnostics provide safe operator visibility into Donna Executive
Conversation Engine v1 without exposing secrets, hidden prompts, raw database
rows, raw Executive Context, or chain-of-thought.

## Safe Fields

- intent category;
- legacy classification;
- execution truth state;
- reason codes;
- working-set summary;
- grounding confidence;
- missing context labels;
- evidence-contract summary;
- truthfulness guard result;
- redaction status.

## Suggested Operator Views

- conversation status;
- conversation intents;
- conversation diagnostics;
- conversation working-set;
- conversation truthfulness;
- conversation last-response.

The v1 implementation surfaces these diagnostics in orchestrator metadata and
trace records. It does not add a new runtime service, connector or deployment
surface.

## Redaction Rules

- no raw system prompts;
- no hidden reasoning;
- no credentials;
- tenant, actor and conversation IDs are digested;
- full raw conversation history is not retained;
- sensitive content is represented as bounded summaries where possible.
