# Hermes Executive Intelligence Engine v1

Last updated: 2026-07-29

## Position

Executive Context answers: what source facts and relevant records are available?

Executive Intelligence answers: what deterministic executive signals can be
derived from those facts?

Executive Insights, recommendations, forecasts and proposed action references
remain separate layers. Planning Engine v1 may create descriptive
`ProposedActionReference` records; Intelligence v1 remains facts and signals
only.

Runtime flow:

`ExecutiveContextSnapshot -> ExecutiveIntelligenceEngine -> ExecutiveIntelligenceSnapshot -> Executive Reasoning -> optional Executive Planning -> Context Composer -> Executive Orchestrator`

The engine does not call integrations, load credentials, invoke MCP, query
Google Calendar, call an LLM, write databases, send messages or execute actions.

## Definitions

- Source fact: directly observed or retrieved context with provenance.
- Derived fact: deterministic calculation from source facts.
- Signal: structured indication that something is relevant, abnormal,
  approaching, delayed, conflicting or changing.
- Score: transparent bounded calculation with versioned inputs and thresholds.
- Inference: reasoned conclusion not directly stated by facts.
- Insight: executive interpretation of facts and signals.
- Recommendation: proposed course of action.
- Forecast: forward-looking estimate.
- Proposed action: candidate action subject to capability, approval and safety.

v1 emits only derived facts and deterministic signals. Inference modules are
disabled.

## Initial Modules

- `context_availability`
- `schedule_summary`
- `calendar_conflict`
- `focus_time`
- `back_to_back_load`
- `preparation_gap`
- `commitment_due`

The modules operate on canonical `ExecutiveContextContribution` records. They
support synthetic context, so Calendar live authorisation is not required.

## Snapshot Lifecycle

v1 snapshots are request-scoped. Full signal payloads are not durably persisted.
Safe trace metadata stores counts, module IDs, digests, priority/severity
summaries and error codes.

Future work may add persisted trend history after separate privacy review.

## Ranking

Ranking is deterministic by profile:

- profile relevance override
- priority
- severity
- confidence
- generated time
- module ID
- signal ID

Implemented profiles: `direct_request`, `morning_brief`, `schedule_review`.

## Safety

Every signal requires source context IDs and evidence references. Cross-tenant
or cross-user signals are rejected. Invalid, duplicate or unsupported outputs
are skipped. One module failure does not fail the whole snapshot.

Execution boundary remains `not_executed`.
