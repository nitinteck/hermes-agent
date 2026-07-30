# Hermes Technical Debt Register

Status: living register.

Last updated: 2026-07-30.

## Maintenance Rule

Every milestone PR must update this register when it accepts a deferral,
discovers a cleanup, narrows scope, or leaves a temporary compatibility path.
Debt is acceptable when named, owned, bounded, and sequenced.

## Debt States

- `open`: known debt with no active fix PR.
- `in_progress`: being addressed by an open PR.
- `blocked`: cannot proceed until a named dependency lands.
- `retired`: resolved or made irrelevant by later architecture.

## Register

| id | area | debt | status | target | owner | notes |
| --- | --- | --- | --- | --- | --- | --- |
| HTD-0001 | Business Knowledge | Slice 3 defines canonical tables and repository contracts, but population/review workflow is not implemented. | open | Business Knowledge Population | EDP | Must use import-only candidates and lifecycle review; no ingestion pipeline. |
| HTD-0002 | Business Knowledge | Legacy `knowledge_memories`, `knowledge_objects`, and executive-context tables still coexist with canonical `business_*` tables. | open | Business Knowledge Population | EDP | Reuse as provenance/evidence; do not duplicate authority. |
| HTD-0003 | Executive Context | Optional private-schema REST reads are still treated as empty sections where no public RPC exists. | open | Business Knowledge Population / Hybrid Retrieval | Hermes | Add deliberate RPCs rather than exposing private tables broadly. |
| HTD-0004 | Retrieval | Hybrid Retrieval exists as architecture only; no relational-first retrieval provider has landed. | open | Hybrid Retrieval | EDP | Relational filters must run before vector search. |
| HTD-0005 | Executive State | Executive State read model is documented but not built. | open | Executive State | EDP | Must be derived from authoritative facts/events; never hand-maintained. |
| HTD-0006 | Dashboard | Executive Dashboard does not yet consume EDP read models. | open | Executive Dashboard | Hermes | Dashboard should be read-only until approval/execution milestones. |
| HTD-0007 | Connectors | Calendar, ClickUp, and Gmail live context are not enabled in owner runtime. | open | Calendar / ClickUp / Gmail | Hermes | Start read-only; writes remain unavailable. |
| HTD-0008 | Approvals | Approval engine is future work. | open | Approvals | EDP | User request text must not be interpreted as approval. |
| HTD-0009 | Execution | Execution boundary is future work. | open | Execution | EDP | Requires explicit authorisation, receipts, idempotency, audit, and rollback semantics. |
| HTD-0010 | Documentation | Older milestone docs may describe now-superseded sequencing. | open | Continuous | Hermes | Living docs here are canonical when conflicts arise. |
| HTD-0011 | Planning | Planning Engine v1 is request-scoped and does not durably persist full plan bodies. | open | Approval Engine / Planning Lifecycle | Hermes | Keep full plans request-scoped until approval semantics and retention rules exist; traces may store safe digests and counts only. |
| HTD-0012 | Planning | Model-assisted planning remains disabled. | open | Post-v1 Planning | Hermes | Deterministic envelope is required first; any model-assisted drafting must pass schema, evidence, lifecycle and safety validation. |

## Debt Acceptance Criteria

New debt entries must include:

- why the debt exists;
- what milestone should resolve it;
- what must not be built early to hide it;
- validation needed when resolved.

## Cleanup Rule

When a debt item is resolved, mark it `retired` and link the PR or decision log
entry that retired it. Do not delete retired debt immediately; it is useful
architectural memory.
