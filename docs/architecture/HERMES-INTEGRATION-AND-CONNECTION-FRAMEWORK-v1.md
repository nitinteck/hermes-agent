# Hermes Integration And Connection Framework v1

Last updated: 2026-07-29

## Purpose

The Integration and Connection Framework separates executive context selection
from the mechanics of reaching external systems.

Conceptual flow for context reads:

`Executive Context Provider -> IntegrationService -> ConnectionRegistry -> CredentialResolver -> IntegrationAdapter -> External System`

The v1 implementation is read-only. It can describe write capabilities for
future governance, but `IntegrationService.execute_read(...)` fails closed for
any capability whose `read_write` value is not `read`.

## Core Objects

- `IntegrationDefinition`: a supported external system or protocol, such as
  `google_calendar`, `gmail`, `clickup`, `openrouter`, `supabase` or
  `mcp_server`.
- `ConnectionDefinition`: an authorised tenant/user relationship with an
  external account, workspace or resource.
- `CredentialReference`: a reference to a secret location. It never contains
  the secret value.
- `ResolvedCredential`: a boundary object passed only to an adapter. Its repr
  and safe trace redact the value.
- `IntegrationCapability`: a named operation with read/write class, required
  scopes, risk class and adapter mapping.
- `IntegrationAdapter`: the only layer that performs external protocol calls.
- `IntegrationResult`: a redacted result containing data, status, latency,
  retry count, health state and safe audit metadata.

## States

Connection states:

- `unconfigured`
- `disconnected`
- `authorisation_required`
- `connected`
- `degraded`
- `authentication_failed`
- `permission_denied`
- `rate_limited`
- `unavailable`
- `revoked`
- `disabled`

Error codes:

- `missing_credentials`
- `invalid_credentials`
- `expired_credentials`
- `revoked_credentials`
- `insufficient_scope`
- `permission_denied`
- `rate_limited`
- `timeout`
- `upstream_unavailable`
- `malformed_response`
- `configuration_error`
- `unsupported_operation`
- `disabled`
- `tenant_scope_violation`
- `user_scope_violation`
- `unknown_failure`

## Scope And Governance

Every connection is scoped by tenant, optional user and environment. Cross-tenant
or wrong-user access is rejected before credentials are resolved. Capability
execution also checks connection state, enabled flags, declared operation type
and required scopes.

This framework does not bypass the Executive Orchestrator, EDE approvals or the
Execution Safety Kernel. In v1 it provides only read execution through adapters.
Write/action capability descriptions remain non-executable until the controlled
execution boundary is implemented and explicitly authorised.

## Operator Status

Use:

```bash
hermes integrations status
```

The command returns integration, connection, capability and adapter metadata
with credential values and secret-bearing metadata redacted. It also reports:

- `external_execution=not_executed`
- `live_execution_enabled=false`
- `outbound_writes_enabled=false`

## Current v1 Adapter

The first adapter is `calendar_google_rest`, supporting:

- integration: `google_calendar`
- capability: `calendar.events.read`
- auth: OAuth bearer token
- scope: `https://www.googleapis.com/auth/calendar.readonly`
- writes: unsupported

The Google Calendar Context Provider now depends on `IntegrationService` for
external reads. It no longer owns token loading, credential resolution or
connection health state.

## Inventory

Existing external access and framework treatment:

- `openrouter`: external reasoning provider, API-key auth, read/generate
  inference. Not migrated in v1; diagnostic preflight now isolates missing
  credentials before a local behavioural run.
- `custom` local reasoning provider: local HTTP-compatible reasoning endpoint.
  Not migrated; remains model-client infrastructure.
- `WhatsApp`: transport ingress/egress owned by Gateway/platform layer. Not
  migrated; not exposed to the LLM as an integration capability.
- `Supabase`/database: persistence infrastructure. Not migrated in v1.
- `google_calendar`: refactored onto IntegrationService for read-only context.
- MCP: remains disabled behind existing feature flags.

Stable infrastructure is not migrated merely for architectural purity. Future
context connectors should use this framework unless a lower-level platform
boundary is explicitly more appropriate.
