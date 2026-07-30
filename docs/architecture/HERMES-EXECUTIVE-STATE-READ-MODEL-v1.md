# Hermes Executive State Read Model v1

Status: target read model. Do not create a separate source of truth.

## Recommendation

Executive State should be derived from canonical domain tables, events, and
scheduled snapshots. It should not be an independent mutable store that
duplicates facts, plans, commitments, approvals, and risks.

## State Categories

| category | source | representation |
| --- | --- | --- |
| current objectives | `executive.objectives` | mutable canonical records plus versions |
| current priorities | `executive.priorities` | mutable records, ordered by priority/effective date |
| active initiatives | `executive.initiatives`, `projects` | SQL view |
| open decisions | `executive.decisions` | current-state view |
| key risks | `executive.risks`, planning risks | current-state view plus severity |
| overdue commitments | `executive.commitments` | view calculated from due dates/status |
| waiting-for items | commitments, approvals, dependencies | view |
| project health | projects, milestones, risks, KPIs | materialised view when volume requires |
| KPI exceptions | KPIs and observations | calculated view/snapshot |
| relationship attention | relationships, stale contact signals | scheduled snapshot |
| pending approvals | approval requirements/records | view |
| capability constraints | governance capability truth and connections | view |

## Initial Read Model

Create a future view or materialised view equivalent to:

- `tenant_id`;
- `snapshot_at`;
- `active_objective_count`;
- `top_priorities`;
- `active_initiative_refs`;
- `open_decision_refs`;
- `key_risk_refs`;
- `overdue_commitment_refs`;
- `waiting_for_refs`;
- `project_health_summary`;
- `kpi_exception_refs`;
- `relationship_attention_refs`;
- `pending_approval_refs`;
- `capability_constraints`;
- `evidence_refs`;
- `context_digest`.

The read model should contain safe summaries and references, not raw private
message content.

## Runtime Use

The Executive Orchestrator should retrieve this read model, then selectively add
evidence and recent conversation context. The LLM should never decide what
organisational context to retrieve.
