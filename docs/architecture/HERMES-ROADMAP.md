# Hermes Roadmap

Status: living roadmap.

Last updated: 2026-07-30.

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
```

## Milestone Status

| milestone | status | repository state | exit gate |
| --- | --- | --- | --- |
| RC1 Merge | complete | OVOS PR #13 and Hermes PRs #21/#22/#23/#24 merged | clean main branches |
| RC1 Deploy | complete | production VPS deployed from Hermes `3888f8d40` and OVOS `aca0d4c3` | gateway active, Supabase migrated |
| RC1 WhatsApp Test | complete by precondition | owner validation completed before Slice 3 | owner-only WhatsApp behavior accepted |
| Business Knowledge Foundation | in review | OVOS PR #14, Hermes PR #25 | canonical relational model, repository boundary, no execution |
| Business Knowledge Population | next | not started | curated proposed/verified facts loaded through import/review flow |
| Hybrid Retrieval | planned | not started | relational-first retrieval with supplementary vector search |
| Executive State | planned | not started | derived read model only, never primary authority |
| Executive Dashboard | planned | not started | read-only operational visibility over EDP state |
| Calendar | planned | not started | read-only context first; writes remain unavailable |
| ClickUp | planned | not started | read-only context first; writes remain unavailable |
| Gmail | planned | not started | read-only context first; writes remain unavailable |
| Approvals | planned | not started | human approval records without execution |
| Execution | future | not started | controlled execution boundary with receipts and replay safety |
| Autonomous Executive Assistant | future | not started | assistant acts only inside governed, approved, observable boundaries |

## Current Focus

Business Knowledge Foundation is the active review milestone. It establishes
canonical Business Knowledge tables, lifecycle, evidence, provenance,
sensitivity, disclosure policy, review, import dry-run behavior, and Hermes
repository consumption.

Business Knowledge Population must not begin until the foundation PRs are
reviewed and merged.

## Next Milestone: Business Knowledge Population

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

## Change Control

Roadmap changes should be small, explicit, and tied to a milestone. If a
milestone changes order, record the decision in
`HERMES-DECISION-LOG.md`. If a milestone reveals unresolved cleanup, add it to
`HERMES-TECHNICAL-DEBT-REGISTER.md`.
