# Hermes EDP Slice 1 RLS Review

Status: local implementation review. Production migration is not authorised.

## Tables

RLS is enabled on:

- `ovos.edp_tenant_memberships`
- `ovos.edp_capability_overlays`
- `ovos.edp_improvement_proposals`

## Access Model

Normal authenticated users:

- may read their own active tenant membership;
- may read capability overlays only through tenant membership or existing OVOS
  scope checks;
- may insert only `proposed` Improvement Proposals for their own active tenant;
- may not update capability overlays;
- may not review or transition proposals directly.

Tenant governance roles:

- owner, admin and operator are recognised by
  `ovos.edp_has_governance_role(...)`;
- proposal review transitions require governance role or explicit service-role
  RPC context;
- governance roles still cannot override Hermes hard code safety ceilings.

Hermes service/operator diagnostics:

- bounded RPCs expose only safe status fields;
- service-role RPC use in `hermes-agent` is opt-in via
  `HERMES_EDP_ALLOW_SERVICE_ROLE_RPC=true`;
- ordinary runtime reads should use an authenticated bearer token plus anon or
  publishable key.

## Security-Definer Functions

All Slice 1 RPCs set `search_path = ''`, validate tenant and actor context, and
avoid dynamic SQL.

## Audit

Governance events are written to `ovos.executive_event_journal` using bounded
metadata. Audit payloads contain identifiers, event types and safe metadata; they
must not contain secrets, raw prompts, unrestricted code or private message
content.

## Open Review Items

Before production migration, run database-level tests for:

- cross-tenant read blocking;
- cross-tenant write blocking;
- normal user overlay mutation rejection;
- conflicting overlay fail-closed behaviour;
- expired overlay ignore behaviour;
- invalid proposal transitions;
- audit event creation.
