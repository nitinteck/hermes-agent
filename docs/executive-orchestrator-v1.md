# Hermes Executive Orchestrator v1

The Executive Orchestrator is the standard pre-reasoning and post-reasoning
boundary for normal Hermes gateway conversations when
`HERMES_EXECUTIVE_ORCHESTRATOR_ENABLED=true`.

## Runtime Path

Production message flow:

1. Platform adapter receives an inbound message.
2. `GatewayRunner._handle_message` handles transport, authorization, platform
   normalization, plugin hooks and session claiming.
3. `authorized_gateway_dispatch` runs deterministic hooks.
4. `GatewayRunner._run_agent_inner` prepares the current turn.
5. `run_reasoning_with_optional_orchestrator(...)` calls
   `ExecutiveOrchestrator.prepare_turn(...)`.
6. `ExecutiveContextCollectionService` gathers bounded local provider
   contributions.
7. The existing `AIAgent.run_conversation(...)` receives the constructed
   executive reasoning request.
8. `ExecutiveOrchestrator.observe_response(...)` records a bounded trace and
   confirms `execution_state=not_executed`.
9. Gateway response delivery remains owned by the existing gateway adapter path.

The insertion point is
`gateway/run.py`, inside `GatewayRunner._run_agent_inner`, immediately before
the existing `agent.run_conversation(...)` call.

## Responsibilities

The orchestrator owns:

- request classification;
- bounded executive context assembly;
- executive context provider snapshot integration;
- safety boundary text;
- reasoning request construction;
- post-response observation;
- privacy-conscious trace metadata;
- non-execution enforcement for external-action requests.

The gateway still owns:

- transport;
- authentication and authorization;
- platform normalization;
- session persistence;
- agent lifecycle and model client configuration;
- outbound response delivery.

## Context Sources

The default context layer reads only local Hermes/OVOS state:

- current conversation/session metadata from the gateway turn;
- recent conversation metadata rendered as digests, not raw history;
- persistent profile or memory availability metadata;
- recent local OVOS EDE journal entries from `OVOS_EDE_LOCAL_STORE`, if set;
- latest local Daily Brief records from the same store, if available;
- pending approval-like journal entries;
- pending execution/action-like journal entries, still declarative;
- risk/opportunity-like journal entries;
- deterministic command output supplied by the gateway, where applicable.

No Gmail, Google Calendar, ClickUp, Slack, WhatsApp history or CRM connector is
implemented by this milestone.

## Context Provider Framework

The provider framework lives in
`gateway/executive_context_providers.py`.

Current production-safe providers:

- `current_request_metadata`
- `recent_conversation`
- `persistent_profile`

Disabled boundaries:

- `mock_executive_context`, local/test only and disabled by default
- `mcp_context_boundary`, disabled until explicitly authorised read-only
  connector work

Each contribution includes provenance, tenant/user scope, source mechanism,
evidence references, sensitivity and freshness metadata. Operator traces expose
counts, provider IDs, warnings and digests, not raw private content.

## Limits

Default bounded context limits:

- journal records: 5;
- brief items: 5;
- decisions: 5;
- approvals: 5;
- execution requests: 5;
- risks: 5;
- opportunities: 5;
- rendered context: 6000 characters.

Context is tenant-filtered when tenant IDs are present. Secret-like values are
redacted before context is rendered for the model.

## Safety

Potential external action requests fail closed before the model call. The user
receives:

```text
External execution is unavailable until the controlled execution boundary is implemented and explicitly authorised. I can help draft a declarative plan or action proposal, but I will not send, create, modify or delete external records.
```

Post-reasoning responses that imply external execution occurred are rewritten to
the same boundary message. Trace metadata always records
`execution_state=not_executed`.

## Failure Behaviour

For ordinary non-executable conversation, missing or unavailable context
degrades to safe ordinary conversation with a warning.

For potentially executable or unsafe requests, context or safety failures block
the turn instead of inventing an authorization state.

## Configuration

Development, test and production enablement:

```bash
HERMES_EXECUTIVE_ORCHESTRATOR_ENABLED=true
HERMES_EXECUTIVE_CONTEXT_PROVIDER_FRAMEWORK_ENABLED=true
HERMES_EXECUTIVE_CONTEXT_MOCK_PROVIDER_ENABLED=false
HERMES_MCP_CONTEXT_ADAPTER_ENABLED=false
OVOS_EDE_LOCAL_STORE=/path/to/ede-local-store.json
```

If the feature flag is false or unset, the gateway uses the previous direct
`AIAgent.run_conversation(...)` path.

Gateway startup logs include:

```text
Executive Orchestrator: ENABLED (execution_boundary=not_executed)
```

## Diagnostics

Operator-safe status:

```bash
hermes executive-orchestrator status
hermes eo status
```

Local-only diagnostic turn:

```bash
hermes executive-orchestrator diagnostic-turn "What is the executive status?"
```

The diagnostic command is a local process invocation. It does not bind a public
listener, does not attach a platform adapter, does not deliver outbound
messages, and disables diagnostic toolsets. Output includes correlation ID,
trace ID, classification, provider, model, response text, and
`no_execution_confirmed`. It also includes safe context-provider snapshot
metadata showing whether mock and MCP providers are disabled.

Redacted operator trace lookup:

```bash
hermes executive-orchestrator trace-lookup --approx-timestamp "2026-07-29T16:14:31Z" --window-seconds 900
hermes executive-orchestrator trace-lookup --correlation-id eo_...
hermes executive-orchestrator trace-lookup --message-digest abc123 --response-digest def456
```

Trace lookup reads `~/.hermes/executive_orchestrator_traces.jsonl` by default
and returns correlation ID, trace ID, classification, provider/model, context
source counts, safety state, execution state, message digest and response
digest. It does not return complete private message text, complete prompts,
phone numbers, tokens or secrets.

## Production Verification

Recommended production checks:

```bash
systemctl --user status hermes-gateway.service
hermes executive-orchestrator status
hermes executive-orchestrator diagnostic-turn "Hermes diagnostic: confirm orchestrator health."
hermes executive-orchestrator trace-lookup --approx-timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --window-seconds 900
tail -n 50 ~/.hermes/executive_orchestrator_traces.jsonl
```

Next milestone:

`HERMES MVP v0.2 — READ-ONLY EXECUTIVE CONTEXT CONNECTORS`
