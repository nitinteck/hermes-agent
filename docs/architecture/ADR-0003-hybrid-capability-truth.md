# ADR-0003: Hybrid Capability Truth

Status: accepted, implemented by Foundation Slice 1

Decision: Capability Truth is hybrid-owned. Code owns immutable deny defaults
and execution prohibitions. PostgreSQL owns tenant/channel capability state,
connection availability, authorised overlays, and auditable disclosure records.

Consequences:

- no connector can become available by prompt or model claim;
- capability honesty is queryable and auditable;
- PR #18 code-derived capability truth remains a safe baseline, not the final
  source of truth.

Implementation evidence:

- `ovos-core/supabase/migrations/20260730120000_edp_foundation_slice_1.sql`
  adds `ovos.edp_capability_overlays` and bounded Capability Truth RPCs.
- `hermes-agent/gateway/edp_governance.py` applies immutable code ceilings
  before database overlays.
- The effective execution boundary remains `not_executed`.
