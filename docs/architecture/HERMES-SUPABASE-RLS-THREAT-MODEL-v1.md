# Hermes Supabase RLS Threat Model v1

Status: target security model.

## Threats

| threat | control |
| --- | --- |
| Cross-tenant reads | RLS on every tenant table; leading `tenant_id`; membership checks through stable functions. |
| Cross-user private data leakage | owner/user scoped policies in addition to tenant membership. |
| Brand or department over-disclosure | brand/legal/financial policy joins, not application-only filters. |
| Confused-deputy service-role access | service role used only in narrow backend functions with explicit tenant/actor parameters and audit. |
| Vector search leakage | tenant, sensitivity, document-access filters must apply before or inside vector search functions. |
| Document URL leakage | private buckets, signed URLs, short expiry, document access policy checks. |
| Connector token leakage | secrets stored outside business tables; DB stores metadata and secret references only. |
| Model prompt/data leakage | audit stores digests and evidence IDs, not raw prompts. |
| Unsupported action execution | proposed actions and authorisations separated; approval alone never executes. |
| Operator overreach | operator actions audited; support access requires scoped, time-bound grants. |

## Roles And Access

- `anon`: no business data access.
- `authenticated`: access only through tenant membership and RLS.
- `tenant_owner`: manage tenant, policies, roles, and access.
- `tenant_admin`: operational administration within tenant.
- `employee`: normal scoped user access.
- `brand_member`: limited to assigned brand/location/programme.
- `approver`: read approval context and record decisions for assigned policies.
- `operator`: health and diagnostics, not private row dumps by default.
- `service_role`: backend-only, never exposed to clients, never used for broad
  user-facing reads.

## Operations That Must Not Use Broad Service Role

- normal dashboard reads;
- WhatsApp response context retrieval;
- vector search for user answers;
- document download/listing;
- approval recording by a human;
- capability disclosure to the user;
- tenant/brand scoped business fact retrieval.

When a privileged backend function is unavoidable, it must accept explicit
`tenant_id`, `actor_user_id`, `purpose`, and `correlation_id`, enforce policy
inside the database, and write an audit event.

## Policy Function Pattern

Use small stable SQL functions such as:

- `identity.current_user_id()`;
- `identity.has_tenant_role(tenant_id, role_key)`;
- `governance.can_disclose(actor, channel, object, sensitivity)`;
- `documents.can_access_document(actor, document_id)`;
- `governance.can_record_approval(actor, approval_request_id)`.

These functions should improve policy centralisation, not become broad
service-role mutation APIs.

## Edge And Background Jobs

Edge Functions and background workers may use privileged credentials only to
call narrow RPCs. Each RPC must validate idempotency, tenant membership or
connector ownership, permitted operation, and write an audit event.

## Current Gap Summary

The current `ovos` migrations include extensive tenant/user columns and many
RLS policies. The missing foundation is a clear canonical tenant/user/membership
model covering Hermes runtime state, future dashboards, and connector identity.
