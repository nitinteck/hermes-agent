# Hermes Business Knowledge RLS Review v1

Status: Slice 3 review candidate.

## Access Model

Business Knowledge tables live in the private `ovos` schema. Direct table writes
are granted to `service_role` only. Authenticated users receive direct `select`
grants so RLS can enforce tenant and sensitivity checks, and runtime access goes
through public RPCs.

## RLS Predicate

Read policies call `ovos.bk_can_read(...)`.

The predicate allows:

- service-role diagnostics;
- the row owner;
- tenant members for `public` and `internal` rows with matching disclosure
  policy;
- governance roles for sensitive review scenarios.

It blocks:

- cross-tenant reads;
- non-owner reads of `confidential` or `restricted` rows unless the actor has a
  governance role;
- direct authenticated inserts into canonical tables.

## RPC Checks

`ovos.bk_assert_actor(...)` requires service-role context or both:

- `auth.uid() = actor_user_id`;
- active membership in the supplied tenant.

This prevents a signed-in user from pairing their own user id with another
tenant id during import dry-runs or lifecycle transitions.

## Audit

Insert/update triggers write bounded audit metadata through
`ovos.edp_record_governance_audit`. Audit events include table, operation,
aggregate id, and safe status fields; they do not dump raw fact values or import
payloads.
