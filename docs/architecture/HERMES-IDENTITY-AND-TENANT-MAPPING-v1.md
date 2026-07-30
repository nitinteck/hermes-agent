# Hermes Identity And Tenant Mapping v1

Status: Foundation Slice 1 implementation.

## Decision

Supabase Auth remains the canonical human identity provider. Hermes does not
create a parallel user identity system.

The OVOS schema already carries `tenant_id` and `owner_user_id` across
knowledge, executive, planning and audit tables, but the schema rationalisation
found no explicit tenant membership bridge. Slice 1 therefore adds
`ovos.edp_tenant_memberships` as the narrow relationship between `auth.users`
and OVOS tenant scopes.

## Mapping

```text
auth.users.id
  -> ovos.edp_tenant_memberships.user_id
  -> ovos.edp_tenant_memberships.tenant_id
  -> existing OVOS tenant_id columns
  -> channel/runtime context supplied by Hermes
```

`ovos.edp_tenant_memberships` stores role, status, channel and actor type. It
does not store credentials, profile payloads, phone numbers or external account
tokens.

## TenantContext

Hermes resolves a bounded runtime object:

- `user_id`
- `tenant_id`
- `membership_id`
- `role`
- `channel`
- `actor_type`
- `request_id`
- `correlation_id`

The runtime resolver reads trusted process configuration for diagnostics and
operator paths. Client-supplied tenant identifiers must not be trusted where
authenticated context can derive the tenant.

## Roles

Initial roles:

- `owner`
- `admin`
- `operator`
- `approver`
- `member`
- `service`

Governance review transitions require an owner, admin, operator, or explicit
service-role RPC context. Normal authenticated users may read only authorised
tenant rows and may create only proposed Improvement Proposals for their tenant.

## Non-Goals

This slice does not add a dashboard account system, OAuth connector identity,
workspace switching UX or production tenant backfill.
