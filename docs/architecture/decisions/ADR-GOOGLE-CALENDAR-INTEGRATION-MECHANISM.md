# ADR: Google Calendar Integration Mechanism

Date: 2026-07-29

## Status

Accepted for Hermes MVP v0.2 Calendar provider.

## Context

Hermes needs its first live external Executive Context Provider without
weakening the execution boundary. The options considered were:

- direct Google Calendar API integration
- a connected MCP/connector tool
- exposing Google Calendar tool calls to the reasoning provider

The Executive Orchestrator already owns context selection and must not let the
LLM decide which organisational context to retrieve.

## Decision

Implement a direct, read-only Google Calendar provider inside the Executive
Context Provider Framework.

The provider calls Google Calendar API `events.list` through a small injectable
read client, normalises events into Hermes-owned
`ExecutiveContextContribution` records, and exposes only safe summaries and
digests to the Orchestrator trace.

The provider is selected only for Calendar-shaped context requests and Daily
Brief agenda requests. Potentially executable Calendar requests fail closed
before Calendar reads.

## Consequences

- The LLM never invokes raw Google Calendar tools.
- OAuth tokens and raw Calendar payloads remain outside prompts and traces.
- The implementation can be tested with focused fakes.
- Live reads can remain disabled until user authorisation is complete.
- Writes remain architecturally absent; EDE/Safety Kernel execution state stays
  `not_executed`.

## Non-Goals

- Calendar event create/update/delete
- freebusy write scopes
- Gmail, ClickUp, Slack or CRM connectors
- public chat API
- generic MCP tool access
- live execution adapters
