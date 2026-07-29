# ADR-0001: Layered Runtime Boundaries

Status: accepted

Date: 2026-07-29

## Decision

Hermes keeps the gateway, Orchestrator, context providers, reasoning provider,
and execution boundary as separate layers.

## Rationale

The gateway already owns transport and session responsibilities. The
Orchestrator needs to own executive context and safety without becoming a
replacement gateway or model client.

## Consequences

Future connector work must integrate through the context provider framework or
explicit execution boundary, not by adding hidden adapter calls inside prompts
or gateway glue.
