# Hermes Edge Function Boundaries v1

Status: target design. Current OVOS Supabase project inspection returned no
deployed Edge Functions.

## Suitable Edge Functions

| function | trigger | auth | permitted DB surface | idempotency | failure behaviour |
| --- | --- | --- | --- | --- | --- |
| `oauth_callback` | provider OAuth redirect | signed state + Auth | connection metadata RPC only | provider state nonce | reject and audit mismatch |
| `webhook_ingest` | signed provider webhook | provider signature | insert inbound event RPC | provider event id | replay returns existing event |
| `upload_initiate` | dashboard/operator request | Auth + RLS | document metadata RPC, signed upload URL | client idempotency key | fail closed, no object policy bypass |
| `approval_link_validate` | approval link open | signed token + Auth where possible | read approval request summary RPC | token id | expired/replayed links rejected |
| `queue_publish` | internal trusted call | service identity | enqueue job RPC | job key | duplicate returns existing job |
| `realtime_authorize` | subscription setup | Auth | scoped subscription policy | session id | deny by default |

## Unsuitable Edge Function Responsibilities

- executive reasoning or model orchestration;
- planning engines;
- long-running connector sync;
- broad service-role CRUD APIs;
- business rules duplicated from Hermes runtime;
- secret storage in payloads;
- unrestricted notification dispatch;
- direct external execution without the future execution boundary.

## Required Controls

Each function must define:

- input schema and max payload size;
- authentication method;
- database role and exact RPC/table access;
- tenant and actor derivation;
- replay/idempotency policy;
- rate limiting;
- audit event type;
- failure class and retry policy;
- secret handling and redaction.

## Recommendation

Keep Edge Functions thin. They should verify trust at the boundary, persist or
enqueue a minimal event, and return. Hermes runtime remains responsible for
reasoning, planning, and controlled connector orchestration.
