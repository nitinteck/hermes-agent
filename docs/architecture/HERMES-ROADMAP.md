# Hermes Roadmap

Status: living roadmap.

Last updated: 2026-08-01.

## Maintenance Rule

Every milestone PR must update this roadmap before review. A milestone is not
done if this file does not reflect:

- current milestone status;
- next milestone scope;
- completed merge/deploy/test gates;
- changed ordering or dependencies;
- newly discovered blockers or deferrals.

## Operating Mindset

Optimise for long-term architecture, not for preserving historical pull
requests. The value is a clean, coherent Executive Data Platform, not exact
preservation of intermediate implementations.

## Roadmap From RC1

```text
RC1
|
+-- Merge
+-- Deploy
+-- WhatsApp Test
|
v
Business Knowledge Foundation
|
v
Donna Executive Conversation Engine
|
v
Business Knowledge Population
|
v
Hybrid Retrieval
|
v
Executive State
|
v
Executive Dashboard
|
v
Calendar
|
v
ClickUp
|
v
Gmail
|
v
Approvals
|
v
Execution
|
v
Autonomous Executive Assistant
|
v
Multi-Assistant Product Foundation
```

## Milestone Status

| milestone | status | repository state | exit gate |
| --- | --- | --- | --- |
| RC1 Merge | complete | OVOS PR #13 and Hermes PRs #21/#22/#23/#24 merged | clean main branches |
| RC1 Deploy | complete | production VPS deployed from Hermes `3888f8d40` and OVOS `aca0d4c3` | gateway active, Supabase migrated |
| RC1 WhatsApp Test | complete by precondition | owner validation completed before Slice 3 | owner-only WhatsApp behavior accepted |
| RC1 Owner WhatsApp Validation | in progress | production runtime frozen at RC1; docs PR #26 may merge without deployment | owner structured testing complete and findings classified |
| Business Knowledge Foundation | review-ready, frozen during RC1 validation | OVOS PR #14, Hermes PR #25 remain open and unmerged | reviewed, explicitly unfrozen, then migrated/deployed only after RC1 testing |
| Donna Executive Conversation Engine | review-ready | Hermes PR pending from `codex/donna-executive-conversation-engine-v1`; no deployment | owner-test failures covered without enabling external capabilities |
| Business Knowledge Population | planned | not started | curated proposed/verified facts loaded through import/review flow |
| Hybrid Retrieval | planned | not started | relational-first retrieval with supplementary vector search |
| Executive State | planned | not started | derived read model only, never primary authority |
| Executive Dashboard | planned | not started | read-only operational visibility over EDP state |
| Calendar | planned | not started | read-only context first; writes remain unavailable |
| ClickUp | planned | not started | read-only context first; writes remain unavailable |
| Gmail | planned | not started | read-only context first; writes remain unavailable |
| Approvals | planned | not started | human approval records without execution |
| Execution | future | not started | controlled execution boundary with receipts and replay safety |
| Autonomous Executive Assistant | future | not started | assistant acts only inside governed, approved, observable boundaries |
| Multi-Assistant Product Foundation | future | docs-only architecture defined; no runtime implementation | assistant licensing, channel endpoints, participant identity and onboarding implemented after core EDP foundations |

## Current Focus

RC1 Owner WhatsApp Validation is the active milestone. Runtime feature
development is frozen while the owner performs structured real-world WhatsApp
testing.

Frozen review PRs:

- OVOS PR #14: Business Knowledge Foundation database layer;
- Hermes PR #25: Business Knowledge repositories and Executive Context
  integration.

These PRs are review-ready but not approved for production during RC1 owner
validation. Do not apply the Business Knowledge migration, deploy Business
Knowledge, or merge the Business Knowledge milestone during this freeze.

Exit criteria:

- owner completes structured WhatsApp testing;
- behavioural findings are classified;
- release blockers are separated from product improvements;
- next milestone is selected from evidence rather than assumption.

Business Knowledge Population must not begin until the foundation PRs are
reviewed, explicitly unfrozen, and merged.

## Current Review Milestone: Donna Executive Conversation Engine

Purpose:

- improve owner-facing WhatsApp behaviour without adding external
  capabilities;
