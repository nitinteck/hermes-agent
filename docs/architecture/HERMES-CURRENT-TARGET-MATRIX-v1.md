# Hermes Current and Target Architecture Matrix v1

Last updated: 2026-07-29

| Area | Current state | Target direction |
| --- | --- | --- |
| Transport | Existing gateway adapters and local diagnostics | Same; no public chat API |
| Orchestration | Executive Orchestrator wraps normal reasoning turns when enabled | Hermes owns pre/post reasoning context and safety |
| Context | Local request metadata, recent conversation metadata, persistent profile availability, local OVOS/EDE data | Add read-only Gmail, Calendar and ClickUp context providers in MVP v0.2 |
| Provider registry | Deterministic in-process registry | Same registry with authorised read-only providers |
| MCP | Disabled boundary only | Read-only MCP providers after explicit milestone approval |
| Reasoning | Existing `AIAgent.run_conversation(...)` and configured provider/model | Same provider path |
| Execution | `not_executed`, live execution disabled | Controlled execution boundary only in a future milestone |
| Traceability | Correlation IDs, digests, stage records, provider snapshots | Expand evidence references as read-only providers arrive |
| Multi-tenancy | Tenant scope checked where identifiers exist | Hardened tenant isolation before wider deployment |
| Frontend | None | Non-goal for this phase |

## Current Production SHAs

- `hermes-agent`: `bc8393607e8350dacd7f41d83891bb032cd6309c`
- runtime-changing Hermes SHA: `db818dc4da080321767562de322a0968b063bbef`
- `ovos-core`: `0e6ee394d26ff2d7a814f3c84e0ed920aaaf5232`

This matrix must be updated after deployment of this milestone.
