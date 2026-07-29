# Hermes Next Milestones v1

Last updated: 2026-07-29

## Current Milestone

`HERMES LAYERED ARCHITECTURE AND EXECUTIVE CONTEXT FOUNDATION v1`

Completion means the layered architecture is documented and the Executive
Context Provider Framework v1 is implemented, validated, merged and deployed.

## Next Milestone

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

## Later Milestone

Controlled external execution remains a separate future milestone after
read-only context is stable. It must use the existing Execution Safety Kernel
and must not be smuggled into read-only connector work.