- add a planning-versus-execution intent guard;
- preserve a transient working set across a decision conversation;
- enforce an evidence-led answer contract;
- strengthen action-receipt truthfulness;
- produce grounded executive responses;
- refuse unsupported or unsafe requests with a useful alternative.

Non-goals:

- no Business Knowledge deployment;
- no Executive State;
- no vectors;
- no Gmail, Calendar, ClickUp, Slack, CRM or other connectors;
- no approvals;
- no execution.

Exit gate:

- owner-test findings demonstrate the conversation defects being addressed;
- Hermes tracks explicit options and constraints inside a conversation;
- Hermes distinguishes proposals from executed actions;
- evidence, uncertainty and missing context are visible without exposing
  private internals;
- prompt-injection and self-modification requests remain refused.

Implementation documents:

- `HERMES-CONVERSATION-ENGINE-v1.md`;
- `HERMES-CONVERSATION-WORKING-SET-v1.md`;
- `HERMES-EXECUTION-TRUTHFULNESS-BOUNDARY-v1.md`;
- `HERMES-EVIDENCE-LED-RESPONSE-CONTRACT-v1.md`;
- `../testing/HERMES-DONNA-CONVERSATION-ACCEPTANCE-PACK-v1.md`;
- `../operations/HERMES-CONVERSATION-DIAGNOSTICS-v1.md`.

Business Knowledge Foundation remains review-ready but frozen pending owner
test findings and explicit approval.

RC1 hardening landed in this milestone:

- an option-tracking classification fix so connector names inside a compared
  option set are never read as an execution instruction (PR #30);
- a deterministic Donna RC1 tool boundary (`donna_owner_rc1`): the model
  receives no tools by default on the Executive Orchestrator route, so
  terminal, `execute_code`, `write_file`, `patch`, `skill_manage`, browser
  automation and `computer_use` are never available for a Donna WhatsApp
  turn, and self-modification claims are only made when actually provable.

Tenant/user isolation remains single-owner-only (see HTD-0017). A second
assistant instance, including Parent Assistant, must not launch until
per-instance tenant scoping is implemented and verified — this is unchanged
by the tool-boundary work above.

## Later Milestone: Business Knowledge Population

Purpose:

- populate the canonical Business Knowledge domain with owner-approved facts;
- preserve source provenance and confidence;
- use import-only candidate batches for YAML, JSON, and CSV;
- review/promote facts through lifecycle transitions.

Non-goals:

- no Executive State;
- no vectors;
- no ingestion pipeline;
- no connector sync;
- no execution.

Exit gate:

- proposed facts can be reviewed into verified/disputed/rejected states;
- duplicate and conflict reports are reviewed;
- Executive Context retrieves verified Business Knowledge;
- sensitivity and disclosure policy are validated with tenant tests.

## Future Product Milestone: Multi-Assistant Product Foundation

Purpose:

- model tenant subscriptions;
- model assistant licences;
- model assistant instances;
- model channel endpoints;
- model participant identity and audience class;
- model assistant-specific knowledge and capability scope;
- model the customer onboarding lifecycle;
- define the public assistant security boundary.

The initial product architecture is documented in:

- `HERMES-PRODUCT-DEPLOYMENT-MODEL-v1.md`;
- `HERMES-LICENSED-ASSISTANT-DOMAIN-v1.md`;
- `HERMES-MULTI-ASSISTANT-SECURITY-MODEL-v1.md`;
- `../product/HERMES-LICENSING-MODEL-v1.md`;
- `../operations/HERMES-CUSTOMER-ONBOARDING-RUNBOOK-v1.md`.

The Om Vidya Parent Assistant must not go live before:

- Business Knowledge is deployed and populated with approved public facts;
- public disclosure controls are verified;
- assistant-instance isolation is implemented and tested;
- participant identity handling is implemented and tested;
- escalation workflow is implemented and tested;
- customer acceptance testing is complete.

## Change Control

Roadmap changes should be small, explicit, and tied to a milestone. If a
milestone changes order, record the decision in
`HERMES-DECISION-LOG.md`. If a milestone reveals unresolved cleanup, add it to
`HERMES-TECHNICAL-DEBT-REGISTER.md`.
