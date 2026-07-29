# Hermes MCP Boundary v1

Last updated: 2026-07-29

Hermes currently has no live MCP context connector.

`MCPContextProviderBoundary` exists only to define the future read-only
boundary and fail closed until an explicitly authorised milestone connects a
provider.

## Current Runtime State

```bash
HERMES_MCP_CONTEXT_ADAPTER_ENABLED=false
```

When disabled, `collect_resource(...)` raises an error before any resource
collection can occur.

## Access Classification

MCP tool schemas are classified as:

- `read`: explicit `readOnlyHint=true` or read-like tool names such as get,
  list, search, read, fetch, or query.
- `write`: write-like names such as create, update, delete, send, schedule,
  modify, patch, or write.
- `unknown`: anything else.

Only read-classified tools may be considered by a future read-only connector.
Write and unknown tools fail closed.

## Non-Goals

This boundary does not implement Gmail, Google Calendar, ClickUp, Slack, CRM,
news, portfolio data, public chat APIs, or live execution.
