# ADR-0003: Hybrid Capability Truth

Status: proposed

Decision: Capability Truth is hybrid-owned. Code owns immutable deny defaults
and execution prohibitions. PostgreSQL owns tenant/channel capability state,
connection availability, authorised overlays, and auditable disclosure records.

Consequences:

- no connector can become available by prompt or model claim;
- capability honesty is queryable and auditable;
- PR #18 code-derived capability truth remains a safe baseline, not the final
  source of truth.
