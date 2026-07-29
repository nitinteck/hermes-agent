# Hermes Next Milestones v1

Last updated: 2026-07-29

## Current Milestone

`HERMES EXECUTIVE PLANNING ENGINE v1`

Completion means deterministic `ExecutivePlan`, `CandidatePlan`,
`PlanningSnapshot`, `ApprovalRequirement` and descriptive
`ProposedActionReference` contracts are implemented, validated, merged and
deployed in the normal Orchestrator path.

## Next Milestone

`HERMES EXECUTIVE APPROVAL ENGINE v1 DESIGN`

Scope:

- define authorised human approval contracts
- reject model, system, stale, expired, duplicate and unauthorised approvals
- preserve execution boundary
- keep live external execution disabled

## Later Milestone

`HERMES MVP v0.2 - READ-ONLY EXECUTIVE CONTEXT CONNECTORS`

Scope:

- Gmail read-only context provider
- Google Calendar read-only context provider
- ClickUp read-only context provider
- connector health diagnostics
- expanded evidence references
- behavioural regression tests proving capability honesty

Safety boundaries:

- no email send
- no calendar create/update/delete
- no ClickUp create/update/delete
- no Slack/CRM connector
- no live execution
- no public chat API

## Future Execution Milestone

Controlled external execution remains a separate future milestone after
read-only context is stable. It must use the existing Execution Safety Kernel
and must not be smuggled into read-only connector work.
