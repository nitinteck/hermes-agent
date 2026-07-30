# Hermes Capability Truth Data Model v1

Status: Foundation Slice 1 implementation.

## Ownership Model

Capability Truth is hybrid-owned:

- Hermes code owns immutable safety ceilings and deny defaults.
- OVOS PostgreSQL owns tenant/channel/user/environment overlays.
- The effective runtime state is the most restrictive of both.

The database is authoritative for governed overlays, but never for relaxing a
hard code prohibition.

## States

Capability state is not boolean. Slice 1 defines:

- `unavailable`
- `disabled`
- `proposal_only`
- `read_only`
- `approval_required`
- `enabled`

The rank order is restrictive to permissive. Evaluation chooses the lower rank.

## Overlay Columns

`ovos.edp_capability_overlays` includes:

- `capability_key`
- `scope_type`
- `tenant_id`
- optional `user_id`
- optional `channel`
- optional `environment`
- `configured_state`
- `reason`
- `source`
- `version`
- `effective_from`
- `effective_until`
- `created_by`
- `reviewed_by`
- bounded `metadata`

Active overlays are unique per tenant, capability key and scope shape. Expired
overlays are ignored. Conflicting applicable overlays fail closed.

## Code Safety Ceilings

The runtime currently hard-caps these capabilities to `unavailable`:

- `external_execution`
- `live_execution`
- `send_email`
- `send_message`
- `create_event`
- `create_task`
- `gmail.write`
- `calendar.write`
- `clickup.write`
- `slack.write`
- `whatsapp.write`
- `crm.write`

`self_modification` and `improvement_proposals` are capped at
`proposal_only`.

## Fail-Closed Behaviour

- Unknown capability key: `unavailable`.
- Missing database state: restrictive default.
- Database unavailable: degraded and no more permissive than code ceiling.
- Database overlay says `enabled` for prohibited action: effective state remains
  `unavailable`.
- Execution status remains `not_executed`.
