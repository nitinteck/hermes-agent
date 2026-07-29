# Hermes Executive Context Provider Framework v1

Last updated: 2026-07-29

The Executive Context Provider Framework is the minimal production-grade
foundation for bounded executive context. It is implemented in:

`/Users/nitinteckchandani/Projects/Hermes-Build/hermes-agent/gateway/executive_context_providers.py`

## Contract

Each provider exposes `ExecutiveContextProviderMetadata` and returns
`ExecutiveContextContribution` records.

Each contribution must include:

- `contribution_id`
- `context_type`
- title and redacted summary
- `source_provider_id`
- `source_mechanism`
- `source_record_ref`
- `observed_at`
- confidence
- freshness state
- sensitivity
- tenant/user scope when known
- evidence references

The collection service validates provenance, tenant scope, duplicate IDs,
timeouts, and total context budget before the Orchestrator receives context
items.

## Snapshot

`ExecutiveContextSnapshot` records:

- selected provider IDs
- successful and failed provider IDs
- contribution counts by context type
- safe provider trace metadata
- warnings
- collection latency
- context digest
- snapshot digest

The snapshot is safe for operator diagnostics because it stores identifiers,
counts, digests, classifications, and provider status. It does not store full
private messages, phone numbers, secrets, raw prompts, or raw profile content.

Executive Intelligence consumes this snapshot. Providers should not embed
deterministic executive conclusions such as meeting conflicts, overdue
commitments or ranked attention signals unless they are explicitly source facts.

## Built-In Providers

Current production-safe providers:

- `current_request_metadata`
- `recent_conversation`
- `persistent_profile`

Test/local-only provider:

- `mock_executive_context`, disabled by default and enabled only when
  `HERMES_EXECUTIVE_CONTEXT_MOCK_PROVIDER_ENABLED=true`

Future boundary:

- `mcp_context_boundary`, disabled by default and enabled only when
  `HERMES_MCP_CONTEXT_ADAPTER_ENABLED=true`

## Feature Flags

```bash
HERMES_EXECUTIVE_CONTEXT_PROVIDER_FRAMEWORK_ENABLED=true
HERMES_EXECUTIVE_CONTEXT_MOCK_PROVIDER_ENABLED=false
HERMES_MCP_CONTEXT_ADAPTER_ENABLED=false
```

The provider framework defaults to enabled. Mock and MCP providers default to
disabled.

## Context Types

Initial supported logical context types include:

- `identity`
- `message`
- `capability_status`
- `active_project`
- `priority`
- `commitment`
- `risk`
- `opportunity`
- `decision`
- `approval`
- `execution_request`
- `daily_brief_item`
- `deterministic_output`

Providers may contribute zero records. A selected provider ID means the
provider was eligible and consulted, not that private context was available.

## Fail-Closed Rules

Provider failures are isolated and represented as warnings. Context collection
may degrade for ordinary non-executable turns.

Potentially executable or unsafe requests remain blocked by the Executive
Orchestrator and Execution Safety Kernel. Provider failures never create
authorisation or execution state.
