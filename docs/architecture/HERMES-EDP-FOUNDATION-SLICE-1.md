# Hermes EDP Foundation Slice 1

Status: implementation PR, local validation only. No production migration or
deployment is authorised by this document.

## Purpose

Foundation Slice 1 establishes the first database-backed Executive Data
Platform path for Hermes:

- a minimal tenant membership bridge rooted in Supabase Auth;
- hybrid Capability Truth with code-owned safety ceilings and PostgreSQL
  tenant/channel/user/environment overlays;
- durable Improvement Proposals that can be reviewed without directly changing
  code, prompts, routing, skills, feature flags, connectors, or capabilities;
- bounded governance RPCs and operator-safe CLI visibility.

This slice does not enable Gmail, Calendar, ClickUp, Slack, CRM, MCP, approvals
or live external execution.

## Repository Boundary

The schema lives in `ovos-core`:

- `supabase/migrations/20260730120000_edp_foundation_slice_1.sql`
- `tests/test_edp_foundation_migration.py`

The runtime visibility and adapters live in `hermes-agent`:

- `gateway/edp_governance.py`
- `hermes_cli/governance.py`
- `tests/gateway/test_edp_governance.py`
- `tests/hermes_cli/test_edp_governance_cli.py`

## Database Objects

Slice 1 adds three narrowly scoped OVOS tables:

- `ovos.edp_tenant_memberships`
- `ovos.edp_capability_overlays`
- `ovos.edp_improvement_proposals`

It also adds bounded RPCs:

- `public.ovos_edp_resolve_effective_capability(...)`
- `public.ovos_edp_create_improvement_proposal(jsonb)`
- `public.ovos_edp_transition_improvement_proposal(...)`
- `public.ovos_edp_list_governance_status(...)`

The migration is additive. It reuses `auth.users`, `ovos.ede_capabilities`, and
`ovos.executive_event_journal`.

## Runtime Evaluation

Effective capability state is the most restrictive result from:

1. immutable Hermes code safety ceiling;
2. database overlay returned by OVOS RPC;
3. degraded fallback when the database is unavailable.

A database row cannot relax a code prohibition. Unknown capability keys fail
closed. Missing or unavailable database state cannot become permissive.

## CLI Visibility

New commands:

```bash
hermes governance status
hermes governance capability-truth status send_email
hermes governance improvement-proposals status
```

The commands are diagnostic. They do not create proposals, transition proposal
status, approve actions, invoke adapters, send messages or perform external
execution.

## Gate Status

Gate A requires local migration validation, focused tests, documentation, clean
diffs and opened PRs. Gate B and Gate C remain explicit future decisions. This
slice must stop before production migration or deployment unless separately
authorised.
